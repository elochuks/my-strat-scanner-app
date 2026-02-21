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
    etfs = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV", "TLT", "GLD", "VXX"]
    tickers.update(etfs)
    
    # Indexes
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)
    
    return sorted(tickers)

TICKERS = load_tickers()

# =====================================================
# STRAT CANDLE LOGIC (UPDATED FOR MULTIINDEX)
# =====================================================
def strat_type(prev, curr, ticker):
    """
    Extract values handling both MultiIndex (new yfinance) and flat columns (old)
    """
    def get_val(row, col):
        # Try MultiIndex first (new yfinance format: ('Close', 'AAPL'))
        if isinstance(row.index, pd.MultiIndex):
            try:
                return float(row[(col, ticker)])
            except KeyError:
                pass
        # Fall back to flat index (old format)
        return float(row[col])
    
    try:
        prev_h = get_val(prev, "High")
        prev_l = get_val(prev, "Low")
        curr_h = get_val(curr, "High")
        curr_l = get_val(curr, "Low")
        curr_o = get_val(curr, "Open")
        curr_c = get_val(curr, "Close")
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
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers")

timeframe = st.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}

available_patterns = ["1 (Inside)", "3 (Outside)", "2U Red", "2U Green", "2D Red", "2D Green"]

st.subheader("STRAT Pattern Filters")
prev_patterns = st.multiselect("Previous Candle", options=available_patterns, default=available_patterns)
curr_patterns = st.multiselect("Current Candle", options=available_patterns, default=available_patterns)

debug_mode = st.checkbox("Debug Mode (show first 3 tickers data)", value=False)
scan_button = st.button("Run Scanner", type="primary")

# =====================================================
# SCANNER (FIXED)
# =====================================================
if scan_button:
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, ticker in enumerate(TICKERS[:50] if debug_mode else TICKERS):  # Limit to 50 in debug
        try:
            progress_bar.progress(min((idx + 1) / len(TICKERS[:50] if debug_mode else TICKERS), 0.99))
            status_text.text(f"Scanning {ticker}... ({idx+1}/{len(TICKERS[:50] if debug_mode else TICKERS)})")
            
            # Download with auto_adjust=True (recommended) and progress=False
            data = yf.download(
                ticker,
                period="6mo",
                interval=interval_map[timeframe],
                progress=False,
                auto_adjust=True,  # Use adjusted prices
            )
            
            if debug_mode and idx < 3:
                with st.expander(f"Debug: {ticker} raw data"):
                    st.write("Columns:", data.columns.tolist())
                    st.write("Shape:", data.shape)
                    st.dataframe(data.tail(3))
            
            if data.empty or len(data) < 3:
                continue
            
            # Check if we have MultiIndex columns
            is_multiindex = isinstance(data.columns, pd.MultiIndex)
            
            prev_prev = data.iloc[-3]
            prev = data.iloc[-2]
            curr = data.iloc[-1]
            
            prev_candle = strat_type(prev_prev, prev, ticker)
            curr_candle = strat_type(prev, curr, ticker)
            
            # Skip if error in calculation
            if "Error" in prev_candle or "Error" in curr_candle:
                continue
            
            if (not prev_patterns or prev_candle in prev_patterns) and \
               (not curr_patterns or curr_candle in curr_patterns):
                
                # Get current close price handling MultiIndex
                if is_multiindex:
                    curr_close = float(curr[("Close", ticker)])
                    curr_open = float(curr[("Open", ticker)])
                else:
                    curr_close = float(curr["Close"])
                    curr_open = float(curr["Open"])
                
                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": "Up" if curr_close > curr_open else "Down",
                    "Close Price": round(curr_close, 2),
                })
                
        except Exception as e:
            if debug_mode:
                st.error(f"Error with {ticker}: {e}")
            continue
    
    progress_bar.empty()
    status_text.empty()
    
    if results:
        df = pd.DataFrame(results)
        st.success(f"Found **{len(df)}** matching tickers")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "strat_results.csv", "text/csv")
    else:
        st.error("No tickers matched. Enable Debug Mode to troubleshoot.")
        
        # Troubleshooting tips
        with st.expander("🔧 Troubleshooting Tips"):
            st.markdown("""
            1. **Check yfinance version**: Run `pip install yfinance --upgrade`
            2. **Test single ticker**: Try running `yf.download('AAPL', period='5d')` in Python
            3. **Check columns**: New yfinance returns MultiIndex columns like `('Close', 'AAPL')`
            4. **Rate limiting**: Yahoo may block excessive requests. Wait 1-2 minutes and retry.
            """)
