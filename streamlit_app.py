import streamlit as st
import yfinance as yf
import pandas as pd

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    try:
        url = (
            "https://raw.githubusercontent.com/"
            "datasets/s-and-p-500-companies/master/data/constituents.csv"
        )
        df = pd.read_csv(url)
        tickers.update(df["Symbol"].dropna().tolist())
    except Exception:
        pass

    tickers.update([
        "SPY","QQQ","IWM","DIA","IVV","VOO",
        "XLF","XLK","XLE","XLV","XLY","XLP",
        "TLT","IEF","GLD","SLV",
        "^GSPC","^NDX","^DJI","^RUT","^VIX"
    ])

    return sorted(tickers)


TICKERS = load_tickers()

# =====================================================
# SAFE YFINANCE DOWNLOAD
# =====================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_price_data(ticker, period, interval):
    return yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,
    )

# =====================================================
# STRAT LOGIC (FIXED)
# =====================================================
def strat_type(prev, curr):
    prev_h, prev_l = float(prev["High"]), float(prev["Low"])
    curr_h, curr_l = float(curr["High"]), float(curr["Low"])
    curr_o, curr_c = float(curr["Open"]), float(curr["Close"])

    # Normalize color
    color = "Green" if curr_c >= curr_o else "Red"

    if curr_h < prev_h and curr_l > prev_l:
        return "1 (Inside)"
    elif curr_h > prev_h and curr_l < prev_l:
        return "3 (Outside)"
    elif curr_h > prev_h:
        return f"2U {color}"
    elif curr_l < prev_l:
        return f"2D {color}"
    else:
        return "1 (Inside)"  # never undefined

# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Universe size: **{len(TICKERS)}**")

timeframe = st.selectbox(
    "Timeframe",
    ["4-Hour", "Daily", "Weekly", "Monthly"]
)

interval_map = {
    "4-Hour": "4h",
    "Daily": "1d",
    "Weekly": "1wk",
    "Monthly": "1mo",
}

available_patterns = [
    "1 (Inside)", "3 (Outside)",
    "2U Green", "2U Red",
    "2D Green", "2D Red"
]

st.subheader("STRAT Filters")

prev_patterns = st.multiselect(
    "Previous Candle (optional)",
    available_patterns,
    default=[]
)

curr_patterns = st.multiselect(
    "Current Candle",
    available_patterns,
    default=available_patterns
)

use_ftfc = st.checkbox("Include FTFC (Weekly / Monthly)", value=True)

show_all = st.checkbox("Ignore STRAT filters (debug)", value=False)

max_tickers = st.slider(
    "Max tickers to scan",
    25, 600, 200, 25
)

scan_button = st.button("🚀 Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan_button:
    results = []

    with st.spinner("Scanning market..."):
        for ticker in TICKERS[:max_tickers]:
            try:
                data = get_price_data(
                    ticker,
                    "9mo",
                    interval_map[timeframe]
                )

                if data.empty or len(data) < 3:
                    continue

                pprev, prev, curr = data.iloc[-3], data.iloc[-2], data.iloc[-1]

                prev_candle = strat_type(pprev, prev)
                curr_candle = strat_type(prev, curr)

                if not show_all:
                    if prev_patterns and prev_candle not in prev_patterns:
                        continue
                    if curr_patterns and curr_candle not in curr_patterns:
                        continue

                ftfc = "N/A"

                if use_ftfc:
                    tfc = []

                    m = get_price_data(ticker, "12mo", "1mo")
                    if not m.empty:
                        tfc.append(
                            "M: Bullish" if curr["Close"] > m.iloc[-1]["Open"]
                            else "M: Bearish"
                        )

                    w = get_price_data(ticker, "12mo", "1wk")
                    if not w.empty:
                        tfc.append(
                            "W: Bullish" if curr["Close"] > w.iloc[-1]["Open"]
                            else "W: Bearish"
                        )

                    ftfc = ", ".join(tfc)

                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": "Up" if curr["Close"] >= curr["Open"] else "Down",
                    "Close": round(float(curr["Close"]), 2),
                    "FTFC": ftfc
                })

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"✅ {len(df)} results found")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No results — loosen filters or enable debug mode.")
