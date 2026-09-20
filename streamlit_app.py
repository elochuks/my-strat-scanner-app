import streamlit as st
import yfinance as yf
import pandas as pd
import time


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="STRAT Market Scanner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 S&P 500 + Nasdaq-100 STRAT Scanner")

st.caption(
    "Weekly and Monthly STRAT scanners with previous-period "
    "liquidity sweeps, reclaim/rejection, actionable candles, "
    "FTFC and relative volume."
)


# ============================================================
# S&P 500 UNIVERSE
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
            raise ValueError(
                "S&P 500 dataset missing Symbol column."
            )

        tickers = (
            df["Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .tolist()
        )

        tickers = [
            ticker.replace(".", "-")
            for ticker in tickers
        ]

        return sorted(set(tickers))

    except Exception as e:

        st.error(
            f"Unable to load S&P 500 tickers: {e}"
        )

        return []


# ============================================================
# NASDAQ-100 UNIVERSE
#
# STATIC LIST TO AVOID 403 ERRORS
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_nasdaq100_tickers():

    tickers = [
        "AAPL",
        "ABNB",
        "ADBE",
        "ADI",
        "ADP",
        "ADSK",
        "AEP",
        "AMAT",
        "AMD",
        "AMGN",
        "AMZN",
        "APP",
        "ARM",
        "ASML",
        "AVGO",
        "AXON",
        "BKNG",
        "BKR",
        "CCEP",
        "CDNS",
        "CDW",
        "CEG",
        "CHTR",
        "CMCSA",
        "COST",
        "CPRT",
        "CRWD",
        "CSCO",
        "CSX",
        "CTAS",
        "CTSH",
        "DASH",
        "DDOG",
        "DXCM",
        "EA",
        "EXC",
        "FANG",
        "FAST",
        "FTNT",
        "GEHC",
        "GFS",
        "GILD",
        "GOOG",
        "GOOGL",
        "HON",
        "IDXX",
        "INTC",
        "INTU",
        "ISRG",
        "KDP",
        "KHC",
        "KLAC",
        "LIN",
        "LRCX",
        "MAR",
        "MCHP",
        "MDLZ",
        "MELI",
        "META",
        "MNST",
        "MRVL",
        "MSFT",
        "MSTR",
        "MU",
        "NFLX",
        "NVDA",
        "NXPI",
        "ODFL",
        "ORLY",
        "PANW",
        "PAYX",
        "PCAR",
        "PDD",
        "PEP",
        "PLTR",
        "PYPL",
        "QCOM",
        "REGN",
        "ROP",
        "ROST",
        "SBUX",
        "SNPS",
        "TEAM",
        "TMUS",
        "TSLA",
        "TTD",
        "TTWO",
        "TXN",
        "VRSK",
        "VRTX",
        "WBD",
        "WDAY",
        "XEL",
        "ZS"
    ]

    tickers = [
        ticker
        .strip()
        .upper()
        .replace(".", "-")
        for ticker in tickers
        if ticker.strip()
    ]

    return sorted(set(tickers))


# ============================================================
# DOWNLOAD MARKET DATA
#
# ONE DOWNLOAD SUPPORTS BOTH TABS
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    results = {}

    if not tickers:
        return results

    tickers = sorted(set(tickers))

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

            # =================================================
            # MULTIPLE TICKERS
            # =================================================

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

                            results[
                                ticker
                            ] = ticker_df

                    except Exception:
                        continue

            # =================================================
            # SINGLE TICKER
            # =================================================

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
