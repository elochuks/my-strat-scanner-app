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
    
    try:
        sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")
    
    etfs = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV", "TLT", "GLD", "VXX", "SQQQ", "TQQQ"]
    tickers.update(etfs)
    
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)
    
    return sorted(tickers)

TICKERS = load_tickers()

# =====================================================
# MULTIINDEX VALUE EXTRACTOR (FIXED)
# =====================================================
def get_val(row, col, ticker):
    """
    Extract value from row handling MultiIndex columns
    Format: ('Close', 'QQQ'), ('High', 'QQQ'), etc.
    """
    try:
        # MultiIndex format: ('Close', 'TICKER')
        if isinstance(row.index, pd.MultiIndex):
            return float(row[(col, ticker)])
        else:
            # Flat format (older yfinance)
            return float(row[col])
    except (KeyError, ValueError, TypeError) as e:
        raise e

# =====================================================
# STRAT CANDLE LOGIC (WORKING VERSION)
# =====================================================
def strat_type(prev, curr, ticker):
    """Calculate STRAT pattern - WORKING with MultiIndex"""
    try:
        # Extract values using helper
        prev_h = get_val(prev, "High", ticker)
        prev_l = get_val(prev, "Low", ticker)
        curr_h = get_val(curr, "High", ticker)
        curr_l = get_val(curr, "Low", ticker)
        curr_o = get_val(curr, "Open", ticker)
        curr_c = get_val(curr, "Close", ticker)
        
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
            
    except Exception as e:
        return f"Error: {str(e)}"

# =====================================================
# FTFC CALCULATION (FIXED FOR MULTIINDEX)
# =====================================================
def calculate_ftfc(ticker, current_close, is_quarterly=False):
    """Calculate FTFC with proper MultiIndex handling"""
    ftfc_results = []
    
    # Monthly FTFC
    try:
        monthly_data = yf.download(
            ticker, 
            period="6mo", 
            interval="1mo", 
            progress=False, 
            auto_adjust=True
        )
        
        if not monthly_data.empty and len(monthly_data) >= 1:
            # Handle MultiIndex
            if isinstance(monthly_data.columns, pd.MultiIndex):
                monthly_open = float(monthly_data.iloc[-1][("Open", ticker)])
            else:
                monthly_open = float(monthly_data.iloc[-1]["Open"])
            
            if current_close > monthly_open:
                ftfc_results.append("M: Bullish")
            elif current_close < monthly_open:
                ftfc_results.append("M: Bearish")
    except Exception:
        pass
    
    # Weekly or Quarterly FTFC
    if is_quarterly:
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
        except Exception:
            pass
    else:
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
        except Exception:
            pass
    
    return ", ".join(ftfc_results) if ftfc_results else "N/A"

# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner with FTFC")
st.caption(f"Scanning **{len(TICKERS)}** tickers | Working 3-Month Support")

timeframe = st.selectbox(
    "Select Timeframe", 
    ["Daily", "Weekly", "Monthly", "3-Month"]
)

interval_map = {
    "Daily": ("1d", "1y"),
    "Weekly": ("1wk", "2y"), 
    "Monthly": ("1mo", "5y"),
    "3-Month": ("3mo", "max")
}

available_patterns = ["1 (Inside)", "3 (Outside)", "2U Red", "2U Green", "2D Red", "2D Green"]

st.subheader("STRAT Pattern Filters")
col1, col2 = st.columns(2)
with col1:
    prev_patterns = st.multiselect("Previous Candle", options=available_patterns, default=available_patterns)
with col2:
    curr_patterns = st.multiselect("Current Candle", options=available_patterns, default=available_patterns)

# FTFC Filter
st.subheader("FTFC Filter")

if timeframe == "3-Month":
    ftfc_options = ["Any", "M: Bullish", "M: Bearish", "Q: Bullish", "Q: Bearish", "Both Bullish", "Both Bearish"]
else:
    ftfc_options = ["Any", "M: Bullish", "M: Bearish", "W: Bullish", "W: Bearish", "Both Bullish", "Both Bearish"]

ftfc_filter = st.multiselect("FTFC Direction", options=ftfc_options, default=["Any"])

# Options
col3, col4 = st.columns(2)
with col3:
    show_details = st.checkbox("Show Processing Details", value=False)
with col4:
    limit_tickers = st.number_input("Limit tickers (0 = all)", min_value=0, max_value=len(TICKERS), value=100)

