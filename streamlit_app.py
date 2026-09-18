import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Weekly High/Low Scanner",
    layout="wide"
)

st.title("📊 Previous Week High / Low Scanner")

# ---------------------------------------------------
# TICKERS
# ---------------------------------------------------

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    table = pd.read_html(url)[0]

    tickers = table["Symbol"].tolist()

    # Yahoo Finance uses BRK-B instead of BRK.B
    tickers = [ticker.replace(".", "-") for ticker in tickers]

    return tickers


# ---------------------------------------------------
# DOWNLOAD DATA
# ---------------------------------------------------

@st.cache_data(ttl=900)
def download_data(tickers):

    data = yf.download(
        tickers,
        period="3mo",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False
    )

    return data


# ---------------------------------------------------
# SCANNER LOGIC
# ---------------------------------------------------

def scan_market(tickers, data):

    results = []

    for ticker in tickers:

        try:

            df = data[ticker].copy()

            df = df.dropna()

            if len(df) < 10:
                continue

            # Make sure index is datetime
            df.index = pd.to_datetime(df.index)

            # ---------------------------------------
            # Create weekly candles
            # ---------------------------------------

            weekly = df.resample("W-FRI").agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum"
            })

            weekly = weekly.dropna()

            if len(weekly) < 2:
                continue

            # ---------------------------------------
            # Previous completed week
            # ---------------------------------------

            previous_week = weekly.iloc[-2]

            previous_week_high = previous_week["High"]
            previous_week_low = previous_week["Low"]

            # ---------------------------------------
            # Current week
            # ---------------------------------------

            current_week = weekly.iloc[-1]

            current_week_high = current_week["High"]
            current_week_low = current_week["Low"]
            current_price = df["Close"].iloc[-1]

            # ---------------------------------------
            # Sweep logic
            # ---------------------------------------

            high_taken = current_week_high > previous_week_high

            low_taken = current_week_low < previous_week_low

            # ---------------------------------------
            # Reclaim logic
            # ---------------------------------------

            high_rejected = (
                high_taken
                and current_price < previous_week_high
            )

            low_reclaimed = (
                low_taken
                and current_price > previous_week_low
            )

            # ---------------------------------------
            # Signal
            # ---------------------------------------

            if low_taken and high_taken:
                signal = "Both Taken"

            elif low_taken:
                signal = "Previous Week Low Taken"

            elif high_taken:
                signal = "Previous Week High Taken"

            else:
                continue

            results.append({

                "Ticker": ticker,

                "Price": round(float(current_price), 2),

                "Previous Week High":
                    round(float(previous_week_high), 2),

                "Previous Week Low":
                    round(float(previous_week_low), 2),

                "Current Week High":
                    round(float(current_week_high), 2),

                "Current Week Low":
                    round(float(current_week_low), 2),

                "High Taken":
                    high_taken,

                "Low Taken":
                    low_taken,

                "High Rejected":
                    high_rejected,

                "Low Reclaimed":
                    low_reclaimed,

                "Signal":
                    signal
            })

        except Exception:
            continue

    return pd.DataFrame(results)


# ---------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------

tickers = get_sp500_tickers()

st.sidebar.header("Scanner Settings")

scan_type = st.sidebar.selectbox(
    "Signal",
    [
        "All",
        "Previous Week Low Taken",
        "Previous Week High Taken",
        "Both Taken",
        "Low Taken + Reclaimed",
        "High Taken + Rejected"
    ]
)

if st.sidebar.button("Run Scanner"):

    with st.spinner("Scanning market..."):

        data = download_data(tickers)

        results = scan_market(
            tickers,
            data
        )

    # -----------------------------------------------
    # FILTERS
    # -----------------------------------------------

    if not results.empty:

        if scan_type == "Previous Week Low Taken":

            results = results[
                results["Low Taken"] == True
            ]

        elif scan_type == "Previous Week High Taken":

            results = results[
                results["High Taken"] == True
            ]

        elif scan_type == "Both Taken":

            results = results[
                (results["Low Taken"] == True)
                &
                (results["High Taken"] == True)
            ]

        elif scan_type == "Low Taken + Reclaimed":

            results = results[
                results["Low Reclaimed"] == True
            ]

        elif scan_type == "High Taken + Rejected":

            results = results[
                results["High Rejected"] == True
            ]

    # -----------------------------------------------
    # OUTPUT
    # -----------------------------------------------

    if results.empty:

        st.warning("No stocks found.")

    else:

        st.success(
            f"{len(results)} stocks found"
        )

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True
        )
