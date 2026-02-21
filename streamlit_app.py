import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (FIXED URL)
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()
    
    # S&P 500 (FIXED URL - removed space)
    try:
        sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")
    
    # ETFs
    etfs = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV", "TLT", "GLD", "VXX", "SQQQ", "TQQQ"]
    tickers.update(etfs)
    
    # Indexes
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)
    
    return sorted(tickers)

TICKERS = load_tickers()

# =====================================================
# MULTIINDEX HELPER (CRITICAL FIX FOR MODERN YFINANCE)
# =====================================================
def get_val(row, col, ticker=None):
    """
    Extract values handling both MultiIndex (new yfinance) and flat columns (old)
    """
    if isinstance(row.index, pd.MultiIndex):
        try:
            # Try (column, ticker) format first
            if ticker and (col, ticker) in row.index:
                return float(row[(col, ticker)])
            # If ticker not provided or not found, try to get first value
            return float(row[col].iloc[0] if hasattr(row[col], 'iloc') else row[col])
        except (KeyError, IndexError, ValueError):
            pass
    # Fall back to flat index (old yfinance or single ticker)
    return float(row[col])

# =====================================================
# STRAT CANDLE LOGIC (WITH MULTIINDEX SUPPORT)
# =====================================================
def strat_type(prev, curr, ticker):
    """Calculate STRAT pattern with proper MultiIndex handling"""
    try:
        prev_h = get_val(prev, "High", ticker)
        prev_l = get_val(prev, "Low", ticker)
        curr_h = get_val(curr, "High", ticker)
        curr_l = get_val(curr, "Low", ticker)
        curr_o = get_val(curr, "Open", ticker)
        curr_c = get_val(curr, "Close", ticker)
    except Exception as e:
        return f"Error: {e}"
    
    candle_color = "Green" if curr_c >= curr_o else "Red"
    
    if curr_h < prev_h and curr_l > prev_l:
        return "1 (Inside)"
    elif curr_h > prev_h and curr_l < prev_l:
        return "3 (Outside)"
    elif curr_h > prev_h:
        return f"2U {candle_color}"
    elif curr_l < prev_l:
        return f"2D {candle_color}"
    else:
        return "Undefined"

# =====================================================
# FTFC CALCULATION (FIXED FOR 3M TIMEFRAME)
# =====================================================
def calculate_ftfc(ticker, current_close, is_quarterly=False):
    """
    Calculate FTFC: Compare current price to Monthly and Weekly/Quarterly opening prices
    For 3M timeframe, compares to Quarterly open instead of Weekly
    """
    ftfc_results = []
    
    # Monthly FTFC (always check monthly)
    try:
        monthly_data = yf.download(
            ticker, 
            period="6mo",  # Shorter period for monthly
            interval="1mo", 
            progress=False, 
            auto_adjust=True
        )
        
        if not monthly_data.empty and len(monthly_data) >= 1:
            # Get current month's open price
            if isinstance(monthly_data.columns, pd.MultiIndex):
                monthly_open = float(monthly_data.iloc[-1][("Open", ticker)])
            else:
                monthly_open = float(monthly_data.iloc[-1]["Open"])
            
            if current_close > monthly_open:
                ftfc_results.append("M: Bullish")
            elif current_close < monthly_open:
                ftfc_results.append("M: Bearish")
    except Exception as e:
        pass
    
    # Weekly or Quarterly FTFC based on timeframe
    if is_quarterly:
        # For 3M timeframe, check against current quarter open using 3mo data
        try:
            quarterly_data = yf.download(
                ticker, 
                period="1y",
                interval="3mo", 
                progress=False, 
                auto_adjust=True
            )
            
            if not quarterly_data.empty and len(quarterly_data) >= 1:
                if isinstance(quarterly_data.columns, pd.MultiIndex):
                    quarterly_open = float(quarterly_data.iloc[-1][("Open", ticker)])
                else:
                    quarterly_open = float(quarterly_data.iloc[-1]["Open"])
                
                if current_close > quarterly_open:
                    ftfc_results.append("Q: Bullish")
                elif current_close < quarterly_open:
                    ftfc_results.append("Q: Bearish")
        except Exception as e:
            pass
    else:
        # Weekly FTFC for daily/weekly/monthly timeframes
        try:
            weekly_data = yf.download(
                ticker, 
                period="1mo",
                interval="1wk", 
                progress=False, 
                auto_adjust=True
            )
            
            if not weekly_data.empty and len(weekly_data) >= 1:
                if isinstance(weekly_data.columns, pd.MultiIndex):
                    weekly_open = float(weekly_data.iloc[-1][("Open", ticker)])
                else:
                    weekly_open = float(weekly_data.iloc[-1]["Open"])
                
                if current_close > weekly_open:
                    ftfc_results.append("W: Bullish")
                elif current_close < weekly_open:
                    ftfc_results.append("W: Bearish")
        except Exception as e:
            pass
    
    return ", ".join(ftfc_results) if ftfc_results else "N/A"

# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner with FTFC")
st.caption(f"Scanning **{len(TICKERS)}** tickers | STRAT Patterns + Timeframe Continuity")