scan_button = st.button("🔍 Run Scanner", type="primary")

# =====================================================
# SCANNER (FIXED AND WORKING)
# =====================================================
if scan_button:
    results = []
    
    tickers_to_scan = TICKERS[:limit_tickers] if limit_tickers > 0 else TICKERS
    total = len(tickers_to_scan)
    
    interval, period = interval_map[timeframe]
    is_3m = (timeframe == "3-Month")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # For 3M, we only need 2 candles. For others, we need 3
    min_candles = 2 if is_3m else 3
    
    for idx, ticker in enumerate(tickers_to_scan):
        try:
            progress = (idx + 1) / total
            progress_bar.progress(min(progress, 0.99))
            status_text.text(f"Scanning {ticker}... ({idx+1}/{total})")
            
            # Download data
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            
            if show_details and idx < 3:
                st.write(f"**{ticker}:** {len(data)} candles, MultiIndex: {isinstance(data.columns, pd.MultiIndex)}")
            
            if data.empty or len(data) < min_candles:
                continue
            
            # Get candles based on timeframe
            if is_3m:
                # 3M: Compare last 2 candles only
                prev = data.iloc[-2]
                curr = data.iloc[-1]
                
                # Calculate pattern (prev vs curr)
                curr_candle = strat_type(prev, curr, ticker)
                prev_candle = "N/A (3M)"  # No previous pattern with only 2 candles
                
                # Get current price
                curr_close = get_val(curr, "Close", ticker)
                curr_open = get_val(curr, "Open", ticker)
                
            else:
                # Daily/Weekly/Monthly: Use 3 candles
                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]
                
                prev_candle = strat_type(prev_prev, prev, ticker)
                curr_candle = strat_type(prev, curr, ticker)
                
                # Get current price
                curr_close = get_val(curr, "Close", ticker)
                curr_open = get_val(curr, "Open", ticker)
            
            # Skip if error
            if "Error" in str(curr_candle):
                continue
            
            # Check pattern filters
            if is_3m:
                pattern_match = (not curr_patterns or curr_candle in curr_patterns)
            else:
                pattern_match = (not prev_patterns or prev_candle in prev_patterns) and \
                               (not curr_patterns or curr_candle in curr_patterns)
            
            if not pattern_match:
                continue
            
            # Calculate FTFC
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
                    if not any(f in ftfc_str for f in ftfc_filter if f != "Any"):
                        continue
            
            # Add result
            results.append({
                "Ticker": ticker,
                "Previous Candle": prev_candle,
                "Current Candle": curr_candle,
                "Direction": "Up" if curr_close > curr_open else "Down",
                "Close Price": round(curr_close, 2),
                "FTFC": ftfc_str,
            })
            
        except Exception as e:
            if show_details:
                st.error(f"Error with {ticker}: {e}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    # Display results
    if results:
        df = pd.DataFrame(results)
        
        # Color coding
        def color_ftfc(val):
            if "Bullish" in val:
                return "color: #00aa00; font-weight: bold"
            elif "Bearish" in val:
                return "color: #cc0000; font-weight: bold"
            return ""
        
        st.success(f"🎯 Found **{len(df)}** matching tickers out of {total} scanned | Timeframe: {timeframe}")
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, f"strat_{timeframe.lower().replace('-', '_')}_results.csv", "text/csv")
        
        st.dataframe(
            df.style.applymap(color_ftfc, subset=['FTFC']),
            use_container_width=True,
            hide_index=True
        )
        
        # Summary
        st.subheader("Summary")
        if timeframe == "3-Month":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Monthly Bullish", df['FTFC'].str.contains('M: Bullish').sum())
            c2.metric("Monthly Bearish", df['FTFC'].str.contains('M: Bearish').sum())
            c3.metric("Quarterly Bullish", df['FTFC'].str.contains('Q: Bullish').sum())
            c4.metric("Quarterly Bearish", df['FTFC'].str.contains('Q: Bearish').sum())
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Monthly Bullish", df['FTFC'].str.contains('M: Bullish').sum())
            c2.metric("Monthly Bearish", df['FTFC'].str.contains('M: Bearish').sum())
            c3.metric("Weekly Bullish", df['FTFC'].str.contains('W: Bullish').sum())
            c4.metric("Weekly Bearish", df['FTFC'].str.contains('W: Bearish').sum())
    else:
        st.warning("No tickers matched. Try relaxing filters or check 'Show Processing Details' to debug.")
