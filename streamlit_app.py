import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (FIXED URL - REMOVED SPACE)
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()
    
    # S&P 500 (FIXED URL)
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
    New yfinance returns columns like: ('Close', 'AAPL'), ('High', 'AAPL'), etc.
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
# FTFC CALCULATION (FOLLOW THE TIMEFRAME CONTINUITY)
# =====================================================
def calculate_ftfc(ticker, current_close):
    """
    Calculate FTFC: Compare current price to Monthly and Weekly opening prices
    Returns format: "M: Bullish, W: Bearish" or "N/A"
    """
    ftfc_results = []
    
    # Monthly FTFC
    try:
        monthly_data = yf.download(
            ticker, 
            period="3mo", 
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
    except Exception:
        pass
    
    # Weekly FTFC
    try:
        weekly_data = yf.download(
            ticker, 
            period="1mo", 
            interval="1wk", 
            progress=False, 
            auto_adjust=True
        )
        
        if not weekly_data.empty and len(weekly_data) >= 1:
            # Get current week's open price
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
st.caption(f"Scanning **{len(TICKERS)}** tickers | STRAT Patterns + Timeframe Continuity")

timeframe = st.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}

available_patterns = ["1 (Inside)", "3 (Outside)", "2U Red", "2U Green", "2D Red", "2D Green"]

st.subheader("STRAT Pattern Filters")
col1, col2 = st.columns(2)
with col1:
    prev_patterns = st.multiselect("Previous Candle", options=available_patterns, default=available_patterns)
with col2:
    curr_patterns = st.multiselect("Current Candle", options=available_patterns, default=available_patterns)

# FTFC Filter Section
st.subheader("FTFC (Follow The Timeframe Continuity) Filter")
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
# SCANNER WITH FTFC
# =====================================================
if scan_button:
    results = []
    
    tickers_to_scan = TICKERS[:limit_tickers] if limit_tickers > 0 else TICKERS
    total = len(tickers_to_scan)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, ticker in enumerate(tickers_to_scan):
        try:
            # Update progress
            progress = (idx + 1) / total
            progress_bar.progress(min(progress, 0.99))
            status_text.text(f"Scanning {ticker}... ({idx+1}/{total})")
            
            # Download main timeframe data
            data = yf.download(
                ticker,
                period="6mo",
                interval=interval_map[timeframe],
                progress=False,
                auto_adjust=True,
            )
            
            # Debug: Show raw data structure
            if debug_mode and idx < 2:
                with st.expander(f"🔍 Debug: {ticker} - Columns: {data.columns.tolist()}"):
                    st.write("Data shape:", data.shape)
                    st.dataframe(data.tail(3))
            
            if data.empty or len(data) < 3:
                continue
            
            # Get last 3 candles for STRAT calculation
            prev_prev = data.iloc[-3]
            prev = data.iloc[-2]
            curr = data.iloc[-1]
            
            # Calculate STRAT patterns with MultiIndex support
            prev_candle = strat_type(prev_prev, prev, ticker)
            curr_candle = strat_type(prev, curr, ticker)
            
            # Skip if error in calculation
            if "Error" in prev_candle or "Error" in curr_candle:
                continue
            
            # Check pattern filters
            pattern_match = (not prev_patterns or prev_candle in prev_patterns) and \
                           (not curr_patterns or curr_candle in curr_patterns)
            
            if not pattern_match:
                continue
            
            # Get current price with MultiIndex support
            curr_close = get_val(curr, "Close", ticker)
            curr_open = get_val(curr, "Open", ticker)
            
            # Calculate FTFC
            ftfc_str = calculate_ftfc(ticker, curr_close)
            
            # Apply FTFC filter
            if "Any" not in ftfc_filter:
                if "Both Bullish" in ftfc_filter:
                    if not ("M: Bullish" in ftfc_str and "W: Bullish" in ftfc_str):
                        continue
                elif "Both Bearish" in ftfc_filter:
                    if not ("M: Bearish" in ftfc_str and "W: Bearish" in ftfc_str):
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
        
        st.success(f"🎯 Found **{len(df)}** matching tickers out of {total} scanned")
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "strat_scanner_results.csv", "text/csv")
        
        # Display with FTFC styling
        st.dataframe(
            df.style.applymap(color_ftfc, subset=['FTFC']),
            use_container_width=True,
            hide_index=True
        )
        
        # Summary statistics
        st.subheader("Summary")
        col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
        
        with col_stats1:
            bullish_ftfc = df['FTFC'].str.contains('M: Bullish').sum()
            st.metric("Monthly Bullish", f"{bullish_ftfc}")
        with col_stats2:
            bearish_ftfc = df['FTFC'].str.contains('M: Bearish').sum()
            st.metric("Monthly Bearish", f"{bearish_ftfc}")
        with col_stats3:
            weekly_bull = df['FTFC'].str.contains('W: Bullish').sum()
            st.metric("Weekly Bullish", f"{weekly_bull}")
        with col_stats4:
            weekly_bear = df['FTFC'].str.contains('W: Bearish').sum()
            st.metric("Weekly Bearish", f"{weekly_bear}")
            
    else:
        st.warning("⚠️ No tickers matched the selected criteria.")
        
        with st.expander("🔧 Troubleshooting Tips"):
            st.markdown("""
            **If no results appear:**
            
            1. **Enable Debug Mode** - Check the box and run again to see if data is downloading
            2. **Relax filters** - Select "Any" in FTFC filter and all patterns in STRAT filters
            3. **Check yfinance** - Run: `pip install yfinance --upgrade`
            4. **Test single ticker** - In Python run:
               ```python
               import yfinance as yf
               data = yf.download('AAPL', period='5d')
               print(data.columns)  # Should show MultiIndex like ('Close', 'AAPL')
               ```
            
            **Common issues:**
            - **MultiIndex columns**: Modern yfinance returns `('Close', 'AAPL')` instead of just `'Close'`
            - **Rate limiting**: Too many requests to Yahoo Finance
            - **Invalid intervals**: Only use 1d, 1wk, 1mo (not 2d, 4h, etc.)
            """)
