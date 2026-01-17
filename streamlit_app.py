import streamlit as st
import yfinance as yf
import pandas as pd

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (HARDENED & CLOUD-SAFE)
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    # -----------------------------
    # S&P 500
    # -----------------------------
    try:
        sp500_url = (
            "https://raw.githubusercontent.com/"
            "datasets/s-and-p-500-companies/master/data/constituents.csv"
        )
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")

    # -----------------------------
    # ETFs
    # -----------------------------
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

    # -----------------------------
    # Indexes
    # -----------------------------
    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)

    tickers = sorted(tickers)

    if not tickers:
        raise RuntimeError("No tickers loaded")

    return tickers


TICKERS = load_tickers()

# =====================================================
# SAFE YFINANCE DOWNLOAD (CACHED + NO THREADING)
# =====================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_price_data(ticker, period, interval):
    return yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,  # 🔑 CRITICAL FIX
    )


# =====================================================
# STRAT CANDLE LOGIC
# =====================================================
def strat_type(prev, curr):
    prev_h, prev_l = float(prev["High"]), float(prev["Low"])
    curr_h, curr_l = float(curr["High"]), float(curr["Low"])
    curr_o, curr_c = float(curr["Open"]), float(curr["Close"])

    candle_color = "Green" if curr_c > curr_o else "Red"

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
st.caption(f"Scanning universe: **{len(TICKERS)}** tickers")

timeframe = st.selectbox(
    "Select Timeframe",
    ["4-Hour", "2-Day", "Daily", "2-Week", "Weekly", "Monthly", "3-Month"],
)

interval_map = {
    "4-Hour": "4h",
    "2-Day": "2d",
    "Daily": "1d",
    "2-Week": "2wk",
    "Weekly": "1wk",
    "Monthly": "1mo",
    "3-Month": "3mo",
}

available_patterns = [
    "1 (Inside)", "3 (Outside)",
    "2U Red", "2U Green",
    "2D Red", "2D Green"
]

st.subheader("STRAT Filters")

prev_patterns = st.multiselect(
    "Previous Candle",
    options=available_patterns,
    default=available_patterns,
)

curr_patterns = st.multiselect(
    "Current Candle",
    options=available_patterns,
    default=available_patterns,
)

use_ftfc = st.checkbox("Include FTFC (Weekly / Monthly)", value=True)

max_tickers = st.slider(
    "Max tickers to scan (performance control)",
    min_value=50,
    max_value=600,
    value=200,
    step=25,
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
                    period="9mo",
                    interval=interval_map[timeframe],
                )

                if data.empty or len(data) < 3:
                    continue

                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if prev_candle not in prev_patterns or curr_candle not in curr_patterns:
                    continue

                ftfc_str = "N/A"

                if use_ftfc:
                    ftfc = []

                    monthly = get_price_data(ticker, "12mo", "1mo")
                    if not monthly.empty:
                        ftfc.append(
                            "M: Bullish"
                            if curr["Close"] > monthly.iloc[-1]["Open"]
                            else "M: Bearish"
                        )

                    weekly = get_price_data(ticker, "12mo", "1wk")
                    if not weekly.empty:
                        ftfc.append(
                            "W: Bullish"
                            if curr["Close"] > weekly.iloc[-1]["Open"]
                            else "W: Bearish"
                        )

                    ftfc_str = ", ".join(ftfc)

                results.append({
                    "Ticker": ticker,
                    "Previous Candle": prev_candle,
                    "Current Candle": curr_candle,
                    "Direction": "Up" if curr["Close"] > curr["Open"] else "Down",
                    "Close Price": round(float(curr["Close"]), 2),
                    "FTFC": ftfc_str,
                })

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"✅ Found {len(df)} matching tickers")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No tickers matched the selected STRAT criteria.")
