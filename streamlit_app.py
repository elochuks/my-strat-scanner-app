import time

import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="STRAT Market Scanner",
    page_icon="📊",
    layout="wide",
)

st.title("📊 STRAT Market Scanner")

st.caption(
    "S&P 500 + Nasdaq-100 + ETFs | "
    "Weekly / Monthly Liquidity Sweeps | "
    "STRAT | FTFC | RVOL | ATR % | Market Context"
)


# ============================================================
# CONSTANTS
# ============================================================

STRAT_OPTIONS = [
    "All",
    "1 Inside",
    "2U Green",
    "2U Red",
    "2D Green",
    "2D Red",
    "3 Outside",
    "N/A",
]

BULLISH_PATTERNS = [
    "2U Green",
    "2D Green",
    "2U Red",
    "1 Inside",
    "3 Outside",
]

BEARISH_PATTERNS = [
    "2D Red",
    "2U Red",
    "2D Green",
    "1 Inside",
    "3 Outside",
]

ETF_NAMES = {
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq-100 ETF",
    "IWM": "Russell 2000 ETF",
    "XLC": "Communication Services ETF",
    "XLY": "Consumer Discretionary ETF",
    "XLP": "Consumer Staples ETF",
    "XLE": "Energy ETF",
    "XLF": "Financials ETF",
    "XLV": "Health Care ETF",
    "XLI": "Industrials ETF",
    "XLB": "Materials ETF",
    "XLRE": "Real Estate ETF",
    "XLK": "Technology ETF",
    "XLU": "Utilities ETF",
}

MARKET_CONTEXT_TICKERS = [
    "SPY",
    "QQQ",
    "IWM",
    "^VIX",
    "XLC",
    "XLY",
    "XLP",
    "XLE",
    "XLF",
    "XLV",
    "XLI",
    "XLB",
    "XLRE",
    "XLK",
    "XLU",
]

MARKET_CONTEXT_NAMES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq-100",
    "IWM": "Russell 2000",
    "^VIX": "VIX",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLK": "Technology",
    "XLU": "Utilities",
}

SECTOR_TICKERS = [
    "XLC",
    "XLY",
    "XLP",
    "XLE",
    "XLF",
    "XLV",
    "XLI",
    "XLB",
    "XLRE",
    "XLK",
    "XLU",
]


# ============================================================
# UNIVERSES
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

    except Exception as exc:

        st.error(
            f"Could not load S&P 500 list: {exc}"
        )

        return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_nasdaq100_tickers():

    # Static fallback list.
    # You can replace this later with a maintained CSV/API source.

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
        "WBD", "WDAY", "XEL", "ZS",
    ]

    return sorted(set(tickers))


@st.cache_data(ttl=86400, show_spinner=False)
def get_etf_tickers():

    return sorted(
        {
            "SPY",
            "QQQ",
            "IWM",
            "XLC",
            "XLY",
            "XLP",
            "XLE",
            "XLF",
            "XLV",
            "XLI",
            "XLB",
            "XLRE",
            "XLK",
            "XLU",
        }
    )


def get_asset_type(ticker):

    if ticker in ETF_NAMES:
        return ETF_NAMES[ticker]

    if ticker == "^VIX":
        return "Volatility Index"

    return "Stock"


# ============================================================
# MARKET DATA DOWNLOAD
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    tickers = sorted(set(tickers))

    results = {}

    if not tickers:
        return results

    batch_size = 50

    for start in range(
        0,
        len(tickers),
        batch_size,
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
                timeout=30,
            )

            if (
                data is None
                or data.empty
            ):
                continue

            # ----------------------------------------------
            # MULTIPLE TICKERS
            # ----------------------------------------------

            if len(batch) > 1:

                if not isinstance(
                    data.columns,
                    pd.MultiIndex,
                ):
                    continue

                level0 = set(
                    data.columns
                    .get_level_values(0)
                )

                level1 = set(
                    data.columns
                    .get_level_values(1)
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
                                    level=1,
                                )
                                .copy()
                            )

                        else:
                            continue

                        if not ticker_df.empty:

                            results[ticker] = (
                                ticker_df
                            )

                    except Exception:
                        continue

            # ----------------------------------------------
            # SINGLE TICKER
            # ----------------------------------------------

            else:

                ticker = batch[0]

                ticker_df = data.copy()

                if isinstance(
                    ticker_df.columns,
                    pd.MultiIndex,
                ):

                    level0 = set(
                        ticker_df.columns
                        .get_level_values(0)
                    )

                    level1 = set(
                        ticker_df.columns
                        .get_level_values(1)
                    )

                    if ticker in level0:

                        ticker_df = (
                            ticker_df[ticker]
                            .copy()
                        )

                    elif ticker in level1:

                        ticker_df = (
                            ticker_df.xs(
                                ticker,
                                axis=1,
                                level=1,
                            )
                            .copy()
                        )

                if not ticker_df.empty:

                    results[ticker] = (
                        ticker_df
                    )

        except Exception:
            continue

        time.sleep(0.10)

    return results


# ============================================================
# CLEAN DATA
# ============================================================

def clean_ticker_dataframe(
    market_data,
    ticker,
):

    try:

        if ticker not in market_data:
            return None

        df = market_data[
            ticker
        ].copy()

        if isinstance(
            df.columns,
            pd.MultiIndex,
        ):

            flattened = []

            for column in df.columns:

                if isinstance(
                    column,
                    tuple,
                ):

                    candidates = [
                        str(value)
                        for value in column
                        if str(value)
                        in {
                            "Open",
                            "High",
                            "Low",
                            "Close",
                            "Adj Close",
                            "Volume",
                        }
                    ]

                    if candidates:
                        flattened.append(
                            candidates[0]
                        )
                    else:
                        flattened.append(
                            str(column[-1])
                        )

                else:

                    flattened.append(
                        str(column)
                    )

            df.columns = flattened

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        if not all(
            column in df.columns
            for column in required
        ):
            return None

        df = df[
            required
        ].copy()

        for column in required:

            df[column] = (
                pd.to_numeric(
                    df[column],
                    errors="coerce",
                )
            )

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ]
        )

        if df.empty:
            return None

        df.index = pd.to_datetime(
            df.index
        )

        try:

            df.index = (
                df.index
                .tz_localize(None)
            )

        except Exception:
            pass

        df = (
            df[
                ~df.index.duplicated(
                    keep="last"
                )
            ]
            .sort_index()
        )

        return df

    except Exception:
        return None


# ============================================================
# STRAT
# ============================================================

def classify_strat_candle(
    current_open,
    current_high,
    current_low,
    current_close,
    previous_high,
    previous_low,
):

    if (
        current_high > previous_high
        and
        current_low < previous_low
    ):
        return "3 Outside"

    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):
        return "1 Inside"

    if current_high > previous_high:

        if current_close >= current_open:
            return "2U Green"

        return "2U Red"

    if current_low < previous_low:

        if current_close >= current_open:
            return "2D Green"

        return "2D Red"

    return "N/A"


def get_daily_strat(df):

    if (
        df is None
        or len(df) < 2
    ):
        return "N/A"

    previous = df.iloc[-2]
    current = df.iloc[-1]

    return classify_strat_candle(
        float(current["Open"]),
        float(current["High"]),
        float(current["Low"]),
        float(current["Close"]),
        float(previous["High"]),
        float(previous["Low"]),
    )


# ============================================================
# ACTIONABLE CANDLE
# ============================================================

def classify_actionable_candle(
    current_open,
    current_high,
    current_low,
    current_close,
    previous_high,
    previous_low,
):

    candle_range = (
        current_high
        - current_low
    )

    if candle_range <= 0:
        return None

    body = abs(
        current_close
        - current_open
    )

    upper_wick = (
        current_high
        - max(
            current_open,
            current_close,
        )
    )

    lower_wick = (
        min(
            current_open,
            current_close,
        )
        - current_low
    )

    body_for_ratio = max(
        body,
        candle_range * 0.05,
    )

    # Priority 1: Inside Bar

    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):
        return "Inside Bar"

    # Priority 2: Hammer

    if (
        lower_wick
        >= 2 * body_for_ratio
        and
        upper_wick
        <= body_for_ratio
        and
        body
        <= candle_range * 0.40
    ):
        return "Hammer"

    # Priority 3: Shooting Star

    if (
        upper_wick
        >= 2 * body_for_ratio
        and
        lower_wick
        <= body_for_ratio
        and
        body
        <= candle_range * 0.40
    ):
        return "Shooting Star"

    return None


# ============================================================
# WEEKLY / MONTHLY AGGREGATION
# ============================================================

def build_weekly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index
        .to_period("W-FRI")
    )

    temp["TradingDate"] = (
        temp.index
    )

    weekly = (
        temp.groupby("Period")
        .agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum"),
            FirstDate=(
                "TradingDate",
                "first",
            ),
            LastDate=(
                "TradingDate",
                "last",
            ),
        )
    )

    return weekly


def build_monthly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index
        .to_period("M")
    )

    temp["TradingDate"] = (
        temp.index
    )

    monthly = (
        temp.groupby("Period")
        .agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum"),
            FirstDate=(
                "TradingDate",
                "first",
            ),
            LastDate=(
                "TradingDate",
                "last",
            ),
        )
    )

    return monthly


# ============================================================
# WEEKLY LEVELS
# ============================================================

def get_weekly_levels(df):

    weekly = build_weekly_dataframe(
        df
    )

    if len(weekly) < 3:
        return None

    current_period = (
        df.index[-1]
        .to_period("W-FRI")
    )

    if current_period not in weekly.index:
        return None

    completed = weekly[
        weekly.index
        < current_period
    ]

    if len(completed) < 2:
        return None

    current = weekly.loc[
        current_period
    ]

    previous = completed.iloc[-1]
    two_back = completed.iloc[-2]

    previous_strat = (
        classify_strat_candle(
            float(previous["Open"]),
            float(previous["High"]),
            float(previous["Low"]),
            float(previous["Close"]),
            float(two_back["High"]),
            float(two_back["Low"]),
        )
    )

    current_strat = (
        classify_strat_candle(
            float(current["Open"]),
            float(current["High"]),
            float(current["Low"]),
            float(current["Close"]),
            float(previous["High"]),
            float(previous["Low"]),
        )
    )

    return {
        "previous_high":
            float(previous["High"]),

        "previous_low":
            float(previous["Low"]),

        "previous_strat":
            previous_strat,

        "current_open":
            float(current["Open"]),

        "current_high":
            float(current["High"]),

        "current_low":
            float(current["Low"]),

        "current_close":
            float(current["Close"]),

        "current_strat":
            current_strat,

        "current_period":
            current_period,
    }


