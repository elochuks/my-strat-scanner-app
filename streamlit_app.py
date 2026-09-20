import streamlit as st
import yfinance as yf
import pandas as pd
import time


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="S&P 500 + Nasdaq-100 STRAT Scanner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 S&P 500 + Nasdaq-100 STRAT Scanner")

st.caption(
    "Weekly and monthly sweep scanner with STRAT, "
    "reclaims/rejections, actionable candles, FTFC and RVOL."
)


# ============================================================
# S&P 500
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_sp500_tickers():

    url = (
        "https://raw.githubusercontent.com/"
        "datasets/s-and-p-500-companies/"
        "main/data/constituents.csv"
    )

    try:

        df = pd.read_csv(url)

        if "Symbol" not in df.columns:
            return []

        tickers = (
            df["Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .tolist()
        )

        tickers = [
            x.replace(".", "-")
            for x in tickers
        ]

        return sorted(set(tickers))

    except Exception as e:

        st.error(
            f"Unable to load S&P 500: {e}"
        )

        return []


# ============================================================
# NASDAQ-100
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_nasdaq100_tickers():

    tickers = [

        "AAPL", "ABNB", "ADBE", "ADI", "ADP",
        "ADSK", "AEP", "AMAT", "AMD", "AMGN",
        "AMZN", "APP", "ARM", "ASML", "AVGO",
        "AXON", "BKNG", "BKR", "CCEP", "CDNS",
        "CDW", "CEG", "CHTR", "CMCSA", "COST",
        "CPRT", "CRWD", "CSCO", "CSX", "CTAS",
        "CTSH", "DASH", "DDOG", "DXCM", "EA",
        "EXC", "FANG", "FAST", "FTNT", "GEHC",
        "GFS", "GILD", "GOOG", "GOOGL", "HON",
        "IDXX", "INTC", "INTU", "ISRG", "KDP",
        "KHC", "KLAC", "LIN", "LRCX", "MAR",
        "MCHP", "MDLZ", "MELI", "META", "MNST",
        "MRVL", "MSFT", "MSTR", "MU", "NFLX",
        "NVDA", "NXPI", "ODFL", "ORLY", "PANW",
        "PAYX", "PCAR", "PDD", "PEP", "PLTR",
        "PYPL", "QCOM", "REGN", "ROP", "ROST",
        "SBUX", "SNPS", "TEAM", "TMUS", "TSLA",
        "TTD", "TTWO", "TXN", "VRSK", "VRTX",
        "WBD", "WDAY", "XEL", "ZS"
    ]

    return sorted(set(tickers))


# ============================================================
# MARKET DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    all_data = {}

    tickers = sorted(set(tickers))

    if not tickers:
        return all_data

    batch_size = 50

    for start in range(
        0,
        len(tickers),
        batch_size
    ):

        batch = tickers[
            start:start + batch_size
        ]

        try:

            data = yf.download(
                tickers=batch,
                period="1y",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                threads=True,
                progress=False,
                timeout=30
            )

            if data is None or data.empty:
                continue

            if len(batch) > 1:

                if not isinstance(
                    data.columns,
                    pd.MultiIndex
                ):
                    continue

                level0 = (
                    data.columns
                    .get_level_values(0)
                    .unique()
                    .tolist()
                )

                level1 = (
                    data.columns
                    .get_level_values(1)
                    .unique()
                    .tolist()
                )

                for ticker in batch:

                    try:

                        if ticker in level0:

                            ticker_df = (
                                data[ticker]
                                .copy()
                            )

                        elif ticker in level1:

                            ticker_df = (
                                data.xs(
                                    ticker,
                                    axis=1,
                                    level=1
                                )
                                .copy()
                            )

                        else:

                            continue

                        if not ticker_df.empty:

                            all_data[ticker] = (
                                ticker_df
                            )

                    except Exception:

                        continue

            else:

                ticker = batch[0]

                ticker_df = data.copy()

                if isinstance(
                    ticker_df.columns,
                    pd.MultiIndex
                ):

                    if ticker in (
                        ticker_df.columns
                        .get_level_values(0)
                    ):

                        ticker_df = (
                            ticker_df[ticker]
                            .copy()
                        )

                    elif ticker in (
                        ticker_df.columns
                        .get_level_values(1)
                    ):

                        ticker_df = (
                            ticker_df.xs(
                                ticker,
                                axis=1,
                                level=1
                            )
                            .copy()
                        )

                if not ticker_df.empty:

                    all_data[ticker] = (
                        ticker_df
                    )

        except Exception:

            continue

        time.sleep(0.20)

    return all_data


# ============================================================
# CLEAN DATA
# ============================================================

def clean_ticker_dataframe(
    market_data,
    ticker
):

    try:

        if ticker not in market_data:
            return None

        df = market_data[ticker].copy()

        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = [
                col[-1]
                if isinstance(col, tuple)
                else col
                for col in df.columns
            ]

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        if not all(
           