timeframe = st.selectbox(
    "Select Timeframe", 
    ["Daily", "Weekly", "Monthly", "3-Month"]
)

# UPDATED: Fixed period mapping for 3M to ensure enough data
interval_map = {
    "Daily": "1d", 
    "Weekly": "1wk", 
    "Monthly": "1mo",
    "3-Month": "3mo"
}

# CRITICAL FIX: 3mo needs "max" period to get enough candles
period_map = {
    "Daily": "6mo",
    "Weekly": "12mo", 
    "Monthly": "2y",
    "3-Month": "max"  # Changed from "5y" to "max" to ensure enough 3mo candles
}

# Minimum candles needed for STRAT calculation
min_candles_map = {
    "Daily": 3,
    "Weekly": 3,
    "Monthly": 3,
    "3-Month": 2  # 3mo candles are large, only need 2 for comparison (prev vs curr)
}

available_patterns = ["1 (Inside)", "3 (Outside)", "2U Red", "2U Green", "2D Red", "2D Green"]

st.subheader("STRAT Pattern Filters")
col1, col2 = st.columns(2)
with col1:
    prev_patterns = st.multiselect("Previous Candle", options=available_patterns, default=available_patterns)
with col2:
    curr_patterns = st.multiselect("Current Candle", options=available_patterns, default=available_patterns)

# FTFC Filter Section
st.subheader("FTFC (Follow The Timeframe Continuity) Filter")

# Dynamic FTFC options based on timeframe
if timeframe == "3-Month":
    ftfc_options = ["Any", "M: Bullish", "M: Bearish", "Q: Bullish", "Q: Bearish", "Both Bullish", "Both Bearish"]
else:
    ftfc_options = ["Any", "M: Bullish", "M: Bearish", "W: Bullish", "W: Bearish", "Both Bullish", "Both Bearish"]

ftfc_filter = st.multiselect("FTFC Direction", options=ftfc_options, default=["Any"])

# Options
col3, col4 = st.columns(2)
with col3:
    debug_mode = st.checkbox("Debug Mode (show raw data)", value=False)
with col4:
    limit_tickers = st.number_input("Limit tickers (0 = all)", min_value=0, max_value=len(TICKERS), value=50)

scan_button = st.button("🔍 Run Scanner", type="primary")