# ============================================================
# MONTHLY LEVELS
# ============================================================

def get_monthly_levels(df):

    monthly = build_monthly_dataframe(
        df
    )

    if len(monthly) < 3:
        return None

    current_period = (
        df.index[-1]
        .to_period("M")
    )

    if current_period not in monthly.index:
        return None

    completed = monthly[
        monthly.index
        < current_period
    ]

    if len(completed) < 2:
        return None

    current = monthly.loc[
        current_period
    ]

    previous = completed.iloc[-1]
    two_back = completed.iloc[-2]

    previous_strat = (
        classify_strat_candle(
            float(previous["Open"]),
            float(previous["High"]),
            float(previous["Low"]),
            float(previous["Close"]),
            float(two_back["High"]),
            float(two_back["Low"]),
        )
    )

    current_strat = (
        classify_strat_candle(
            float(current["Open"]),
            float(current["High"]),
            float(current["Low"]),
            float(current["Close"]),
            float(previous["High"]),
            float(previous["Low"]),
        )
    )

    return {
        "previous_high":
            float(previous["High"]),

        "previous_low":
            float(previous["Low"]),

        "previous_strat":
            previous_strat,

        "current_open":
            float(current["Open"]),

        "current_high":
            float(current["High"]),

        "current_low":
            float(current["Low"]),

        "current_close":
            float(current["Close"]),

        "current_strat":
            current_strat,

        "current_period":
            current_period,
    }


def get_current_week_strat(df):

    levels = get_weekly_levels(
        df
    )

    if levels is None:
        return "N/A"

    return levels[
        "current_strat"
    ]


# ============================================================
# FTFC
# ============================================================

def calculate_ftfc(df):

    try:

        price = float(
            df["Close"]
            .iloc[-1]
        )

        # Weekly FTFC

        current_week = (
            df.index[-1]
            .to_period("W-FRI")
        )

        week_mask = (
            df.index
            .to_period("W-FRI")
            == current_week
        )

        week_data = df[
            week_mask
        ]

        weekly_open = float(
            week_data["Open"]
            .iloc[0]
        )

        if price > weekly_open:
            weekly = "Up"

        elif price < weekly_open:
            weekly = "Down"

        else:
            weekly = "Neutral"

        # Monthly FTFC

        current_month = (
            df.index[-1]
            .to_period("M")
        )

        month_mask = (
            df.index
            .to_period("M")
            == current_month
        )

        month_data = df[
            month_mask
        ]

        monthly_open = float(
            month_data["Open"]
            .iloc[0]
        )

        if price > monthly_open:
            monthly = "Up"

        elif price < monthly_open:
            monthly = "Down"

        else:
            monthly = "Neutral"

        if (
            weekly == "Up"
            and monthly == "Up"
        ):

            alignment = "FTFC Up"

        elif (
            weekly == "Down"
            and monthly == "Down"
        ):

            alignment = "FTFC Down"

        else:

            alignment = "Mixed"

        return {
            "weekly": weekly,
            "monthly": monthly,
            "alignment": alignment,
        }

    except Exception:

        return {
            "weekly": "N/A",
            "monthly": "N/A",
            "alignment": "N/A",
        }


# ============================================================
# RVOL
# ============================================================

def calculate_rvol(
    df,
    lookback=20,
):

    try:

        if (
            df is None
            or len(df)
            < lookback + 1
        ):
            return None

        current_volume = float(
            df["Volume"]
            .iloc[-1]
        )

        previous_volume = (
            df["Volume"]
            .iloc[
                -(lookback + 1):-1
            ]
        )

        average_volume = float(
            previous_volume.mean()
        )

        if (
            pd.isna(average_volume)
            or average_volume <= 0
        ):
            return None

        return (
            current_volume
            / average_volume
        )

    except Exception:
        return None


# ============================================================
# ATR / ATR %
# ============================================================

def calculate_atr(
    df,
    period=14,
):

    """
    Wilder ATR.

    ATR % =
        ATR(14) / latest close * 100
    """

    try:

        if (
            df is None
            or len(df)
            < period + 1
        ):

            return {
                "atr": None,
                "atr_pct": None,
            }

        previous_close = (
            df["Close"]
            .shift(1)
        )

        high_low = (
            df["High"]
            - df["Low"]
        )

        high_previous_close = (
            df["High"]
            - previous_close
        ).abs()

        low_previous_close = (
            df["Low"]
            - previous_close
        ).abs()

        true_range = pd.concat(
            [
                high_low,
                high_previous_close,
                low_previous_close,
            ],
            axis=1,
        ).max(axis=1)

        atr_series = (
            true_range
            .ewm(
                alpha=1 / period,
                adjust=False,
                min_periods=period,
            )
            .mean()
        )

        atr = float(
            atr_series.iloc[-1]
        )

        price = float(
            df["Close"]
            .iloc[-1]
        )

        if (
            pd.isna(atr)
            or price <= 0
        ):

            return {
                "atr": None,
                "atr_pct": None,
            }

        atr_pct = (
            atr
            / price
        ) * 100

        return {
            "atr":
                round(
                    atr,
                    2,
                ),

            "atr_pct":
                round(
                    atr_pct,
                    2,
                ),
        }

    except Exception:

        return {
            "atr": None,
            "atr_pct": None,
        }


# ============================================================
# MOVING AVERAGES
# ============================================================

