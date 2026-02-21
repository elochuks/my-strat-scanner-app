import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="STRAT Scanner", layout="wide")

# =====================================================
# LOAD TICKERS (HARDENED & CLOUD-SAFE)
# =====================================================
@st.cache_data(ttl=86400)
def load_tickers():
    tickers = set()

    try:
        sp500_url = (
            "https://raw.githubusercontent.com/"
            "datasets/s-and-p-500-companies/master/data/constituents.csv"
        )
        sp500_df = pd.read_csv(sp500_url)
        tickers.update(sp500_df["Symbol"].dropna().tolist())
    except Exception as e:
        st.warning(f"S&P 500 load failed: {e}")

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

    indexes = ["^GSPC", "^NDX", "^DJI", "^RUT", "^VIX"]
    tickers.update(indexes)

    tickers = sorted(tickers)

    if not tickers:
        raise RuntimeError("No tickers loaded")

    return tickers


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
st.caption(f"Scanning **{len(TICKERS)}** tickers (S&P 500 + ETFs + Indexes)")

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
}

available_patterns = [
    "1 (Inside)", "3 (Outside)",
    "2U Red", "2U Green",
    "2D Red", "2D Green"
]

st.subheader("STRAT Pattern Filters")

prev_patterns = st.multiselect(
    "Previous Candle Patterns",
    options=available_patterns,
    default=available_patterns,
)

curr_patterns = st.multiselect(
    "Current Candle Patterns",
    options=available_patterns,
    default=available_patterns,
)

scan_button = st.button("Run Scanner")

# =====================================================
# SCANNER
# =====================================================
if scan_button:
    results = []

    with st.spinner("Scanning market..."):
        for ticker in TICKERS:
            try:

                # =========================
                # 3-MONTH (Quarterly FIX)
                # =========================
                if timeframe == "3-Month":
                    data = yf.download(
                        ticker,
                        period="3y",     # enough data for quarters
                        interval="1mo",
                        progress=False,
                        auto_adjust=False,
                    )

                    if data.empty:
                        continue

                    # Proper Quarterly Candles
                    data = data.resample("Q").agg({
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum"
                    }).dropna()

                else:
                    data = yf.download(
                        ticker,
                        period="9mo",
                        interval=interval_map[timeframe],
                        progress=False,
                        auto_adjust=False,
                    )

                if data.empty or len(data) < 3:
                    continue

                prev_prev = data.iloc[-3]
                prev = data.iloc[-2]
                curr = data.iloc[-1]

                prev_candle = strat_type(prev_prev, prev)
                curr_candle = strat_type(prev, curr)

                if (
                    (not prev_patterns or prev_candle in prev_patterns)
                    and (not curr_patterns or curr_candle in curr_patterns)
                ):

                    ftfc_result = []

                    monthly_data = yf.download(
                        ticker, period="12mo", interval="1mo",
                        progress=False, auto_adjust=False
                    )
                    if not monthly_data.empty:
                        current_month_open = monthly_data.iloc[-1]["Open"]
                        if float(curr["Close"]) > float(current_month_open):
                            ftfc_result.append("M: Bullish")
                        elif float(curr["Close"]) < float(current_month_open):
                            ftfc_result.append("M: Bearish")

                    weekly_data = yf.download(
                        ticker, period="12mo", interval="1wk",
                        progress=False, auto_adjust=False
                    )
                    if not weekly_data.empty:
                        current_week_open = weekly_data.iloc[-1]["Open"]
                        if float(curr["Close"]) > float(current_week_open):
                            ftfc_result.append("W: Bullish")
                        elif float(curr["Close"]) < float(current_week_open):
                            ftfc_result.append("W: Bearish")

                    ftfc_str = ", ".join(ftfc_result) if ftfc_result else "N/A"

                    results.append(
                        {
                            "Ticker": ticker,
                            "Previous Candle": prev_candle,
                            "Current Candle": curr_candle,
                            "Direction": "Up" if float(curr["Close"]) > float(curr["Open"]) else "Down",
                            "Close Price": round(float(curr["Close"]), 2),
                            "FTFC": ftfc_str,
                        }
                    )

            except Exception:
                continue

    if results:
        df = pd.DataFrame(results)
        st.success(f"Found {len(df)} matching tickers")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No tickers matched the selected STRAT criteria.")