# =====================================================
# SCANNER WITH 3-MONTH SUPPORT
# =====================================================
if scan_button:
    results = []
    
    tickers_to_scan = TICKERS[:limit_tickers] if limit_tickers > 0 else TICKERS
    total = len(tickers_to_scan)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Get appropriate settings for selected timeframe
    download_period = period_map[timeframe]
    min_candles = min_candles_map[timeframe]
    is_3m = (timeframe == "3-Month")
    
    for idx, ticker in enumerate(tickers_to_scan):
        try:
            # Update progress
            progress = (idx + 1) / total
            progress_bar.progress(min(progress, 0.99))
            status_text.text(f"Scanning {ticker}... ({idx+1}/{total}) | TF: {timeframe} | Need {min_candles} candles")
            
            # Download main timeframe data
            data = yf.download(
                ticker,
                period=download_period,
                interval=interval_map[timeframe],
                progress=False,
                auto_adjust=True,
            )
            
            # Debug: Show raw data structure
            if debug_mode and idx < 3:
                with st.expander(f"🔍 Debug: {ticker} - {len(data)} candles found"):
                    st.write("Columns:", data.columns.tolist())
                    st.write("Data shape:", data.shape)
                    st.write("First candle:", data.iloc[0].to_dict() if len(data) > 0 else "None")
                    st.write("Last 3 candles:")
                    st.dataframe(data.tail(3))
            
            # Check if we have enough data
            if data.empty or len(data) < min_candles:
                if debug_mode:
                    st.warning(f"{ticker}: Insufficient data (found {len(data)}, need {min_candles})")
                continue
            
            # For 3M timeframe, we only need 2 candles (prev vs curr)
            # For others, we need 3 candles (prev_prev, prev, curr)
            if is_3m and len(data) >= 2:
                prev = data.iloc[-2]
                curr = data.iloc[-1]
                prev_candle = strat_type(prev, curr, ticker)  # Compare prev to curr
                curr_candle = strat_type(prev, curr, ticker)  # Same for current (simplified for 3M)
                # For 3M, we treat the comparison as the "current" candle pattern
                curr_candle = strat_type(prev, curr, ticker)
                prev_candle = "N/A (3M)"  # No previous pattern for 3M with only 2 candles
            else:
                # Standard 3-candle STRAT for other timeframes
                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]
                prev_candle = strat_type(prev_prev, prev, ticker)
                curr_candle = strat_type(prev, curr, ticker)
            
            # Skip if error in calculation
            if "Error" in str(prev_candle) or "Error" in str(curr_candle):
                if debug_mode:
                    st.warning(f"{ticker}: STRAT calculation error")
                continue
            
            # Check pattern filters (skip prev check for 3M if N/A)
            if is_3m and prev_candle == "N/A (3M)":
                pattern_match = (not curr_patterns or curr_candle in curr_patterns)
            else:
                pattern_match = (not prev_patterns or prev_candle in prev_patterns) and \
                               (not curr_patterns or curr_candle in curr_patterns)
            
            if not pattern_match:
                continue
            
            # Get current price with MultiIndex support
            curr_close = get_val(curr, "Close", ticker)
            curr_open = get_val(curr, "Open", ticker)
            
            # Calculate FTFC with quarterly flag for 3M
            ftfc_str = calculate_ftfc(ticker, curr_close, is_quarterly=is_3m)
            
            # Apply FTFC filter
            if "Any" not in ftfc_filter:
                if "Both Bullish" in ftfc_filter:
                    if not (("M: Bullish" in ftfc_str and "W: Bullish" in ftfc_str) or 
                            ("M: Bullish" in ftfc_str and "Q: Bullish" in ftfc_str)):
                        continue
                elif "Both Bearish" in ftfc_filter:
                    if not (("M: Bearish" in ftfc_str and "W: Bearish" in ftfc_str) or
                            ("M: Bearish" in ftfc_str and "Q: Bearish" in ftfc_str)):
                        continue
                else:
                    # Check if any selected FTFC matches
                    if not any(f in ftfc_str for f in ftfc_filter if f != "Any"):
                        continue
            
            # Add to results
            results.append({
                "Ticker": ticker,
                "Previous Candle": prev_candle,
                "Current Candle": curr_candle,
                "Direction": "Up" if curr_close > curr_open else "Down",
                "Close Price": round(curr_close, 2),
                "FTFC": ftfc_str,
            })
            
        except Exception as e:
            if debug_mode:
                st.error(f"Error with {ticker}: {str(e)}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    # Display results
    if results:
        df = pd.DataFrame(results)
        
        # FTFC color coding function
        def color_ftfc(val):
            if "Bullish" in val:
                return "color: #00aa00; font-weight: bold"
            elif "Bearish" in val:
                return "color: #cc0000; font-weight: bold"
            return ""
        
        st.success(f"🎯 Found **{len(df)}** matching tickers out of {total} scanned | Timeframe: {timeframe}")
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, f"strat_scanner_{timeframe.lower().replace('-', '_')}_results.csv", "text/csv")
        
        # Display with FTFC styling
        st.dataframe(
            df.style.applymap(color_ftfc, subset=['FTFC']),
            use_container_width=True,
            hide_index=True
        )
        
        # Summary statistics
        st.subheader("Summary")
        
        if timeframe == "3-Month":
            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
            with col_stats1:
                bullish_m = df['FTFC'].str.contains('M: Bullish').sum()
                st.metric("Monthly Bullish", f"{bullish_m}")
            with col_stats2:
                bearish_m = df['FTFC'].str.contains('M: Bearish').sum()
                st.metric("Monthly Bearish", f"{bearish_m}")
            with col_stats3:
                bullish_q = df['FTFC'].str.contains('Q: Bullish').sum()
                st.metric("Quarterly Bullish", f"{bullish_q}")
            with col_stats4:
                bearish_q = df['FTFC'].str.contains('Q: Bearish').sum()
                st.metric("Quarterly Bearish", f"{bearish_q}")
        else:
            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
            with col_stats1:
                bullish_m = df['FTFC'].str.contains('M: Bullish').sum()
                st.metric("Monthly Bullish", f"{bullish_m}")
            with col_stats2:
                bearish_m = df['FTFC'].str.contains('M: Bearish').sum()
                st.metric("Monthly Bearish", f"{bearish_m}")
            with col_stats3:
                bullish_w = df['FTFC'].str.contains('W: Bullish').sum()
                st.metric("Weekly Bullish", f"{bullish_w}")
            with col_stats4:
                bearish_w = df['FTFC'].str.contains('W: Bearish').sum()
                st.metric("Weekly Bearish", f"{bearish_w}")
            
    else:
        st.warning("⚠️ No tickers matched the selected criteria.")
        
        with st.expander("🔧 Troubleshooting 3-Month Timeframe"):
            st.markdown(f"""
            **Current Settings:**
            - Timeframe: {timeframe}
            - Interval: {interval_map[timeframe]}
            - Download Period: {period_map[timeframe]}
            - Min Candles Required: {min_candles_map[timeframe]}
            
            **Common 3-Month Issues:**
            
            1. **Not enough candles**: 3-month data returns very few candles. 
               - "max" period typically returns ~20-25 years = ~80 quarterly candles
               - "5y" only returns ~20 candles (may not be enough)
            
            2. **Enable Debug Mode** - Check the box and run again to see:
               - How many candles yfinance returns
               - Column structure (MultiIndex vs flat)
            
            3. **Test single ticker**:
               ```python
               import yfinance as yf
               data = yf.download('AAPL', period='max', interval='3mo')
               print(f"Candles: {len(data)}")
               print(data.tail(3))
               ```
            
            4. **Relax filters** - Try selecting "Any" in FTFC filter and all patterns
            
            **Note**: With 3-month candles, STRAT patterns are calculated differently:
            - Only 2 candles needed (previous quarter vs current quarter)
            - Previous candle shows "N/A (3M)" if only 2 candles available
            """)
