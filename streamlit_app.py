import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (HARDENED & CLOUD-SAFE)
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    # S&P 500 (fixed URL)
    try:
        sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")

    # ETFs (curated list)
    etfs = [
        "SPY", "IVV", "VOO", "QQQ", "DIA", "IWM",
        "XLF", "XLK", "XLE", "XLY", "XLP", "XLV",
        "XLI", "XLB", "XLRE", "XLU", "XLC",
        "VUG", "VTV", "IWF", "IWD",
        "TLT", "IEF", "SHY", "LQD", "HYG",
        "GLD", "SLV", "USO", "UNG",
        "VXX", "SQQQ", "TQQQ"
    ]
    tickers.update(etfs)

    # Indexes
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)

    return sorted(tickers)

TICKERS = load_tickers()

# =====================================================
# STRAT CANDLE LOGIC WITH COLOR
# =====================================================
def strat_type(prev, curr):
    prev_h = float(prev["High"])
    prev_l = float(prev["Low"])
    curr_h = float(curr["High"])
    curr_l = float(curr["Low"])
    curr_o = float(curr["Open"])
    curr_c = float(curr["Close"])

    candle_color = "Green" if curr_c >= curr_o else "Red"  # Changed to >= for doji handling

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
# FTFC CALCULATION (OPTIMIZED)
# =====================================================
@st.cache_data(ttl=3600)
def get_ftfc_data(ticker):
    """Pre-fetch FTFC data to avoid nested API calls"""
    ftfc_result = []
    
    try:
        # Monthly
        monthly = yf.download(ticker, period="3mo", interval="1mo", progress=False, auto_adjust=True)
        if len(monthly) >= 2:
            current_month_open = float(monthly.iloc[-1]["Open"])
            current_price = float(monthly.iloc[-1]["Close"])
            if current_price > current_month_open:
                ftfc_result.append("M: Bullish")
            elif current_price < current_month_open:
                ftfc_result.append("M: Bearish")
    except:
        pass
    
    try:
        # Weekly
        weekly = yf.download(ticker, period="3mo", interval="1wk", progress=False, auto_adjust=True)
        if len(weekly) >= 2:
            current_week_open = float(weekly.iloc[-1]["Open"])
            current_price = float(weekly.iloc[-1]["Close"])
            if current_price > current_week_open:
                ftfc_result.append("W: Bullish")
            elif current_price < current_week_open:
                ftfc_result.append("W: Bearish")
    except:
        pass
    
    return ", ".join(ftfc_result) if ftfc_result else "N/A"

# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers (S&P 500 + ETFs + Indexes)")

timeframe = st.selectbox(
    "Select Timeframe",
    ["4-Hour", "Daily", "Weekly", "Monthly"],  # Removed invalid yfinance intervals
)

interval_map = {
    "4-Hour": "1h",  # yfinance doesn't have 4h, use 1h and resample or use 1h
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo",
}

# Note: 2d, 2wk, 3mo are not valid yfinance intervals

available_patterns = [
    "1 (Inside)", "3 (Outside)",
    "2U Red", "2U Green",
    "2D Red", "2D Green"
]

st.subheader("STRAT Pattern Filters")

prev_patterns = st.multiselect("Previous Candle Patterns", options=available_patterns, default=available_patterns)
curr_patterns = st.multiselect("Current Candle Patterns", options=available_patterns, default=available_patterns)

# Add FTFC filter
st.subheader("FTFC Filter")
ftfc_filter = st.multiselect(
    "FTFC Direction",
    options=["Any", "M: Bullish", "M: Bearish", "W: Bullish", "W: Bearish"],
    default=["Any"]
)

scan_button = st.button("Run Scanner", type="primary")

# =====================================================
# SCANNER (OPTIMIZED)
# =====================================================
if scan_button:
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_tickers = len(TICKERS)
    
    for idx, ticker in enumerate(TICKERS):
        try:
            # Update progress
            progress = (idx + 1) / total_tickers
            progress_bar.progress(min(progress, 0.99))
            status_text.text(f"Scanning {ticker}... ({idx+1}/{total_tickers})")
            
            # Download data
            data = yf.download(
                ticker,
                period="6mo",  # Reduced for speed
                interval=interval_map[timeframe],
                progress=False,
                auto_adjust=True,  # Use adjusted prices
            )

            if data.empty or len(data) < 3:
                continue

            # Get last 3 candles
            prev_prev = data.iloc[-3]
            prev = data.iloc[-2]
            curr = data.iloc[-1]

            prev_candle = strat_type(prev_prev, prev)
            curr_candle = strat_type(prev, curr)

            # Pattern matching
            if (not prev_patterns or prev_candle in prev_patterns) and \
               (not curr_patterns or curr_candle in curr_patterns):
                
                # Get FTFC (cached)
                ftfc_str = get_ftfc_data(ticker)
                
                # Apply FTFC filter
                if "Any" not in ftfc_filter:
                    if not any(f in ftfc_str for f in ftfc_filter):
                        continue
                
                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": "Up" if float(curr["Close"]) > float(curr["Open"]) else "Down",
                    "Close Price": round(float(curr["Close"]), 2),
                    "FTFC": ftfc_str,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

        except Exception as e:
            continue
    
    progress_bar.empty()
    status_text.empty()

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found **{len(df)}** matching tickers out of {total_tickers} scanned")
        
        # Add export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "strat_scan_results.csv", "text/csv")
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("No tickers matched the selected STRAT criteria.")
