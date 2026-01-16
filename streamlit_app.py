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

    # -----------------------------
    # S&P 500 (stable & live)
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
    # ETFs (curated, stable list)
    # -----------------------------
    etfs = [
        # Index ETFs
        "SPY", "IVV", "VOO", "QQQ", "DIA", "IWM",

        # Sector ETFs
        "XLF", "XLK", "XLE", "XLY", "XLP", "XLV",
        "XLI", "XLB", "XLRE", "XLU", "XLC",

        # Growth / Value
        "VUG", "VTV", "IWF", "IWD",

        # Bonds
        "TLT", "IEF", "SHY", "LQD", "HYG",

        # Commodities
        "GLD", "SLV", "USO", "UNG",

        # Volatility / Inverse
        "VXX", "SQQQ", "TQQQ"
    ]
    tickers.update(etfs)

    # -----------------------------
    # Indexes (Yahoo symbols)
    # -----------------------------
    indexes = [
        "^GSPC",  # S&P 500
        "^NDX",   # Nasdaq 100
        "^DJI",   # Dow Jones
        "^RUT",   # Russell 2000
        "^VIX",   # Volatility Index
    ]
    tickers.update(indexes)

    # -----------------------------
    # Final cleanup
    # -----------------------------
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

    # Determine candle color
    candle_color = "Green" if curr_c > curr_o else "Red"

    # STRAT logic
    if curr_h < prev_h and curr_l > prev_l:
        return "1 (Inside)"
    elif curr_h > prev_h and curr_l < prev_l:
        return "3 (Outside)"
    elif curr_h > prev_h:
        return f"2U {candle_color}"  # 2U Red / 2U Green
    elif curr_l < prev_l:
        return f"2D {candle_color}"  # 2D Red / 2D Green
    else:
        return "Undefined"


# =====================================================
# UI
# =====================================================
st.title("📊 STRAT Scanner")
st.caption(f"Scanning **{len(TICKERS)}** tickers (S&P 500 + ETFs + Indexes)")

# Timeframes
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

# STRAT patterns with color options
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
                    results.append(
                        {
                            "Ticker": ticker,
                            "Previous Candle": prev_candle,
                            "Current Candle": curr_candle,
                            "Direction": "Up"
                            if float(curr["Close"]) > float(curr["Open"])
                            else "Down",
                            "Close Price": round(float(curr["Close"]), 2),
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