def calculate_ma_context(df):

    result = {
        "MA20": None,
        "MA50": None,
        "MA200": None,
        "Above MA20": False,
        "Above MA50": False,
        "Above MA200": False,
        "Trend": "N/A",
    }

    if (
        df is None
        or df.empty
    ):
        return result

    close = df["Close"]

    price = float(
        close.iloc[-1]
    )

    if len(close) >= 20:

        ma20 = float(
            close
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        result["MA20"] = ma20

        result["Above MA20"] = (
            price > ma20
        )

    if len(close) >= 50:

        ma50 = float(
            close
            .rolling(50)
            .mean()
            .iloc[-1]
        )

        result["MA50"] = ma50

        result["Above MA50"] = (
            price > ma50
        )

    if len(close) >= 200:

        ma200 = float(
            close
            .rolling(200)
            .mean()
            .iloc[-1]
        )

        result["MA200"] = ma200

        result["Above MA200"] = (
            price > ma200
        )

    if (
        result["MA20"]
        is not None
        and result["MA50"]
        is not None
        and result["MA200"]
        is not None
    ):

        if (
            price > result["MA20"]
            > result["MA50"]
            > result["MA200"]
        ):

            result["Trend"] = (
                "Strong Uptrend"
            )

        elif (
            price < result["MA20"]
            < result["MA50"]
            < result["MA200"]
        ):

            result["Trend"] = (
                "Strong Downtrend"
            )

        elif (
            price > result["MA50"]
            and price > result["MA200"]
        ):

            result["Trend"] = (
                "Bullish"
            )

        elif (
            price < result["MA50"]
            and price < result["MA200"]
        ):

            result["Trend"] = (
                "Bearish"
            )

        else:

            result["Trend"] = (
                "Mixed"
            )

    return result


# ============================================================
# RETURNS / RELATIVE STRENGTH
# ============================================================

def calculate_return(
    df,
    sessions,
):

    try:

        if (
            df is None
            or len(df) <= sessions
        ):
            return None

        current = float(
            df["Close"]
            .iloc[-1]
        )

        previous = float(
            df["Close"]
            .iloc[-sessions - 1]
        )

        if previous == 0:
            return None

        return (
            (
                current
                / previous
            )
            - 1
        ) * 100

    except Exception:
        return None


def calculate_relative_strength(
    asset_df,
    spy_df,
    sessions=20,
):

    asset_return = (
        calculate_return(
            asset_df,
            sessions,
        )
    )

    spy_return = (
        calculate_return(
            spy_df,
            sessions,
        )
    )

    if (
        asset_return is None
        or spy_return is None
    ):
        return None

    return (
        asset_return
        - spy_return
    )


# ============================================================
# WEEKLY ACTIONABLE HISTORY
# ============================================================

def find_weekly_actionable_signals(
    df,
    previous_high,
    previous_low,
):

    result = {
        "low_taken_date": None,
        "low_reclaim_date": None,
        "high_taken_date": None,
        "high_rejection_date": None,

        "pre_signal": None,
        "pre_date": None,
        "pre_event": None,

        "post_signal": None,
        "post_date": None,
        "post_event": None,
    }

    current_period = (
        df.index[-1]
        .to_period("W-FRI")
    )

    current_data = df[
        df.index
        .to_period("W-FRI")
        == current_period
    ].copy()

    if current_data.empty:
        return result

    low_taken = False
    high_taken = False

    low_reclaimed = False
    high_rejected = False

    low_taken_date = None
    high_taken_date = None

    low_reclaim_date = None
    high_rejection_date = None

    for date, row in (
        current_data.iterrows()
    ):

        current_open = float(
            row["Open"]
        )

        current_high = float(
            row["High"]
        )

        current_low = float(
            row["Low"]
        )

        current_close = float(
            row["Close"]
        )

        # ----------------------------------------------
        # UPDATE EVENT STATE FIRST
        # ----------------------------------------------

        if (
            not low_taken
            and current_low
            < previous_low
        ):

            low_taken = True
            low_taken_date = date

        if (
            not high_taken
            and current_high
            > previous_high
        ):

            high_taken = True
            high_taken_date = date

        if (
            low_taken
            and not low_reclaimed
            and current_close
            > previous_low
        ):

            low_reclaimed = True
            low_reclaim_date = date

        if (
            high_taken
            and not high_rejected
            and current_close
            < previous_high
        ):

            high_rejected = True
            high_rejection_date = date

        # ----------------------------------------------
        # PREVIOUS DAILY CANDLE
        # ----------------------------------------------

        location = (
            df.index
            .get_loc(date)
        )

        if location == 0:
            continue

        previous_row = (
            df.iloc[
                location - 1
            ]
        )

        actionable = (
            classify_actionable_candle(
                current_open,
                current_high,
                current_low,
                current_close,
                float(
                    previous_row[
                        "High"
                    ]
                ),
                float(
                    previous_row[
                        "Low"
                    ]
                ),
            )
        )

        if actionable is None:
            continue

        # ----------------------------------------------
        # POST-CONFIRMATION
        # ----------------------------------------------

        if result[
            "post_signal"
        ] is None:

            candidates = []

            if (
                low_reclaimed
                and low_reclaim_date
                is not None
                and date
                >= low_reclaim_date
            ):

                candidates.append(
                    (
                        low_reclaim_date,
                        "PWL Taken → Reclaimed",
                    )
                )

            if (
                high_rejected
                and high_rejection_date
                is not None
                and date
                >= high_rejection_date
            ):

                candidates.append(
                    (
                        high_rejection_date,
                        "PWH Taken → Rejected",
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda item:
                    item[0]
                )

                result[
                    "post_signal"
                ] = actionable

                result[
                    "post_date"
                ] = (
                    date.strftime(
                        "%Y-%m-%d"
                    )
                )

                result[
                    "post_event"
                ] = (
                    candidates[0][1]
                )

        # ----------------------------------------------
        # PRE-CONFIRMATION
        # ----------------------------------------------

        if result[
            "pre_signal"
        ] is None:

            candidates = []

            if (
                low_taken
                and not low_reclaimed
                and low_taken_date
                is not None
            ):

                candidates.append(
                    (
                        low_taken_date,
                        "PWL Taken → "
                        "Not Yet Reclaimed",
                    )
                )

            if (
                high_taken
                and not high_rejected
                and high_taken_date
                is not None
            ):

                candidates.append(
                    (
                        high_taken_date,
                        "PWH Taken → "
                        "Not Yet Rejected",
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda item:
                    item[0]
                )

                result[
                    "pre_signal"
                ] = actionable

                result[
                    "pre_date"
                ] = (
                    date.strftime(
                        "%Y-%m-%d"
                    )
                )

                result[
                    "pre_event"
                ] = (
                    candidates[0][1]
                )

    result["low_taken_date"] = (
        low_taken_date.strftime(
            "%Y-%m-%d"
        )
        if low_taken_date
        is not None
        else None
    )

    result["low_reclaim_date"] = (
        low_reclaim_date.strftime(
            "%Y-%m-%d"
        )
        if low_reclaim_date
        is not None
        else None
    )

    result["high_taken_date"] = (
        high_taken_date.strftime(
            "%Y-%m-%d"
        )
        if high_taken_date
        is not None
        else None
    )

    result["high_rejection_date"] = (
        high_rejection_date.strftime(
            "%Y-%m-%d"
        )
        if high_rejection_date
        is not None
        else None
    )

    return result


# ============================================================
# MONTHLY ACTIONABLE HISTORY
# ============================================================

def find_monthly_actionable_signals(
    df,
    previous_high,
    previous_low,
):

    result = {
        "low_taken_date": None,
        "low_reclaim_date": None,
        "high_taken_date": None,
        "high_rejection_date": None,

        "pre_signal": None,
        "pre_date": None,
        "pre_event": None,

        "post_signal": None,
        "post_date": None,
        "post_event": None,
    }

    current_month = (
        df.index[-1]
        .to_period("M")
    )

    month_daily = df[
        df.index
        .to_period("M")
        == current_month
    ].copy()

    if month_daily.empty:
        return result

    low_taken = False
    high_taken = False

    low_reclaimed = False
    high_rejected = False

    low_taken_date = None
    high_taken_date = None

    low_reclaim_date = None
    high_rejection_date = None

    # ----------------------------------------------
    # FIND DAILY MONTHLY EVENT DATES
    # ----------------------------------------------

    for date, row in (
        month_daily.iterrows()
    ):

        current_high = float(
            row["High"]
        )

        current_low = float(
            row["Low"]
        )

        current_close = float(
            row["Close"]
        )

        if (
            not low_taken
            and current_low
            < previous_low
        ):

            low_taken = True
            low_taken_date = date

        if (
            not high_taken
            and current_high
            > previous_high
        ):

            high_taken = True
            high_taken_date = date

        if (
            low_taken
            and not low_reclaimed
            and current_close
            > previous_low
        ):

            low_reclaimed = True
            low_reclaim_date = date

        if (
            high_taken
            and not high_rejected
            and current_close
            < previous_high
        ):

            high_rejected = True
            high_rejection_date = date

    # ----------------------------------------------
    # BUILD WEEKLY CANDLES
    # ----------------------------------------------

    weekly = build_weekly_dataframe(
        df
    )

    weekly_periods = list(
        weekly.index
    )

    # Use actual observed trading dates.
    monthly_weekly = weekly[
        (
            weekly["FirstDate"]
            .dt.to_period("M")
            == current_month
        )
        |
        (
            weekly["LastDate"]
            .dt.to_period("M")
            == current_month
        )
    ].copy()

    for period, row in (
        monthly_weekly.iterrows()
    ):

        try:

            location = (
                weekly_periods
                .index(period)
            )

        except ValueError:
            continue

        if location == 0:
            continue

        previous_row = (
            weekly.iloc[
                location - 1
            ]
        )

        actionable = (
            classify_actionable_candle(
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(
                    previous_row[
                        "High"
                    ]
                ),
                float(
                    previous_row[
                        "Low"
                    ]
                ),
            )
        )

        if actionable is None:
            continue

        week_start = pd.Timestamp(
            row["FirstDate"]
        )

        week_end = pd.Timestamp(
            row["LastDate"]
        )

        # ----------------------------------------------
        # POST-CONFIRMATION
        # ----------------------------------------------

        if result[
            "post_signal"
        ] is None:

            candidates = []

            if (
                low_reclaim_date
                is not None
                and week_end
                >= low_reclaim_date
            ):

                candidates.append(
                    (
                        low_reclaim_date,
                        "PML Taken → Reclaimed",
                    )
                )

            if (
                high_rejection_date
                is not None
                and week_end
                >= high_rejection_date
            ):

                candidates.append(
                    (
                        high_rejection_date,
                        "PMH Taken → Rejected",
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda item:
                    item[0]
                )

                result[
                    "post_signal"
                ] = actionable

                result[
                    "post_date"
                ] = (
                    week_end.strftime(
                        "%Y-%m-%d"
                    )
                )

                result[
                    "post_event"
                ] = (
                    candidates[0][1]
                )

        # ----------------------------------------------
        # PRE-CONFIRMATION
        # ----------------------------------------------

        if result[
            "pre_signal"
        ] is None:

            candidates = []

            if (
                low_taken_date
                is not None
                and week_end
                >= low_taken_date
                and (
                    low_reclaim_date
                    is None
                    or week_start
                    < low_reclaim_date
                )
            ):

                candidates.append(
                    (
                        low_taken_date,
                        "PML Taken → "
                        "Not Yet Reclaimed",
                    )
                )

            if (
                high_taken_date
                is not None
                and week_end
                >= high_taken_date
                and (
                    high_rejection_date
                    is None
                    or week_start
                    < high_rejection_date
                )
            ):

                candidates.append(
                    (
                        high_taken_date,
                        "PMH Taken → "
                        "Not Yet Rejected",
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda item:
                    item[0]
                )

                result[
                    "pre_signal"
                ] = actionable

                result[
                    "pre_date"
                ] = (
                    week_end.strftime(
                        "%Y-%m-%d"
                    )
                )

                result[
                    "pre_event"
                ] = (
                    candidates[0][1]
                )

    result["low_taken_date"] = (
        low_taken_date.strftime(
            "%Y-%m-%d"
        )
        if low_taken_date
        is not None
        else None
    )

    result["low_reclaim_date"] = (
        low_reclaim_date.strftime(
            "%Y-%m-%d"
        )
        if low_reclaim_date
        is not None
        else None
    )

    result["high_taken_date"] = (
        high_taken_date.strftime(
            "%Y-%m-%d"
        )
        if high_taken_date
        is not None
        else None
    )

    result["high_rejection_date"] = (
        high_rejection_date.strftime(
            "%Y-%m-%d"
        )
        if high_rejection_date
        is not None
        else None
    )

    return result


# ============================================================
# WEEKLY SCANNER
# ============================================================

def scan_weekly(
    tickers,
    market_data,
):

    rows = []

    tickers = sorted(
        set(tickers)
    )

    total = len(tickers)

    progress = st.progress(0)
    status = st.empty()

    for index, ticker in enumerate(
        tickers
    ):

        status.text(
            f"Weekly scan: "
            f"{ticker} "
            f"({index + 1}/{total})"
        )

        try:

            df = clean_ticker_dataframe(
                market_data,
                ticker,
            )

            if (
                df is None
                or len(df) < 30
            ):
                continue

            levels = get_weekly_levels(
                df
            )

            if levels is None:
                continue

            previous_high = (
                levels[
                    "previous_high"
                ]
            )

            previous_low = (
                levels[
                    "previous_low"
                ]
            )

            price = float(
                df["Close"]
                .iloc[-1]
            )

            low_taken = (
                levels["current_low"]
                < previous_low
            )

            high_taken = (
                levels["current_high"]
                > previous_high
            )

            # Scanner only shows sweeps.

            if not (
                low_taken
                or high_taken
            ):
                continue

            low_reclaimed = (
                low_taken
                and price
                > previous_low
            )

            high_rejected = (
                high_taken
                and price
                < previous_high
            )

            daily_strat = (
                get_daily_strat(
                    df
                )
            )

            ftfc = calculate_ftfc(
                df
            )

            rvol = calculate_rvol(
                df
            )

            atr_data = calculate_atr(
                df,
                period=14,
            )

            actionable = (
                find_weekly_actionable_signals(
                    df,
                    previous_high,
                    previous_low,
                )
            )

            bullish = (
                low_reclaimed
                and daily_strat
                in BULLISH_PATTERNS
                and ftfc["weekly"]
                == "Up"
            )

            bearish = (
                high_rejected
                and daily_strat
                in BEARISH_PATTERNS
                and ftfc["weekly"]
                == "Down"
            )

            if bullish:

                signal = (
                    "Previous Week Low Taken "
                    "→ Reclaimed → "
                    f"Daily {daily_strat} → "
                    "Weekly FTFC Up"
                )

            elif bearish:

                signal = (
                    "Previous Week High Taken "
                    "→ Rejected → "
                    f"Daily {daily_strat} → "
                    "Weekly FTFC Down"
                )

            elif (
                low_taken
                and high_taken
            ):

                signal = (
                    "Both Previous Week "
                    "Levels Taken"
                )

            elif low_reclaimed:

                signal = (
                    "Previous Week Low Taken "
                    "→ Reclaimed"
                )

            elif high_rejected:

                signal = (
                    "Previous Week High Taken "
                    "→ Rejected"
                )

            elif low_taken:

                signal = (
                    "Previous Week Low Taken"
                )

            else:

                signal = (
                    "Previous Week High Taken"
                )

            pct_from_pwl = (
                (
                    price
                    - previous_low
                )
                / previous_low
            ) * 100

            pct_from_pwh = (
                (
                    price
                    - previous_high
                )
                / previous_high
            ) * 100

            rows.append(
                {
                    "Ticker":
                        ticker,

                    "Asset":
                        get_asset_type(
                            ticker
                        ),

                    "Price":
                        round(
                            price,
                            2,
                        ),

                    "Prev Week Low":
                        round(
                            previous_low,
                            2,
                        ),

                    "Prev Week High":
                        round(
                            previous_high,
                            2,
                        ),

                    "Prev Week STRAT":
                        levels[
                            "previous_strat"
                        ],

                    "Current Week Low":
                        round(
                            levels[
                                "current_low"
                            ],
                            2,
                        ),

                    "Current Week High":
                        round(
                            levels[
                                "current_high"
                            ],
                            2,
                        ),

                    "Current Week STRAT":
                        levels[
                            "current_strat"
                        ],

                    "Low Taken":
                        low_taken,

                    "Low Sweep Date":
                        actionable[
                            "low_taken_date"
                        ],

                    "Low Reclaimed":
                        low_reclaimed,

                    "Low Reclaim Date":
                        actionable[
                            "low_reclaim_date"
                        ],

                    "High Taken":
                        high_taken,

                    "High Sweep Date":
                        actionable[
                            "high_taken_date"
                        ],

                    "High Rejected":
                        high_rejected,

                    "High Rejection Date":
                        actionable[
                            "high_rejection_date"
                        ],

                    "First Pre-Confirmation Signal":
                        actionable[
                            "pre_signal"
                        ],

                    "Pre-Confirmation Date":
                        actionable[
                            "pre_date"
                        ],

                    "Pre-Confirmation Event":
                        actionable[
                            "pre_event"
                        ],

                    "First Post-Confirmation Signal":
                        actionable[
                            "post_signal"
                        ],

                    "Post-Confirmation Date":
                        actionable[
                            "post_date"
                        ],

                    "Post-Confirmation Event":
                        actionable[
                            "post_event"
                        ],

                    "Daily STRAT":
                        daily_strat,

                    "Weekly FTFC":
                        ftfc[
                            "weekly"
                        ],

                    "Monthly FTFC":
                        ftfc[
                            "monthly"
                        ],

                    "FTFC":
                        ftfc[
                            "alignment"
                        ],

                    "RVOL":
                        (
                            round(
                                rvol,
                                2,
                            )
                            if rvol
                            is not None
                            else None
                        ),

                    "ATR":
                        atr_data[
                            "atr"
                        ],

                    "ATR %":
                        atr_data[
                            "atr_pct"
                        ],

                    "% From PWL":
                        round(
                            pct_from_pwl,
                            2,
                        ),

                    "% From PWH":
                        round(
                            pct_from_pwh,
                            2,
                        ),

                    "Bullish Setup":
                        bullish,

                    "Bearish Setup":
                        bearish,

                    "Signal":
                        signal,
                }
            )

        except Exception:
            pass

        finally:

            if total:

                progress.progress(
                    (index + 1)
                    / total
                )

    progress.empty()
    status.empty()

    return pd.DataFrame(
        rows
    )


# ============================================================
# MONTHLY SCANNER
# ============================================================

def scan_monthly(
    tickers,
    market_data,
):

    rows = []

    tickers = sorted(
        set(tickers)
    )

    total = len(tickers)

    progress = st.progress(0)
    status = st.empty()

    for index, ticker in enumerate(
        tickers
    ):

        status.text(
            f"Monthly scan: "
            f"{ticker} "
            f"({index + 1}/{total})"
        )

        try:

            df = clean_ticker_dataframe(
                market_data,
                ticker,
            )

            if (
                df is None
                or len(df) < 60
            ):
                continue

            levels = get_monthly_levels(
                df
            )

            if levels is None:
                continue

            previous_high = (
                levels[
                    "previous_high"
                ]
            )

            previous_low = (
                levels[
                    "previous_low"
                ]
            )

            price = float(
                df["Close"]
                .iloc[-1]
            )

            low_taken = (
                levels["current_low"]
                < previous_low
            )

            high_taken = (
                levels["current_high"]
                > previous_high
            )

            if not (
                low_taken
                or high_taken
            ):
                continue

            low_reclaimed = (
                low_taken
                and price
                > previous_low
            )

            high_rejected = (
                high_taken
                and price
                < previous_high
            )

            weekly_strat = (
                get_current_week_strat(
                    df
                )
            )

            ftfc = calculate_ftfc(
                df
            )

            rvol = calculate_rvol(
                df
            )

            atr_data = calculate_atr(
                df,
                period=14,
            )

            actionable = (
                find_monthly_actionable_signals(
                    df,
                    previous_high,
                    previous_low,
                )
            )

            bullish = (
                low_reclaimed
                and weekly_strat
                in BULLISH_PATTERNS
                and ftfc["monthly"]
                == "Up"
            )

            bearish = (
                high_rejected
                and weekly_strat
                in BEARISH_PATTERNS
                and ftfc["monthly"]
                == "Down"
            )

            if bullish:

                signal = (
                    "Previous Month Low Taken "
                    "→ Reclaimed → "
                    f"Weekly {weekly_strat} → "
                    "Monthly FTFC Up"
                )

            elif bearish:

                signal = (
                    "Previous Month High Taken "
                    "→ Rejected → "
                    f"Weekly {weekly_strat} → "
                    "Monthly FTFC Down"
                )

            elif (
                low_taken
                and high_taken
            ):

                signal = (
                    "Both Previous Month "
                    "Levels Taken"
                )

            elif low_reclaimed:

                signal = (
                    "Previous Month Low Taken "
                    "→ Reclaimed"
                )

            elif high_rejected:

                signal = (
                    "Previous Month High Taken "
                    "→ Rejected"
                )

            elif low_taken:

                signal = (
                    "Previous Month Low Taken"
                )

            else:

                signal = (
                    "Previous Month High Taken"
                )

            pct_from_pml = (
                (
                    price
                    - previous_low
                )
                / previous_low
            ) * 100

            pct_from_pmh = (
                (
                    price
                    - previous_high
                )
                / previous_high
            ) * 100

            rows.append(
                {
                    "Ticker":
                        ticker,

                    "Asset":
                        get_asset_type(
                            ticker
                        ),

                    "Price":
                        round(
                            price,
                            2,
                        ),

                    "Prev Month Low":
                        round(
                            previous_low,
                            2,
                        ),

                    "Prev Month High":
                        round(
                            previous_high,
                            2,
                        ),

                    "Prev Month STRAT":
                        levels[
                            "previous_strat"
                        ],

                    "Current Month Low":
                        round(
                            levels[
                                "current_low"
                            ],
                            2,
                        ),

                    "Current Month High":
                        round(
                            levels[
                                "current_high"
                            ],
                            2,
                        ),

                    "Current Month STRAT":
                        levels[
                            "current_strat"
                        ],

                    "Low Taken":
                        low_taken,

                    "PML Sweep Date":
                        actionable[
                            "low_taken_date"
                        ],

                    "Low Reclaimed":
                        low_reclaimed,

                    "PML Reclaim Date":
                        actionable[
                            "low_reclaim_date"
                        ],

                    "High Taken":
                        high_taken,

                    "PMH Sweep Date":
                        actionable[
                            "high_taken_date"
                        ],

                    "High Rejected":
                        high_rejected,

                    "PMH Rejection Date":
                        actionable[
                            "high_rejection_date"
                        ],

                    "First Pre-Confirmation Weekly Signal":
                        actionable[
                            "pre_signal"
                        ],

                    "Pre-Confirmation Week":
                        actionable[
                            "pre_date"
                        ],

                    "Pre-Confirmation Event":
                        actionable[
                            "pre_event"
                        ],

                    "First Post-Confirmation Weekly Signal":
                        actionable[
                            "post_signal"
                        ],

                    "Post-Confirmation Week":
                        actionable[
                            "post_date"
                        ],

                    "Post-Confirmation Event":
                        actionable[
                            "post_event"
                        ],

                    "Current Week STRAT":
                        weekly_strat,

                    "Weekly FTFC":
                        ftfc[
                            "weekly"
                        ],

                    "Monthly FTFC":
                        ftfc[
                            "monthly"
                        ],

                    "FTFC":
                        ftfc[
                            "alignment"
                        ],

                    "RVOL":
                        (
                            round(
                                rvol,
                                2,
                            )
                            if rvol
                            is not None
                            else None
                        ),

                    "ATR":
                        atr_data[
                            "atr"
                        ],

                    "ATR %":
                        atr_data[
                            "atr_pct"
                        ],

                    "% From PML":
                        round(
                            pct_from_pml,
                            2,
                        ),

                    "% From PMH":
                        round(
                            pct_from_pmh,
                            2,
                        ),

                    "Bullish Setup":
                        bullish,

                    "Bearish Setup":
                        bearish,

                    "Signal":
                        signal,
                }
            )

        except Exception:
            pass

        finally:

            if total:

                progress.progress(
                    (index + 1)
                    / total
                )

    progress.empty()
    status.empty()

    return pd.DataFrame(
        rows
    )


# ============================================================
# MARKET CONTEXT
# ============================================================

def build_market_context(
    market_data,
):

    rows = []

    spy_df = clean_ticker_dataframe(
        market_data,
        "SPY",
    )

    for ticker in (
        MARKET_CONTEXT_TICKERS
    ):

        try:

            df = clean_ticker_dataframe(
                market_data,
                ticker,
            )

            if (
                df is None
                or len(df) < 30
            ):
                continue

            price = float(
                df["Close"]
                .iloc[-1]
            )

            daily_strat = (
                get_daily_strat(
                    df
                )
            )

            weekly = get_weekly_levels(
                df
            )

            monthly = get_monthly_levels(
                df
            )

            ftfc = calculate_ftfc(
                df
            )

            ma = calculate_ma_context(
                df
            )

            rvol = calculate_rvol(
                df
            )

            atr_data = calculate_atr(
                df,
                period=14,
            )

            return_5d = (
                calculate_return(
                    df,
                    5,
                )
            )

            return_20d = (
                calculate_return(
                    df,
                    20,
                )
            )

            rs20 = None

            if (
                ticker not in {
                    "SPY",
                    "^VIX",
                }
                and spy_df
                is not None
            ):

                rs20 = (
                    calculate_relative_strength(
                        df,
                        spy_df,
                        20,
                    )
                )

            # ----------------------------------------------
            # WEEKLY
            # ----------------------------------------------

            if weekly:

                pwl = weekly[
                    "previous_low"
                ]

                pwh = weekly[
                    "previous_high"
                ]

                previous_week_strat = (
                    weekly[
                        "previous_strat"
                    ]
                )

                current_week_strat = (
                    weekly[
                        "current_strat"
                    ]
                )

                pct_pwl = (
                    (
                        price
                        - pwl
                    )
                    / pwl
                ) * 100

                pct_pwh = (
                    (
                        price
                        - pwh
                    )
                    / pwh
                ) * 100

            else:

                pwl = None
                pwh = None

                previous_week_strat = (
                    "N/A"
                )

                current_week_strat = (
                    "N/A"
                )

                pct_pwl = None
                pct_pwh = None

            # ----------------------------------------------
            # MONTHLY
            # ----------------------------------------------

            if monthly:

                pml = monthly[
                    "previous_low"
                ]

                pmh = monthly[
                    "previous_high"
                ]

                previous_month_strat = (
                    monthly[
                        "previous_strat"
                    ]
                )

                current_month_strat = (
                    monthly[
                        "current_strat"
                    ]
                )

                pct_pml = (
                    (
                        price
                        - pml
                    )
                    / pml
                ) * 100

                pct_pmh = (
                    (
                        price
                        - pmh
                    )
                    / pmh
                ) * 100

            else:

                pml = None
                pmh = None

                previous_month_strat = (
                    "N/A"
                )

                current_month_strat = (
                    "N/A"
                )

                pct_pml = None
                pct_pmh = None

            # ----------------------------------------------
            # CONTEXT SCORE
            # ----------------------------------------------

            points = 0

            if ftfc["weekly"] == "Up":
                points += 1

            elif ftfc["weekly"] == "Down":
                points -= 1

            if ftfc["monthly"] == "Up":
                points += 1

            elif ftfc["monthly"] == "Down":
                points -= 1

            if ma["MA20"] is not None:

                points += (
                    1
                    if ma["Above MA20"]
                    else -1
                )

            if ma["MA50"] is not None:

                points += (
                    1
                    if ma["Above MA50"]
                    else -1
                )

            if ma["MA200"] is not None:

                points += (
                    1
                    if ma["Above MA200"]
                    else -1
                )

            if points >= 4:

                context = (
                    "Strong Bullish"
                )

            elif points >= 2:

                context = "Bullish"

            elif points <= -4:

                context = (
                    "Strong Bearish"
                )

            elif points <= -2:

                context = "Bearish"

            else:

                context = "Mixed"

            if ticker == "^VIX":
                context = "Volatility"

            rows.append(
                {
                    "Ticker":
                        ticker,

                    "Market":
                        MARKET_CONTEXT_NAMES[
                            ticker
                        ],

                    "Price":
                        round(
                            price,
                            2,
                        ),

                    "Context":
                        context,

                    "Daily STRAT":
                        daily_strat,

                    "Prev Week STRAT":
                        previous_week_strat,

                    "Current Week STRAT":
                        current_week_strat,

                    "Prev Month STRAT":
                        previous_month_strat,

                    "Current Month STRAT":
                        current_month_strat,

                    "Weekly FTFC":
                        ftfc[
                            "weekly"
                        ],

                    "Monthly FTFC":
                        ftfc[
                            "monthly"
                        ],

                    "M/W Alignment":
                        ftfc[
                            "alignment"
                        ],

                    "Trend":
                        ma[
                            "Trend"
                        ],

                    "Above MA20":
                        ma[
                            "Above MA20"
                        ],

                    "Above MA50":
                        ma[
                            "Above MA50"
                        ],

                    "Above MA200":
                        ma[
                            "Above MA200"
                        ],

                    "5D Return %":
                        (
                            round(
                                return_5d,
                                2,
                            )
                            if return_5d
                            is not None
                            else None
                        ),

                    "20D Return %":
                        (
                            round(
                                return_20d,
                                2,
                            )
                            if return_20d
                            is not None
                            else None
                        ),

                    "20D RS vs SPY":
                        (
                            round(
                                rs20,
                                2,
                            )
                            if rs20
                            is not None
                            else None
                        ),

                    "RVOL":
                        (
                            round(
                                rvol,
                                2,
                            )
                            if rvol
                            is not None
                            else None
                        ),

                    "ATR":
                        atr_data[
                            "atr"
                        ],

                    "ATR %":
                        atr_data[
                            "atr_pct"
                        ],

                    "Prev Week Low":
                        (
                            round(
                                pwl,
                                2,
                            )
                            if pwl
                            is not None
                            else None
                        ),

                    "Prev Week High":
                        (
                            round(
                                pwh,
                                2,
                            )
                            if pwh
                            is not None
                            else None
                        ),

                    "% From PWL":
                        (
                            round(
                                pct_pwl,
                                2,
                            )
                            if pct_pwl
                            is not None
                            else None
                        ),

                    "% From PWH":
                        (
                            round(
                                pct_pwh,
                                2,
                            )
                            if pct_pwh
                            is not None
                            else None
                        ),

                    "Prev Month Low":
                        (
                            round(
                                pml,
                                2,
                            )
                            if pml
                            is not None
                            else None
                        ),

                    "Prev Month High":
                        (
                            round(
                                pmh,
                                2,
                            )
                            if pmh
                            is not None
                            else None
                        ),

                    "% From PML":
                        (
                            round(
                                pct_pml,
                                2,
                            )
                            if pct_pml
                            is not None
                            else None
                        ),

                    "% From PMH":
                        (
                            round(
                                pct_pmh,
                                2,
                            )
                            if pct_pmh
                            is not None
                            else None
                        ),
                }
            )

        except Exception:
            continue

    return pd.DataFrame(
        rows
    )


# ============================================================
# HELPER FOR SAFE DISPLAY COLUMNS
# ============================================================

def available_columns(
    dataframe,
    requested,
):

    return [
        column
        for column in requested
        if column
        in dataframe.columns
    ]


# ============================================================
# LOAD UNIVERSES
# ============================================================

with st.spinner(
    "Loading market universes..."
):

    sp500_tickers = (
        get_sp500_tickers()
    )

    nasdaq100_tickers = (
        get_nasdaq100_tickers()
    )

    etf_tickers = (
        get_etf_tickers()
    )


combined_tickers = sorted(
    set(
        sp500_tickers
        + nasdaq100_tickers
        + etf_tickers
    )
)


duplicate_count = (
    len(sp500_tickers)
    + len(nasdaq100_tickers)
    + len(etf_tickers)
    - len(combined_tickers)
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Market Settings"
)


universe = (
    st.sidebar.selectbox(
        "Market Universe",
        [
            "S&P 500 + Nasdaq-100 + ETFs",
            "S&P 500",
            "Nasdaq-100",
            "Market + Sector ETFs",
            "Custom Watchlist",
        ],
        key=(
            "sidebar_market_universe"
        ),
    )
)


if (
    universe
    == "S&P 500 + Nasdaq-100 + ETFs"
):

    selected_tickers = (
        combined_tickers
    )

elif universe == "S&P 500":

    selected_tickers = (
        sp500_tickers
    )

elif universe == "Nasdaq-100":

    selected_tickers = (
        nasdaq100_tickers
    )

elif (
    universe
    == "Market + Sector ETFs"
):

    selected_tickers = (
        etf_tickers
    )

else:

    custom = (
        st.sidebar.text_area(
            "Custom Tickers",
            value=(
                "AAPL,MSFT,NVDA,AMD,"
                "TSLA,AMZN,META,SPY,"
                "QQQ,IWM"
            ),
            key=(
                "sidebar_custom_tickers"
            ),
        )
    )

    selected_tickers = sorted(
        set(
            ticker
            .strip()
            .upper()
            .replace(".", "-")

            for ticker
            in custom.split(",")

            if ticker.strip()
        )
    )


# ============================================================
# SIDEBAR STATS
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "Universe Statistics"
)


side1, side2 = (
    st.sidebar.columns(2)
)


side1.metric(
    "S&P 500",
    len(
        sp500_tickers
    ),
)


side2.metric(
    "Nasdaq-100",
    len(
        nasdaq100_tickers
    ),
)


side3, side4 = (
    st.sidebar.columns(2)
)


side3.metric(
    "ETFs",
    len(
        etf_tickers
    ),
)


side4.metric(
    "Duplicates",
    duplicate_count,
)


st.sidebar.metric(
    "Scanner Universe",
    len(
        selected_tickers
    ),
)


with st.sidebar.expander(
    "📈 ETFs Included"
):

    st.markdown(
        """
**Broad Market**

- SPY — S&P 500
- QQQ — Nasdaq-100
- IWM — Russell 2000

**Sectors**

- XLC — Communication Services
- XLY — Consumer Discretionary
- XLP — Consumer Staples
- XLE — Energy
- XLF — Financials
- XLV — Health Care
- XLI — Industrials
- XLB — Materials
- XLRE — Real Estate
- XLK — Technology
- XLU — Utilities

**Market Context Only**

- ^VIX — VIX
"""
    )


# ============================================================
# SESSION STATE
# ============================================================

if (
    "market_data"
    not in st.session_state
):

    st.session_state[
        "market_data"
    ] = None


if (
    "loaded_universe"
    not in st.session_state
):

    st.session_state[
        "loaded_universe"
    ] = None


if (
    "weekly_results_raw"
    not in st.session_state
):

    st.session_state[
        "weekly_results_raw"
    ] = None


if (
    "monthly_results_raw"
    not in st.session_state
):

    st.session_state[
        "monthly_results_raw"
    ] = None


# ============================================================
# LOAD MARKET DATA
# ============================================================

load_market = (
    st.sidebar.button(
        "📥 Load Market Data",
        type="primary",
        use_container_width=True,
        key=(
            "sidebar_load_market_data"
        ),
    )
)


if load_market:

    download_tickers = sorted(
        set(
            selected_tickers
            + MARKET_CONTEXT_TICKERS
        )
    )

    with st.spinner(
        f"Downloading 1 year of data "
        f"for {len(download_tickers)} "
        f"symbols..."
    ):

        market_data = (
            download_market_data(
                download_tickers
            )
        )

    st.session_state[
        "market_data"
    ] = market_data

    st.session_state[
        "loaded_universe"
    ] = tuple(
        selected_tickers
    )

    st.session_state[
        "weekly_results_raw"
    ] = None

    st.session_state[
        "monthly_results_raw"
    ] = None

    if market_data:

        st.sidebar.success(
            f"Loaded data for "
            f"{len(market_data)} "
            f"symbols."
        )

    else:

        st.sidebar.error(
            "No market data was "
            "downloaded."
        )


market_ready = (
    st.session_state[
        "market_data"
    ]
    is not None

    and

    st.session_state[
        "loaded_universe"
    ]
    == tuple(
        selected_tickers
    )
)


if not market_ready:

    st.info(
        "Select a universe and click "
        "**📥 Load Market Data**."
    )


# ============================================================
# TABS
# ============================================================

(
    weekly_tab,
    monthly_tab,
    market_context_tab,
) = st.tabs(
    [
        "📅 Weekly Scanner",
        "🗓️ Monthly Scanner",
        "🌎 Market Context",
    ]
)


# ============================================================
# WEEKLY TAB
# ============================================================

with weekly_tab:

    st.header(
        "📅 Weekly Sweep Scanner"
    )

    st.caption(
        "Previous Week High/Low → "
        "Sweep → Reclaim/Reject → "
        "Daily STRAT → Weekly FTFC"
    )

    # --------------------------------------------------------
    # FILTER ROW 1
    # --------------------------------------------------------

    w1, w2, w3, w4 = (
        st.columns(4)
    )


    weekly_signal_filter = (
        w1.selectbox(
            "Weekly Signal",
            [
                "All Sweeps",
                "PWL Taken",
                "PWH Taken",
                "PWL Reclaimed",
                "PWH Rejected",
                "Bullish Setup",
                "Bearish Setup",
            ],
            key=(
                "weekly_signal_filter"
            ),
        )
    )


    weekly_strat_filter = (
        w2.selectbox(
            "Current Week STRAT",
            STRAT_OPTIONS,
            key=(
                "weekly_current_week_"
                "strat_filter"
            ),
        )
    )


    daily_filter = (
        w3.selectbox(
            "Daily STRAT",
            STRAT_OPTIONS,
            key=(
                "weekly_daily_strat_"
                "filter"
            ),
        )
    )


    weekly_actionable_filter = (
        w4.selectbox(
            "Actionable Candle",
            [
                "All",
                "Hammer",
                "Shooting Star",
                "Inside Bar",
            ],
            key=(
                "weekly_actionable_"
                "candle_filter"
            ),
        )
    )


    # --------------------------------------------------------
    # FILTER ROW 2
    # --------------------------------------------------------

    w5, w6, w7 = (
        st.columns(3)
    )


    weekly_category = (
        w5.selectbox(
            "Actionable Category",
            [
                "All",
                "Pre-Confirmation",
                "Post-Confirmation",
            ],
            key=(
                "weekly_actionable_"
                "category_filter"
            ),
        )
    )


    weekly_min_rvol = (
        w6.number_input(
            "Minimum RVOL",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key=(
                "weekly_minimum_rvol"
            ),
        )
    )


    weekly_min_atr = (
        w7.number_input(
            "Minimum ATR %",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key=(
                "weekly_minimum_atr_pct"
            ),
        )
    )


    run_weekly = (
        st.button(
            "🚀 Run Weekly Scanner",
            type="primary",
            use_container_width=True,
            key=(
                "run_weekly_scanner_button"
            ),
        )
    )


    if run_weekly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            st.session_state[
                "weekly_results_raw"
            ] = scan_weekly(
                selected_tickers,
                st.session_state[
                    "market_data"
                ],
            )


    # ========================================================
    # WEEKLY RESULTS
    # ========================================================

    if (
        st.session_state[
            "weekly_results_raw"
        ]
        is not None
    ):

        weekly_results = (
            st.session_state[
                "weekly_results_raw"
            ]
            .copy()
        )

        if weekly_results.empty:

            st.warning(
                "No previous-week "
                "liquidity sweeps found."
            )

        else:

            # ----------------------------------------------
            # SIGNAL FILTER
            # ----------------------------------------------

            if (
                weekly_signal_filter
                == "PWL Taken"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Low Taken"
                        ]
                    ]
                )

            elif (
                weekly_signal_filter
                == "PWH Taken"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "High Taken"
                        ]
                    ]
                )

            elif (
                weekly_signal_filter
                == "PWL Reclaimed"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Low Reclaimed"
                        ]
                    ]
                )

            elif (
                weekly_signal_filter
                == "PWH Rejected"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "High Rejected"
                        ]
                    ]
                )

            elif (
                weekly_signal_filter
                == "Bullish Setup"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Bullish Setup"
                        ]
                    ]
                )

            elif (
                weekly_signal_filter
                == "Bearish Setup"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Bearish Setup"
                        ]
                    ]
                )

            # ----------------------------------------------
            # STRAT FILTERS
            # ----------------------------------------------

            if (
                weekly_strat_filter
                != "All"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Current Week STRAT"
                        ]
                        == weekly_strat_filter
                    ]
                )

            if daily_filter != "All":

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Daily STRAT"
                        ]
                        == daily_filter
                    ]
                )

            # ----------------------------------------------
            # ACTIONABLE FILTER
            # ----------------------------------------------

            if (
                weekly_actionable_filter
                != "All"
            ):

                if (
                    weekly_category
                    == "Pre-Confirmation"
                ):

                    weekly_results = (
                        weekly_results[
                            weekly_results[
                                "First "
                                "Pre-Confirmation "
                                "Signal"
                            ]
                            == weekly_actionable_filter
                        ]
                    )

                elif (
                    weekly_category
                    == "Post-Confirmation"
                ):

                    weekly_results = (
                        weekly_results[
                            weekly_results[
                                "First "
                                "Post-Confirmation "
                                "Signal"
                            ]
                            == weekly_actionable_filter
                        ]
                    )

                else:

                    weekly_results = (
                        weekly_results[
                            (
                                weekly_results[
                                    "First "
                                    "Pre-Confirmation "
                                    "Signal"
                                ]
                                == weekly_actionable_filter
                            )
                            |
                            (
                                weekly_results[
                                    "First "
                                    "Post-Confirmation "
                                    "Signal"
                                ]
                                == weekly_actionable_filter
                            )
                        ]
                    )

            elif (
                weekly_category
                == "Pre-Confirmation"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "First "
                            "Pre-Confirmation "
                            "Signal"
                        ]
                        .notna()
                    ]
                )

            elif (
                weekly_category
                == "Post-Confirmation"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "First "
                            "Post-Confirmation "
                            "Signal"
                        ]
                        .notna()
                    ]
                )

            # ----------------------------------------------
            # RVOL
            # ----------------------------------------------

            if weekly_min_rvol > 0:

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "RVOL"
                        ]
                        .fillna(0)
                        >= weekly_min_rvol
                    ]
                )

            # ----------------------------------------------
            # ATR %
            # ----------------------------------------------

            if weekly_min_atr > 0:

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "ATR %"
                        ]
                        .fillna(0)
                        >= weekly_min_atr
                    ]
                )

            # ----------------------------------------------
            # DISPLAY
            # ----------------------------------------------

            if weekly_results.empty:

                st.warning(
                    "No weekly signals "
                    "matched the filters."
                )

            else:

                weekly_results = (
                    weekly_results
                    .sort_values(
                        [
                            "Bullish Setup",
                            "Bearish Setup",
                            "ATR %",
                            "RVOL",
                        ],
                        ascending=[
                            False,
                            False,
                            False,
                            False,
                        ],
                        na_position="last",
                    )
                )

                wc1, wc2, wc3, wc4, wc5 = (
                    st.columns(5)
                )

                wc1.metric(
                    "Matches",
                    len(
                        weekly_results
                    ),
                )

                wc2.metric(
                    "PWL Taken",
                    int(
                        weekly_results[
                            "Low Taken"
                        ].sum()
                    ),
                )

                wc3.metric(
                    "PWH Taken",
                    int(
                        weekly_results[
                            "High Taken"
                        ].sum()
                    ),
                )

                wc4.metric(
                    "Bullish",
                    int(
                        weekly_results[
                            "Bullish Setup"
                        ].sum()
                    ),
                )

                wc5.metric(
                    "Bearish",
                    int(
                        weekly_results[
                            "Bearish Setup"
                        ].sum()
                    ),
                )

                st.subheader(
                    "🔎 Weekly Scanner Results"
                )

                st.dataframe(
                    weekly_results,
                    use_container_width=True,
                    hide_index=True,
                )

                # ------------------------------------------
                # POST CONFIRMATION
                # ------------------------------------------

                weekly_post = (
                    weekly_results[
                        weekly_results[
                            "First "
                            "Post-Confirmation "
                            "Signal"
                        ]
                        .notna()
                    ]
                )

                if not weekly_post.empty:

                    st.subheader(
                        "✅ Weekly "
                        "Post-Confirmation Signals"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Post-Confirmation Event",
                        "First Post-Confirmation Signal",
                        "Post-Confirmation Date",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "Daily STRAT",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "Signal",
                    ]

                    st.dataframe(
                        weekly_post[
                            available_columns(
                                weekly_post,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # PRE CONFIRMATION
                # ------------------------------------------

                weekly_pre = (
                    weekly_results[
                        weekly_results[
                            "First "
                            "Pre-Confirmation "
                            "Signal"
                        ]
                        .notna()
                    ]
                )

                if not weekly_pre.empty:

                    st.subheader(
                        "⚠️ Weekly "
                        "Pre-Confirmation Signals"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Pre-Confirmation Event",
                        "First Pre-Confirmation Signal",
                        "Pre-Confirmation Date",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "Daily STRAT",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "Signal",
                    ]

                    st.dataframe(
                        weekly_pre[
                            available_columns(
                                weekly_pre,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # BULLISH
                # ------------------------------------------

                weekly_bullish = (
                    weekly_results[
                        weekly_results[
                            "Bullish Setup"
                        ]
                    ]
                )

                if not weekly_bullish.empty:

                    st.subheader(
                        "🟢 Bullish Weekly Setups"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Prev Week Low",
                        "Low Sweep Date",
                        "Low Reclaim Date",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "Daily STRAT",
                        "First Post-Confirmation Signal",
                        "Post-Confirmation Date",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "% From PWL",
                        "Signal",
                    ]

                    st.dataframe(
                        weekly_bullish[
                            available_columns(
                                weekly_bullish,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # BEARISH
                # ------------------------------------------

                weekly_bearish = (
                    weekly_results[
                        weekly_results[
                            "Bearish Setup"
                        ]
                    ]
                )

                if not weekly_bearish.empty:

                    st.subheader(
                        "🔴 Bearish Weekly Setups"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Prev Week High",
                        "High Sweep Date",
                        "High Rejection Date",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "Daily STRAT",
                        "First Post-Confirmation Signal",
                        "Post-Confirmation Date",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "% From PWH",
                        "Signal",
                    ]

                    st.dataframe(
                        weekly_bearish[
                            available_columns(
                                weekly_bearish,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # DOWNLOAD
                # ------------------------------------------

                weekly_csv = (
                    weekly_results
                    .to_csv(
                        index=False
                    )
                    .encode("utf-8")
                )

                st.download_button(
                    "⬇️ Download Weekly Results",
                    data=weekly_csv,
                    file_name=(
                        "weekly_strat_scanner.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                    key=(
                        "download_weekly_results"
                    ),
                )


# ============================================================
# MONTHLY TAB
# ============================================================

with monthly_tab:

    st.header(
        "🗓️ Monthly Sweep Scanner"
    )

    st.caption(
        "Previous Month High/Low → "
        "Sweep → Reclaim/Reject → "
        "Weekly STRAT → Monthly FTFC"
    )

    # --------------------------------------------------------
    # FILTER ROW 1
    # --------------------------------------------------------

    m1, m2, m3, m4 = (
        st.columns(4)
    )


    monthly_signal_filter = (
        m1.selectbox(
            "Monthly Signal",
            [
                "All Sweeps",
                "PML Taken",
                "PMH Taken",
                "PML Reclaimed",
                "PMH Rejected",
                "Bullish Setup",
                "Bearish Setup",
            ],
            key=(
                "monthly_signal_filter"
            ),
        )
    )


    month_strat_filter = (
        m2.selectbox(
            "Current Month STRAT",
            STRAT_OPTIONS,
            key=(
                "monthly_current_month_"
                "strat_filter"
            ),
        )
    )


    month_weekly_filter = (
        m3.selectbox(
            "Current Week STRAT",
            STRAT_OPTIONS,
            key=(
                "monthly_current_week_"
                "strat_filter"
            ),
        )
    )


    monthly_actionable_filter = (
        m4.selectbox(
            "Weekly Actionable Signal",
            [
                "All",
                "Hammer",
                "Shooting Star",
                "Inside Bar",
            ],
            key=(
                "monthly_weekly_"
                "actionable_filter"
            ),
        )
    )


    # --------------------------------------------------------
    # FILTER ROW 2
    # --------------------------------------------------------

    m5, m6, m7 = (
        st.columns(3)
    )


    monthly_category = (
        m5.selectbox(
            "Actionable Category",
            [
                "All",
                "Pre-Confirmation",
                "Post-Confirmation",
            ],
            key=(
                "monthly_actionable_"
                "category_filter"
            ),
        )
    )


    monthly_min_rvol = (
        m6.number_input(
            "Minimum RVOL",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key=(
                "monthly_minimum_rvol"
            ),
        )
    )


    monthly_min_atr = (
        m7.number_input(
            "Minimum ATR %",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key=(
                "monthly_minimum_atr_pct"
            ),
        )
    )


    run_monthly = (
        st.button(
            "🚀 Run Monthly Scanner",
            type="primary",
            use_container_width=True,
            key=(
                "run_monthly_scanner_button"
            ),
        )
    )


    if run_monthly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            st.session_state[
                "monthly_results_raw"
            ] = scan_monthly(
                selected_tickers,
                st.session_state[
                    "market_data"
                ],
            )


    # ========================================================
    # MONTHLY RESULTS
    # ========================================================

    if (
        st.session_state[
            "monthly_results_raw"
        ]
        is not None
    ):

        monthly_results = (
            st.session_state[
                "monthly_results_raw"
            ]
            .copy()
        )

        if monthly_results.empty:

            st.warning(
                "No previous-month "
                "liquidity sweeps found."
            )

        else:

            # ----------------------------------------------
            # SIGNAL
            # ----------------------------------------------

            if (
                monthly_signal_filter
                == "PML Taken"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "Low Taken"
                        ]
                    ]
                )

            elif (
                monthly_signal_filter
                == "PMH Taken"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "High Taken"
                        ]
                    ]
                )

            elif (
                monthly_signal_filter
                == "PML Reclaimed"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "Low Reclaimed"
                        ]
                    ]
                )

            elif (
                monthly_signal_filter
                == "PMH Rejected"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "High Rejected"
                        ]
                    ]
                )

            elif (
                monthly_signal_filter
                == "Bullish Setup"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "Bullish Setup"
                        ]
                    ]
                )

            elif (
                monthly_signal_filter
                == "Bearish Setup"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "Bearish Setup"
                        ]
                    ]
                )

            # ----------------------------------------------
            # STRAT
            # ----------------------------------------------

            if (
                month_strat_filter
                != "All"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "Current Month STRAT"
                        ]
                        == month_strat_filter
                    ]
                )

            if (
                month_weekly_filter
                != "All"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "Current Week STRAT"
                        ]
                        == month_weekly_filter
                    ]
                )

            # ----------------------------------------------
            # ACTIONABLE
            # ----------------------------------------------

            if (
                monthly_actionable_filter
                != "All"
            ):

                if (
                    monthly_category
                    == "Pre-Confirmation"
                ):

                    monthly_results = (
                        monthly_results[
                            monthly_results[
                                "First "
                                "Pre-Confirmation "
                                "Weekly Signal"
                            ]
                            == monthly_actionable_filter
                        ]
                    )

                elif (
                    monthly_category
                    == "Post-Confirmation"
                ):

                    monthly_results = (
                        monthly_results[
                            monthly_results[
                                "First "
                                "Post-Confirmation "
                                "Weekly Signal"
                            ]
                            == monthly_actionable_filter
                        ]
                    )

                else:

                    monthly_results = (
                        monthly_results[
                            (
                                monthly_results[
                                    "First "
                                    "Pre-Confirmation "
                                    "Weekly Signal"
                                ]
                                == monthly_actionable_filter
                            )
                            |
                            (
                                monthly_results[
                                    "First "
                                    "Post-Confirmation "
                                    "Weekly Signal"
                                ]
                                == monthly_actionable_filter
                            )
                        ]
                    )

            elif (
                monthly_category
                == "Pre-Confirmation"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "First "
                            "Pre-Confirmation "
                            "Weekly Signal"
                        ]
                        .notna()
                    ]
                )

            elif (
                monthly_category
                == "Post-Confirmation"
            ):

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "First "
                            "Post-Confirmation "
                            "Weekly Signal"
                        ]
                        .notna()
                    ]
                )

            # ----------------------------------------------
            # RVOL
            # ----------------------------------------------

            if monthly_min_rvol > 0:

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "RVOL"
                        ]
                        .fillna(0)
                        >= monthly_min_rvol
                    ]
                )

            # ----------------------------------------------
            # ATR %
            # ----------------------------------------------

            if monthly_min_atr > 0:

                monthly_results = (
                    monthly_results[
                        monthly_results[
                            "ATR %"
                        ]
                        .fillna(0)
                        >= monthly_min_atr
                    ]
                )

            # ----------------------------------------------
            # DISPLAY
            # ----------------------------------------------

            if monthly_results.empty:

                st.warning(
                    "No monthly signals "
                    "matched the filters."
                )

            else:

                monthly_results = (
                    monthly_results
                    .sort_values(
                        [
                            "Bullish Setup",
                            "Bearish Setup",
                            "ATR %",
                            "RVOL",
                        ],
                        ascending=[
                            False,
                            False,
                            False,
                            False,
                        ],
                        na_position="last",
                    )
                )

                mc1, mc2, mc3, mc4, mc5 = (
                    st.columns(5)
                )

                mc1.metric(
                    "Matches",
                    len(
                        monthly_results
                    ),
                )

                mc2.metric(
                    "PML Taken",
                    int(
                        monthly_results[
                            "Low Taken"
                        ].sum()
                    ),
                )

                mc3.metric(
                    "PMH Taken",
                    int(
                        monthly_results[
                            "High Taken"
                        ].sum()
                    ),
                )

                mc4.metric(
                    "Bullish",
                    int(
                        monthly_results[
                            "Bullish Setup"
                        ].sum()
                    ),
                )

                mc5.metric(
                    "Bearish",
                    int(
                        monthly_results[
                            "Bearish Setup"
                        ].sum()
                    ),
                )

                st.subheader(
                    "🔎 Monthly Scanner Results"
                )

                st.dataframe(
                    monthly_results,
                    use_container_width=True,
                    hide_index=True,
                )

                # ------------------------------------------
                # POST
                # ------------------------------------------

                monthly_post = (
                    monthly_results[
                        monthly_results[
                            "First "
                            "Post-Confirmation "
                            "Weekly Signal"
                        ]
                        .notna()
                    ]
                )

                if not monthly_post.empty:

                    st.subheader(
                        "✅ Monthly "
                        "Post-Confirmation Signals"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Post-Confirmation Event",
                        "First Post-Confirmation Weekly Signal",
                        "Post-Confirmation Week",
                        "Prev Month STRAT",
                        "Current Month STRAT",
                        "Current Week STRAT",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "Signal",
                    ]

                    st.dataframe(
                        monthly_post[
                            available_columns(
                                monthly_post,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # PRE
                # ------------------------------------------

                monthly_pre = (
                    monthly_results[
                        monthly_results[
                            "First "
                            "Pre-Confirmation "
                            "Weekly Signal"
                        ]
                        .notna()
                    ]
                )

                if not monthly_pre.empty:

                    st.subheader(
                        "⚠️ Monthly "
                        "Pre-Confirmation Signals"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Pre-Confirmation Event",
                        "First Pre-Confirmation Weekly Signal",
                        "Pre-Confirmation Week",
                        "Prev Month STRAT",
                        "Current Month STRAT",
                        "Current Week STRAT",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "Signal",
                    ]

                    st.dataframe(
                        monthly_pre[
                            available_columns(
                                monthly_pre,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # BULLISH
                # ------------------------------------------

                monthly_bullish = (
                    monthly_results[
                        monthly_results[
                            "Bullish Setup"
                        ]
                    ]
                )

                if not monthly_bullish.empty:

                    st.subheader(
                        "🟢 Bullish Monthly Setups"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Prev Month Low",
                        "PML Sweep Date",
                        "PML Reclaim Date",
                        "Prev Month STRAT",
                        "Current Month STRAT",
                        "Current Week STRAT",
                        "First Post-Confirmation Weekly Signal",
                        "Post-Confirmation Week",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "% From PML",
                        "Signal",
                    ]

                    st.dataframe(
                        monthly_bullish[
                            available_columns(
                                monthly_bullish,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # ------------------------------------------
                # BEARISH
                # ------------------------------------------

                monthly_bearish = (
                    monthly_results[
                        monthly_results[
                            "Bearish Setup"
                        ]
                    ]
                )

                if not monthly_bearish.empty:

                    st.subheader(
                        "🔴 Bearish Monthly Setups"
                    )

                    columns = [
                        "Ticker",
                        "Asset",
                        "Price",
                        "Prev Month High",
                        "PMH Sweep Date",
                        "PMH Rejection Date",
                        "Prev Month STRAT",
                        "Current Month STRAT",
                        "Current Week STRAT",
                        "First Post-Confirmation Weekly Signal",
                        "Post-Confirmation Week",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",
                        "RVOL",
                        "ATR",
                        "ATR %",
                        "% From PMH",
                        "Signal",
                    ]

                    st.dataframe(
                        monthly_bearish[
                            available_columns(
                                monthly_bearish,
                                columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                monthly_csv = (
                    monthly_results
                    .to_csv(
                        index=False
                    )
                    .encode("utf-8")
                )

                st.download_button(
                    "⬇️ Download Monthly Results",
                    data=monthly_csv,
                    file_name=(
                        "monthly_strat_scanner.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                    key=(
                        "download_monthly_results"
                    ),
                )


# ============================================================
# MARKET CONTEXT TAB
# ============================================================

with market_context_tab:

    st.header(
        "🌎 Market Context"
    )

    st.caption(
        "SPY · QQQ · IWM · VIX · "
        "11 S&P 500 Sector ETFs"
    )

    if not market_ready:

        st.warning(
            "Load market data first."
        )

    else:

        context_df = (
            build_market_context(
                st.session_state[
                    "market_data"
                ]
            )
        )

        if context_df.empty:

            st.warning(
                "No market context "
                "data available."
            )

        else:

            # ================================================
            # INDEX SNAPSHOT
            # ================================================

            st.subheader(
                "🧭 Index Snapshot"
            )

            i1, i2, i3, i4 = (
                st.columns(4)
            )

            cards = [
                ("SPY", i1),
                ("QQQ", i2),
                ("IWM", i3),
                ("^VIX", i4),
            ]

            for ticker, column in cards:

                selected = (
                    context_df[
                        context_df[
                            "Ticker"
                        ]
                        == ticker
                    ]
                )

                if selected.empty:
                    continue

                row = selected.iloc[0]

                return5 = (
                    row[
                        "5D Return %"
                    ]
                )

                if pd.notna(return5):

                    delta = (
                        f"{return5:.2f}% 5D"
                    )

                else:

                    delta = None

                column.metric(
                    ticker.replace(
                        "^",
                        ""
                    ),
                    f'{row["Price"]:.2f}',
                    delta,
                )

                atr_value = (
                    row[
                        "ATR %"
                    ]
                )

                if pd.notna(
                    atr_value
                ):

                    atr_text = (
                        f"{atr_value:.2f}%"
                    )

                else:

                    atr_text = "N/A"

                column.caption(
                    f'{row["Context"]} | '
                    f'ATR% {atr_text} | '
                    f'W {row["Weekly FTFC"]} | '
                    f'M {row["Monthly FTFC"]}'
                )

            # ================================================
            # MAJOR MARKET
            # ================================================

            st.subheader(
                "📊 Major Market Context"
            )

            major = context_df[
                context_df[
                    "Ticker"
                ]
                .isin(
                    [
                        "SPY",
                        "QQQ",
                        "IWM",
                        "^VIX",
                    ]
                )
            ].copy()

            columns = [
                "Ticker",
                "Market",
                "Price",
                "Context",
                "Daily STRAT",
                "Prev Week STRAT",
                "Current Week STRAT",
                "Prev Month STRAT",
                "Current Month STRAT",
                "Weekly FTFC",
                "Monthly FTFC",
                "M/W Alignment",
                "Trend",
                "5D Return %",
                "20D Return %",
                "RVOL",
                "ATR",
                "ATR %",
            ]

            st.dataframe(
                major[
                    available_columns(
                        major,
                        columns,
                    )
                ],
                use_container_width=True,
                hide_index=True,
            )

            # ================================================
            # SECTOR CONTEXT
            # ================================================

            st.subheader(
                "🏭 Sector ETF Context"
            )

            sectors = context_df[
                context_df[
                    "Ticker"
                ]
                .isin(
                    SECTOR_TICKERS
                )
            ].copy()

            if (
                "20D RS vs SPY"
                in sectors.columns
            ):

                sectors = (
                    sectors
                    .sort_values(
                        "20D RS vs SPY",
                        ascending=False,
                        na_position="last",
                    )
                )

            columns = [
                "Ticker",
                "Market",
                "Price",
                "Context",
                "Daily STRAT",
                "Current Week STRAT",
                "Current Month STRAT",
                "Weekly FTFC",
                "Monthly FTFC",
                "M/W Alignment",
                "Trend",
                "5D Return %",
                "20D Return %",
                "20D RS vs SPY",
                "RVOL",
                "ATR",
                "ATR %",
            ]

            st.dataframe(
                sectors[
                    available_columns(
                        sectors,
                        columns,
                    )
                ],
                use_container_width=True,
                hide_index=True,
            )

            # ================================================
            # SECTOR RS
            # ================================================

            st.subheader(
                "🚀 Sector Relative Strength vs SPY"
            )

            columns = [
                "Ticker",
                "Market",
                "5D Return %",
                "20D Return %",
                "20D RS vs SPY",
                "ATR %",
                "Weekly FTFC",
                "Monthly FTFC",
                "Current Week STRAT",
                "Current Month STRAT",
            ]

            sector_rs = sectors[
                available_columns(
                    sectors,
                    columns,
                )
            ].copy()

            if (
                "20D RS vs SPY"
                in sector_rs.columns
            ):

                sector_rs = (
                    sector_rs
                    .sort_values(
                        "20D RS vs SPY",
                        ascending=False,
                        na_position="last",
                    )
                )

            st.dataframe(
                sector_rs,
                use_container_width=True,
                hide_index=True,
            )

            # ================================================
            # BREADTH
            # ================================================

            st.subheader(
                "📈 Market Trend Breadth"
            )

            equity_context = (
                context_df[
                    context_df[
                        "Ticker"
                    ]
                    != "^VIX"
                ]
                .copy()
            )

            total_assets = len(
                equity_context
            )

            above20 = int(
                equity_context[
                    "Above MA20"
                ].sum()
            )

            above50 = int(
                equity_context[
                    "Above MA50"
                ].sum()
            )

            above200 = int(
                equity_context[
                    "Above MA200"
                ].sum()
            )

            b1, b2, b3 = (
                st.columns(3)
            )

            b1.metric(
                "Above 20D MA",
                f"{above20}/{total_assets}",
            )

            b2.metric(
                "Above 50D MA",
                f"{above50}/{total_assets}",
            )

            b3.metric(
                "Above 200D MA",
                f"{above200}/{total_assets}",
            )

            # ================================================
            # WEEK LEVELS
            # ================================================

            st.subheader(
                "📅 Previous Week Levels"
            )

            columns = [
                "Ticker",
                "Market",
                "Price",
                "Prev Week Low",
                "% From PWL",
                "Prev Week High",
                "% From PWH",
                "Prev Week STRAT",
                "Current Week STRAT",
                "Weekly FTFC",
                "RVOL",
                "ATR",
                "ATR %",
            ]

            st.dataframe(
                context_df[
                    available_columns(
                        context_df,
                        columns,
                    )
                ],
                use_container_width=True,
                hide_index=True,
            )

            # ================================================
            # MONTH LEVELS
            # ================================================

            st.subheader(
                "🗓️ Previous Month Levels"
            )

            columns = [
                "Ticker",
                "Market",
                "Price",
                "Prev Month Low",
                "% From PML",
                "Prev Month High",
                "% From PMH",
                "Prev Month STRAT",
                "Current Month STRAT",
                "Monthly FTFC",
                "RVOL",
                "ATR",
                "ATR %",
            ]

            st.dataframe(
                context_df[
                    available_columns(
                        context_df,
                        columns,
                    )
                ],
                use_container_width=True,
                hide_index=True,
            )

            # ================================================
            # CSV
            # ================================================

            context_csv = (
                context_df
                .to_csv(
                    index=False
                )
                .encode("utf-8")
            )

            st.download_button(
                "⬇️ Download Market Context",
                data=context_csv,
                file_name=(
                    "market_context.csv"
                ),
                mime="text/csv",
                use_container_width=True,
                key=(
                    "download_market_context"
                ),
            )
