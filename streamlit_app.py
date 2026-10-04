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
    "2-Week + 1H Reclaim | STRAT | FTFC | RVOL | ATR %"
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

        return sorted(
            set(
                ticker.replace(".", "-")
                for ticker in tickers
            )
        )

    except Exception as exc:
        st.error(
            f"Could not load S&P 500 list: {exc}"
        )
        return []


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
# DAILY DATA DOWNLOAD
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

            if data is None or data.empty:
                continue

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
                            results[ticker] = ticker_df

                    except Exception:
                        continue

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
                    results[ticker] = ticker_df

        except Exception:
            continue

        time.sleep(0.10)

    return results


# ============================================================
# HOURLY DATA DOWNLOAD
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_hourly_market_data(tickers):

    tickers = sorted(set(tickers))
    results = {}

    if not tickers:
        return results

    batch_size = 30

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
                period="60d",
                interval="1h",
                group_by="ticker",
                auto_adjust=False,
                threads=True,
                progress=False,
                timeout=30,
            )

            if data is None or data.empty:
                continue

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
                            results[ticker] = ticker_df

                    except Exception:
                        continue

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
                    results[ticker] = ticker_df

        except Exception:
            continue

        time.sleep(0.10)

    return results


# ============================================================
# DATA CLEANING
# ============================================================

def clean_dataframe(df):

    try:

        if df is None:
            return None

        df = df.copy()

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

        df = df[required].copy()

        for column in required:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
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


def clean_ticker_dataframe(
    market_data,
    ticker,
):

    if ticker not in market_data:
        return None

    return clean_dataframe(
        market_data[ticker]
    )


def clean_hourly_dataframe(
    hourly_data,
    ticker,
):

    if ticker not in hourly_data:
        return None

    return clean_dataframe(
        hourly_data[ticker]
    )


# ============================================================
# STRAT CLASSIFICATION
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

    # Inside Bar
    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):
        return "Inside Bar"

    # Hammer
    if (
        lower_wick >= (
            2 * body_for_ratio
        )
        and
        upper_wick <= body_for_ratio
        and
        body <= candle_range * 0.40
    ):
        return "Hammer"

    # Shooting Star
    if (
        upper_wick >= (
            2 * body_for_ratio
        )
        and
        lower_wick <= body_for_ratio
        and
        body <= candle_range * 0.40
    ):
        return "Shooting Star"

    return None


# ============================================================
# WEEKLY DATA
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

    return (
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


# ============================================================
# MONTHLY DATA
# ============================================================

def build_monthly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index
        .to_period("M")
    )

    temp["TradingDate"] = (
        temp.index
    )

    return (
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


def get_previous_month_strat(df):

    levels = get_monthly_levels(
        df
    )

    if levels is None:
        return "N/A"

    return levels[
        "previous_strat"
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

        current_week = (
            df.index[-1]
            .to_period("W-FRI")
        )

        week_data = df[
            df.index
            .to_period("W-FRI")
            == current_week
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

        current_month = (
            df.index[-1]
            .to_period("M")
        )

        month_data = df[
            df.index
            .to_period("M")
            == current_month
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
            or len(df) < lookback + 1
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
# ATR
# ============================================================

def calculate_atr(
    df,
    period=14,
):

    try:

        if (
            df is None
            or len(df) < period + 1
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

        high_previous = (
            df["High"]
            - previous_close
        ).abs()

        low_previous = (
            df["Low"]
            - previous_close
        ).abs()

        true_range = (
            pd.concat(
                [
                    high_low,
                    high_previous,
                    low_previous,
                ],
                axis=1,
            )
            .max(axis=1)
        )

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

        return {
            "atr":
                round(
                    atr,
                    2,
                ),

            "atr_pct":
                round(
                    (
                        atr / price
                    ) * 100,
                    2,
                ),
        }

    except Exception:

        return {
            "atr": None,
            "atr_pct": None,
        }


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
                    previous_row["High"]
                ),
                float(
                    previous_row["Low"]
                ),
            )
        )

        if actionable is None:
            continue

        if result["post_signal"] is None:

            candidates = []

            if (
                low_reclaimed
                and low_reclaim_date
                is not None
                and date >=
                low_reclaim_date
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
                and date >=
                high_rejection_date
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

        if result["pre_signal"] is None:

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

    weekly = build_weekly_dataframe(
        df
    )

    weekly_periods = list(
        weekly.index
    )

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
                    previous_row["High"]
                ),
                float(
                    previous_row["Low"]
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

        if result["post_signal"] is None:

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

        if result["pre_signal"] is None:

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

            if not (
                low_taken
                or high_taken
            ):
                continue

            low_reclaimed = (
                low_taken
                and price > previous_low
            )

            high_rejected = (
                high_taken
                and price < previous_high
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
                df
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
                    "Ticker": ticker,

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
                and price > previous_low
            )

            high_rejected = (
                high_taken
                and price < previous_high
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
                df
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
# 2-WEEK LIQUIDITY SWEEP + 1H RECLAIM
# ============================================================

def scan_two_week_levels(
    tickers,
    daily_market_data,
    hourly_market_data,
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
            f"2-Week + 1H scan: "
            f"{ticker} "
            f"({index + 1}/{total})"
        )

        try:

            daily_df = (
                clean_ticker_dataframe(
                    daily_market_data,
                    ticker,
                )
            )

            hourly_df = (
                clean_hourly_dataframe(
                    hourly_market_data,
                    ticker,
                )
            )

            if (
                daily_df is None
                or hourly_df is None
                or len(daily_df) < 30
                or len(hourly_df) < 3
            ):
                continue

            # =================================================
            # TWO PREVIOUS COMPLETED WEEKS
            # =================================================

            weekly = (
                build_weekly_dataframe(
                    daily_df
                )
            )

            current_week = (
                daily_df.index[-1]
                .to_period("W-FRI")
            )

            completed_weeks = (
                weekly[
                    weekly.index
                    < current_week
                ]
                .copy()
            )

            if len(
                completed_weeks
            ) < 2:
                continue

            week_1 = (
                completed_weeks
                .iloc[-1]
            )

            week_2 = (
                completed_weeks
                .iloc[-2]
            )

            week_1_low = float(
                week_1["Low"]
            )

            week_2_low = float(
                week_2["Low"]
            )

            week_1_high = float(
                week_1["High"]
            )

            week_2_high = float(
                week_2["High"]
            )

            # =================================================
            # REQUIRED SWEEP / RECLAIM LEVEL
            # ============================================================
            #
            # LOW EXAMPLE:
            #
            # Week -1 = $185
            # Week -2 = $181
            #
            # Required level = $181
            #
            # Price < $181
            # → Both lows swept
            # → 1H Close > $181
            # → Actionable Signal
            #
            # ============================================================

            required_low = min(
                week_1_low,
                week_2_low,
            )

            required_high = max(
                week_1_high,
                week_2_high,
            )

            # =================================================
            # PREVIOUS MONTH STRAT
            # =================================================

            monthly_levels = (
                get_monthly_levels(
                    daily_df
                )
            )

            if (
                monthly_levels
                is not None
            ):

                previous_month_strat = (
                    monthly_levels[
                        "previous_strat"
                    ]
                )

            else:

                previous_month_strat = (
                    "N/A"
                )

            # =================================================
            # CURRENT WEEK HOURLY DATA
            # =================================================

            hourly_current_week = (
                hourly_df[
                    hourly_df.index
                    .to_period("W-FRI")
                    == current_week
                ]
                .copy()
            )

            if (
                len(
                    hourly_current_week
                )
                < 2
            ):
                continue

            # =================================================
            # STATE VARIABLES
            # =================================================

            low_swept = False
            low_sweep_time = None
            low_sweep_price = None

            bullish_signal = None
            bullish_signal_time = None
            bullish_close = None
            bullish_hourly_strat = None
            bullish_pattern = None
            bullish_same_candle = False

            high_swept = False
            high_sweep_time = None
            high_sweep_price = None

            bearish_signal = None
            bearish_signal_time = None
            bearish_close = None
            bearish_hourly_strat = None
            bearish_pattern = None
            bearish_same_candle = False

            # =================================================
            # WALK 1H CANDLES IN ORDER
            # =================================================

            for i in range(
                1,
                len(
                    hourly_current_week
                ),
            ):

                previous = (
                    hourly_current_week
                    .iloc[i - 1]
                )

                current = (
                    hourly_current_week
                    .iloc[i]
                )

                timestamp = (
                    hourly_current_week
                    .index[i]
                )

                current_open = float(
                    current["Open"]
                )

                current_high = float(
                    current["High"]
                )

                current_low = float(
                    current["Low"]
                )

                current_close = float(
                    current["Close"]
                )

                previous_high = float(
                    previous["High"]
                )

                previous_low = float(
                    previous["Low"]
                )

                # =================================================
                # ACTIONABLE / STRAT
                # =================================================

                actionable = (
                    classify_actionable_candle(
                        current_open,
                        current_high,
                        current_low,
                        current_close,
                        previous_high,
                        previous_low,
                    )
                )

                hourly_strat = (
                    classify_strat_candle(
                        current_open,
                        current_high,
                        current_low,
                        current_close,
                        previous_high,
                        previous_low,
                    )
                )

                # =================================================
                # LOW SWEEP
                # =================================================

                low_sweep_this_candle = (
                    False
                )

                if (
                    not low_swept
                    and
                    current_low
                    < required_low
                ):

                    low_swept = True

                    low_sweep_this_candle = (
                        True
                    )

                    low_sweep_time = (
                        timestamp
                    )

                    low_sweep_price = (
                        current_low
                    )

                # =================================================
                # HIGH SWEEP
                # =================================================

                high_sweep_this_candle = (
                    False
                )

                if (
                    not high_swept
                    and
                    current_high
                    > required_high
                ):

                    high_swept = True

                    high_sweep_this_candle = (
                        True
                    )

                    high_sweep_time = (
                        timestamp
                    )

                    high_sweep_price = (
                        current_high
                    )

                # =================================================
                # BULLISH ACTIONABLE
                # =================================================

                bullish_actionable = (
                    False
                )

                bullish_signal_name = (
                    None
                )

                if actionable in [
                    "Hammer",
                    "Inside Bar",
                ]:

                    bullish_actionable = (
                        True
                    )

                    bullish_signal_name = (
                        actionable
                    )

                elif hourly_strat in [
                    "2U Green",
                    "2D Green",
                ]:

                    bullish_actionable = (
                        True
                    )

                    bullish_signal_name = (
                        hourly_strat
                    )

                # =================================================
                # BEARISH ACTIONABLE
                # =================================================

                bearish_actionable = (
                    False
                )

                bearish_signal_name = (
                    None
                )

                if actionable in [
                    "Shooting Star",
                    "Inside Bar",
                ]:

                    bearish_actionable = (
                        True
                    )

                    bearish_signal_name = (
                        actionable
                    )

                elif hourly_strat in [
                    "2D Red",
                    "2U Red",
                ]:

                    bearish_actionable = (
                        True
                    )

                    bearish_signal_name = (
                        hourly_strat
                    )

                # =================================================
                # BULLISH SEQUENCE
                # =================================================

                if (
                    low_swept
                    and
                    bullish_signal
                    is None
                ):

                    one_hour_reclaim = (
                        current_close
                        > required_low
                    )

                    if (
                        one_hour_reclaim
                        and
                        bullish_actionable
                    ):

                        bullish_signal = (
                            bullish_signal_name
                        )

                        bullish_signal_time = (
                            timestamp
                        )

                        bullish_close = (
                            current_close
                        )

                        bullish_hourly_strat = (
                            hourly_strat
                        )

                        bullish_pattern = (
                            actionable
                        )

                        bullish_same_candle = (
                            low_sweep_this_candle
                        )

                # =================================================
                # BEARISH SEQUENCE
                # =================================================

                if (
                    high_swept
                    and
                    bearish_signal
                    is None
                ):

                    one_hour_rejection = (
                        current_close
                        < required_high
                    )

                    if (
                        one_hour_rejection
                        and
                        bearish_actionable
                    ):

                        bearish_signal = (
                            bearish_signal_name
                        )

                        bearish_signal_time = (
                            timestamp
                        )

                        bearish_close = (
                            current_close
                        )

                        bearish_hourly_strat = (
                            hourly_strat
                        )

                        bearish_pattern = (
                            actionable
                        )

                        bearish_same_candle = (
                            high_sweep_this_candle
                        )

            # =================================================
            # CONFIRMED SETUPS
            # =================================================

            bullish_setup = (
                low_swept
                and
                bullish_signal
                is not None
            )

            bearish_setup = (
                high_swept
                and
                bearish_signal
                is not None
            )

            if not (
                bullish_setup
                or
                bearish_setup
            ):
                continue

            # =================================================
            # METRICS / HIGHER TIMEFRAME CONTEXT
            # =================================================

            current_price = float(
                daily_df[
                    "Close"
                ]
                .iloc[-1]
            )

            daily_strat = (
                get_daily_strat(
                    daily_df
                )
            )

            current_week_strat = (
                get_current_week_strat(
                    daily_df
                )
            )

            ftfc = (
                calculate_ftfc(
                    daily_df
                )
            )

            rvol = (
                calculate_rvol(
                    daily_df
                )
            )

            atr_data = (
                calculate_atr(
                    daily_df
                )
            )

            # =================================================
            # BULLISH ROW
            # =================================================

            if bullish_setup:

                sequence_type = (
                    "Same 1H Candle"
                    if bullish_same_candle
                    else
                    "Later 1H Candle"
                )

                pct_below_level = (
                    (
                        low_sweep_price
                        - required_low
                    )
                    / required_low
                ) * 100

                reclaim_pct = (
                    (
                        bullish_close
                        - required_low
                    )
                    / required_low
                ) * 100

                rows.append(
                    {
                        "Ticker":
                            ticker,

                        "Direction":
                            "Bullish",

                        "Asset":
                            get_asset_type(
                                ticker
                            ),

                        "Price":
                            round(
                                current_price,
                                2,
                            ),

                        "Week -1 Low":
                            round(
                                week_1_low,
                                2,
                            ),

                        "Week -2 Low":
                            round(
                                week_2_low,
                                2,
                            ),

                        "2-Week Low":
                            round(
                                required_low,
                                2,
                            ),

                        "Sweep Price":
                            round(
                                low_sweep_price,
                                2,
                            ),

                        "Sweep %":
                            round(
                                pct_below_level,
                                2,
                            ),

                        "Sweep Time":
                            (
                                low_sweep_time
                                .strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                            ),

                        "1H Close":
                            round(
                                bullish_close,
                                2,
                            ),

                        "Close vs Level %":
                            round(
                                reclaim_pct,
                                2,
                            ),

                        "Reclaim Level":
                            round(
                                required_low,
                                2,
                            ),

                        "1H Reclaimed":
                            True,

                        "Sequence":
                            sequence_type,

                        "1H Actionable Signal":
                            bullish_signal,

                        "1H Candle Pattern":
                            (
                                bullish_pattern
                                if bullish_pattern
                                is not None
                                else
                                bullish_signal
                            ),

                        "1H STRAT":
                            bullish_hourly_strat,

                        "Signal Time":
                            (
                                bullish_signal_time
                                .strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                            ),

                        "Daily STRAT":
                            daily_strat,

                        "Current Week STRAT":
                            current_week_strat,

                        # NEW
                        "Previous Month STRAT":
                            previous_month_strat,

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

                        "Signal":
                            (
                                f"Price < "
                                f"{required_low:.2f} "
                                f"→ Both Weekly Lows Swept "
                                f"→ 1H Close > "
                                f"{required_low:.2f} "
                                f"→ {bullish_signal}"
                            ),
                    }
                )

            # =================================================
            # BEARISH ROW
            # =================================================

            if bearish_setup:

                sequence_type = (
                    "Same 1H Candle"
                    if bearish_same_candle
                    else
                    "Later 1H Candle"
                )

                pct_above_level = (
                    (
                        high_sweep_price
                        - required_high
                    )
                    / required_high
                ) * 100

                rejection_pct = (
                    (
                        bearish_close
                        - required_high
                    )
                    / required_high
                ) * 100

                rows.append(
                    {
                        "Ticker":
                            ticker,

                        "Direction":
                            "Bearish",

                        "Asset":
                            get_asset_type(
                                ticker
                            ),

                        "Price":
                            round(
                                current_price,
                                2,
                            ),

                        "Week -1 High":
                            round(
                                week_1_high,
                                2,
                            ),

                        "Week -2 High":
                            round(
                                week_2_high,
                                2,
                            ),

                        "2-Week High":
                            round(
                                required_high,
                                2,
                            ),

                        "Sweep Price":
                            round(
                                high_sweep_price,
                                2,
                            ),

                        "Sweep %":
                            round(
                                pct_above_level,
                                2,
                            ),

                        "Sweep Time":
                            (
                                high_sweep_time
                                .strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                            ),

                        "1H Close":
                            round(
                                bearish_close,
                                2,
                            ),

                        "Close vs Level %":
                            round(
                                rejection_pct,
                                2,
                            ),

                        "Rejection Level":
                            round(
                                required_high,
                                2,
                            ),

                        "1H Rejected":
                            True,

                        "Sequence":
                            sequence_type,

                        "1H Actionable Signal":
                            bearish_signal,

                        "1H Candle Pattern":
                            (
                                bearish_pattern
                                if bearish_pattern
                                is not None
                                else
                                bearish_signal
                            ),

                        "1H STRAT":
                            bearish_hourly_strat,

                        "Signal Time":
                            (
                                bearish_signal_time
                                .strftime(
                                    "%Y-%m-%d %H:%M"
                                )
                            ),

                        "Daily STRAT":
                            daily_strat,

                        "Current Week STRAT":
                            current_week_strat,

                        # NEW
                        "Previous Month STRAT":
                            previous_month_strat,

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

                        "Signal":
                            (
                                f"Price > "
                                f"{required_high:.2f} "
                                f"→ Both Weekly Highs Swept "
                                f"→ 1H Close < "
                                f"{required_high:.2f} "
                                f"→ {bearish_signal}"
                            ),
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
# SAFE COLUMN HELPER
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


st.sidebar.metric(
    "Scanner Universe",
    len(
        selected_tickers
    ),
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
    "hourly_market_data"
    not in st.session_state
):
    st.session_state[
        "hourly_market_data"
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


if (
    "two_week_results_raw"
    not in st.session_state
):
    st.session_state[
        "two_week_results_raw"
    ] = None


# ============================================================
# LOAD DATA
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
        "Downloading daily market data..."
    ):

        market_data = (
            download_market_data(
                download_tickers
            )
        )

    with st.spinner(
        "Downloading 1-hour market data..."
    ):

        hourly_market_data = (
            download_hourly_market_data(
                selected_tickers
            )
        )

    st.session_state[
        "market_data"
    ] = market_data

    st.session_state[
        "hourly_market_data"
    ] = hourly_market_data

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

    st.session_state[
        "two_week_results_raw"
    ] = None

    st.sidebar.success(
        f"Daily: "
        f"{len(market_data)} | "
        f"1H: "
        f"{len(hourly_market_data)}"
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


hourly_ready = (
    market_ready
    and
    st.session_state[
        "hourly_market_data"
    ]
    is not None
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
    two_week_tab,
    market_context_tab,
) = st.tabs(
    [
        "📅 Weekly Scanner",
        "🗓️ Monthly Scanner",
        "🎯 2-Week + 1H Reclaim",
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
            key="weekly_signal_filter",
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
                "weekly_daily_strat_filter"
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
                "weekly_actionable_filter"
            ),
        )
    )

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
                "weekly_category_filter"
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
            key="weekly_min_rvol",
        )
    )

    weekly_min_atr = (
        w7.number_input(
            "Minimum ATR %",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key="weekly_min_atr",
        )
    )

    run_weekly = (
        st.button(
            "🚀 Run Weekly Scanner",
            type="primary",
            use_container_width=True,
            key="run_weekly_scanner",
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
                                "First Pre-Confirmation Signal"
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
                                "First Post-Confirmation Signal"
                            ]
                            == weekly_actionable_filter
                        ]
                    )

                else:

                    weekly_results = (
                        weekly_results[
                            (
                                weekly_results[
                                    "First Pre-Confirmation Signal"
                                ]
                                == weekly_actionable_filter
                            )
                            |
                            (
                                weekly_results[
                                    "First Post-Confirmation Signal"
                                ]
                                == weekly_actionable_filter
                            )
                        ]
                    )

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

            if weekly_results.empty:

                st.warning(
                    "No weekly signals "
                    "matched the filters."
                )

            else:

                st.dataframe(
                    weekly_results,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "⬇️ Download Weekly Results",
                    data=(
                        weekly_results
                        .to_csv(
                            index=False
                        )
                        .encode("utf-8")
                    ),
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

    m1, m2, m3 = (
        st.columns(3)
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
                "monthly_month_strat_filter"
            ),
        )
    )

    month_weekly_filter = (
        m3.selectbox(
            "Current Week STRAT",
            STRAT_OPTIONS,
            key=(
                "monthly_week_strat_filter"
            ),
        )
    )

    run_monthly = (
        st.button(
            "🚀 Run Monthly Scanner",
            type="primary",
            use_container_width=True,
            key="run_monthly_scanner",
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
                "No monthly sweeps found."
            )

        else:

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

            if monthly_results.empty:

                st.warning(
                    "No monthly signals "
                    "matched the filters."
                )

            else:

                st.dataframe(
                    monthly_results,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "⬇️ Download Monthly Results",
                    data=(
                        monthly_results
                        .to_csv(
                            index=False
                        )
                        .encode("utf-8")
                    ),
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
# 2-WEEK + 1H TAB
# ============================================================

with two_week_tab:

    st.header(
        "🎯 2-Week Liquidity Sweep + 1H Reclaim"
    )

    st.caption(
        "Bullish: Price < lower of previous 2 weekly lows "
        "→ both lows swept → 1H Close > level "
        "→ actionable signal | "
        "Bearish: Price > higher of previous 2 weekly highs "
        "→ both highs swept → 1H Close < level "
        "→ actionable signal"
    )

    st.info(
        "Example: Previous weekly lows = "
        "$185 and $181. "
        "Price < $181 → both lows swept → "
        "1H close > $181 → actionable 1H signal."
    )

    # ========================================================
    # FILTER ROW 1
    # ========================================================

    tw1, tw2, tw3 = (
        st.columns(3)
    )

    two_week_direction = (
        tw1.selectbox(
            "Direction",
            [
                "All",
                "Bullish",
                "Bearish",
            ],
            key=(
                "two_week_direction"
            ),
        )
    )

    two_week_signal = (
        tw2.selectbox(
            "1H Actionable Signal",
            [
                "All",
                "Hammer",
                "Shooting Star",
                "Inside Bar",
                "2U Green",
                "2D Green",
                "2U Red",
                "2D Red",
            ],
            key=(
                "two_week_signal"
            ),
        )
    )

    # NEW
    previous_month_strat_filter = (
        tw3.selectbox(
            "Previous Month STRAT",
            STRAT_OPTIONS,
            key=(
                "two_week_previous_month_"
                "strat_filter"
            ),
        )
    )

    # ========================================================
    # FILTER ROW 2
    # ========================================================

    tw4, tw5, tw6 = (
        st.columns(3)
    )

    current_week_filter = (
        tw4.selectbox(
            "Current Week STRAT",
            STRAT_OPTIONS,
            key=(
                "two_week_current_week_"
                "strat_filter"
            ),
        )
    )

    sequence_filter = (
        tw5.selectbox(
            "Sweep / Reclaim Timing",
            [
                "All",
                "Same 1H Candle",
                "Later 1H Candle",
            ],
            key=(
                "two_week_sequence_filter"
            ),
        )
    )

    ftfc_filter = (
        tw6.selectbox(
            "M/W FTFC",
            [
                "All",
                "FTFC Up",
                "FTFC Down",
                "Mixed",
            ],
            key=(
                "two_week_ftfc_filter"
            ),
        )
    )

    # ========================================================
    # FILTER ROW 3
    # ========================================================

    tw7, tw8 = (
        st.columns(2)
    )

    two_week_min_rvol = (
        tw7.number_input(
            "Minimum RVOL",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key=(
                "two_week_min_rvol"
            ),
        )
    )

    two_week_min_atr = (
        tw8.number_input(
            "Minimum ATR %",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=0.1,
            key=(
                "two_week_min_atr"
            ),
        )
    )

    run_two_week = (
        st.button(
            "🚀 Run 2-Week + 1H Scanner",
            type="primary",
            use_container_width=True,
            key=(
                "run_two_week_scanner"
            ),
        )
    )

    if run_two_week:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        elif not hourly_ready:

            st.warning(
                "1-hour market data "
                "is not loaded."
            )

        else:

            st.session_state[
                "two_week_results_raw"
            ] = scan_two_week_levels(
                selected_tickers,
                st.session_state[
                    "market_data"
                ],
                st.session_state[
                    "hourly_market_data"
                ],
            )

    # ========================================================
    # RESULTS
    # ========================================================

    if (
        st.session_state[
            "two_week_results_raw"
        ]
        is not None
    ):

        two_week_results = (
            st.session_state[
                "two_week_results_raw"
            ]
            .copy()
        )

        if two_week_results.empty:

            st.warning(
                "No confirmed 2-week "
                "sweep + 1H reclaim/rejection "
                "setups found."
            )

        else:

            # =================================================
            # DIRECTION
            # =================================================

            if (
                two_week_direction
                != "All"
            ):

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "Direction"
                        ]
                        == two_week_direction
                    ]
                )

            # =================================================
            # ACTIONABLE SIGNAL
            # =================================================

            if (
                two_week_signal
                != "All"
            ):

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "1H Actionable Signal"
                        ]
                        == two_week_signal
                    ]
                )

            # =================================================
            # PREVIOUS MONTH STRAT FILTER
            # =================================================

            if (
                previous_month_strat_filter
                != "All"
            ):

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "Previous Month STRAT"
                        ]
                        == previous_month_strat_filter
                    ]
                )

            # =================================================
            # CURRENT WEEK STRAT
            # =================================================

            if (
                current_week_filter
                != "All"
            ):

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "Current Week STRAT"
                        ]
                        == current_week_filter
                    ]
                )

            # =================================================
            # SEQUENCE
            # =================================================

            if (
                sequence_filter
                != "All"
            ):

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "Sequence"
                        ]
                        == sequence_filter
                    ]
                )

            # =================================================
            # FTFC
            # =================================================

            if ftfc_filter != "All":

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "FTFC"
                        ]
                        == ftfc_filter
                    ]
                )

            # =================================================
            # RVOL
            # =================================================

            if two_week_min_rvol > 0:

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "RVOL"
                        ]
                        .fillna(0)
                        >= two_week_min_rvol
                    ]
                )

            # =================================================
            # ATR %
            # =================================================

            if two_week_min_atr > 0:

                two_week_results = (
                    two_week_results[
                        two_week_results[
                            "ATR %"
                        ]
                        .fillna(0)
                        >= two_week_min_atr
                    ]
                )

            if two_week_results.empty:

                st.warning(
                    "No 2-week setups matched "
                    "the current filters."
                )

            else:

                two_week_results = (
                    two_week_results
                    .sort_values(
                        [
                            "ATR %",
                            "RVOL",
                        ],
                        ascending=[
                            False,
                            False,
                        ],
                        na_position="last",
                    )
                )

                # =================================================
                # METRICS
                # =================================================

                t1, t2, t3, t4 = (
                    st.columns(4)
                )

                t1.metric(
                    "Confirmed Setups",
                    len(
                        two_week_results
                    ),
                )

                t2.metric(
                    "Bullish",
                    int(
                        (
                            two_week_results[
                                "Direction"
                            ]
                            == "Bullish"
                        )
                        .sum()
                    ),
                )

                t3.metric(
                    "Bearish",
                    int(
                        (
                            two_week_results[
                                "Direction"
                            ]
                            == "Bearish"
                        )
                        .sum()
                    ),
                )

                t4.metric(
                    "Same 1H Candle",
                    int(
                        (
                            two_week_results[
                                "Sequence"
                            ]
                            == "Same 1H Candle"
                        )
                        .sum()
                    ),
                )

                # =================================================
                # ALL SETUPS
                # =================================================

                st.subheader(
                    "🔎 Confirmed "
                    "2-Week + 1H Setups"
                )

                display_columns = [
                    "Ticker",
                    "Direction",
                    "Price",

                    "Week -1 Low",
                    "Week -2 Low",
                    "2-Week Low",

                    "Week -1 High",
                    "Week -2 High",
                    "2-Week High",

                    "Sweep Price",
                    "Sweep Time",

                    "1H Close",

                    "Reclaim Level",
                    "Rejection Level",

                    "Sequence",

                    "1H Actionable Signal",
                    "1H Candle Pattern",
                    "1H STRAT",

                    "Signal Time",

                    "Daily STRAT",
                    "Current Week STRAT",

                    # NEW
                    "Previous Month STRAT",

                    "Weekly FTFC",
                    "Monthly FTFC",
                    "FTFC",

                    "RVOL",
                    "ATR",
                    "ATR %",

                    "Signal",
                ]

                st.dataframe(
                    two_week_results[
                        available_columns(
                            two_week_results,
                            display_columns,
                        )
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # BULLISH SETUPS
                # =================================================

                bullish_results = (
                    two_week_results[
                        two_week_results[
                            "Direction"
                        ]
                        == "Bullish"
                    ]
                )

                if not bullish_results.empty:

                    st.subheader(
                        "🟢 Two Weekly Lows Swept "
                        "+ 1H Reclaim"
                    )

                    bullish_columns = [
                        "Ticker",
                        "Price",

                        "Week -1 Low",
                        "Week -2 Low",
                        "2-Week Low",

                        "Sweep Price",
                        "Sweep %",
                        "Sweep Time",

                        "1H Close",
                        "Close vs Level %",
                        "Reclaim Level",

                        "Sequence",

                        "1H Actionable Signal",
                        "1H Candle Pattern",
                        "1H STRAT",

                        "Signal Time",

                        "Daily STRAT",
                        "Current Week STRAT",

                        # NEW
                        "Previous Month STRAT",

                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",

                        "RVOL",
                        "ATR",
                        "ATR %",

                        "Signal",
                    ]

                    st.dataframe(
                        bullish_results[
                            available_columns(
                                bullish_results,
                                bullish_columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # =================================================
                # BEARISH SETUPS
                # =================================================

                bearish_results = (
                    two_week_results[
                        two_week_results[
                            "Direction"
                        ]
                        == "Bearish"
                    ]
                )

                if not bearish_results.empty:

                    st.subheader(
                        "🔴 Two Weekly Highs Swept "
                        "+ 1H Rejection"
                    )

                    bearish_columns = [
                        "Ticker",
                        "Price",

                        "Week -1 High",
                        "Week -2 High",
                        "2-Week High",

                        "Sweep Price",
                        "Sweep %",
                        "Sweep Time",

                        "1H Close",
                        "Close vs Level %",
                        "Rejection Level",

                        "Sequence",

                        "1H Actionable Signal",
                        "1H Candle Pattern",
                        "1H STRAT",

                        "Signal Time",

                        "Daily STRAT",
                        "Current Week STRAT",

                        # NEW
                        "Previous Month STRAT",

                        "Weekly FTFC",
                        "Monthly FTFC",
                        "FTFC",

                        "RVOL",
                        "ATR",
                        "ATR %",

                        "Signal",
                    ]

                    st.dataframe(
                        bearish_results[
                            available_columns(
                                bearish_results,
                                bearish_columns,
                            )
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                # =================================================
                # PREVIOUS MONTH STRAT BREAKDOWN
                # =================================================

                st.subheader(
                    "🗓️ Previous Month STRAT Breakdown"
                )

                month_breakdown = (
                    two_week_results[
                        "Previous Month STRAT"
                    ]
                    .fillna("N/A")
                    .value_counts()
                    .rename_axis(
                        "Previous Month STRAT"
                    )
                    .reset_index(
                        name="Setups"
                    )
                )

                st.dataframe(
                    month_breakdown,
                    use_container_width=True,
                    hide_index=True,
                )

                # =================================================
                # DOWNLOAD
                # =================================================

                st.download_button(
                    "⬇️ Download "
                    "2-Week + 1H Results",
                    data=(
                        two_week_results
                        .to_csv(
                            index=False
                        )
                        .encode("utf-8")
                    ),
                    file_name=(
                        "two_week_1h_scanner.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                    key=(
                        "download_two_week_results"
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
        "Sector ETFs"
    )

    if not market_ready:

        st.warning(
            "Load market data first."
        )

    else:

        rows = []

        for ticker in (
            MARKET_CONTEXT_TICKERS
        ):

            df = (
                clean_ticker_dataframe(
                    st.session_state[
                        "market_data"
                    ],
                    ticker,
                )
            )

            if (
                df is None
                or len(df) < 30
            ):
                continue

            ftfc = (
                calculate_ftfc(
                    df
                )
            )

            atr = (
                calculate_atr(
                    df
                )
            )

            rvol = (
                calculate_rvol(
                    df
                )
            )

            weekly_levels = (
                get_weekly_levels(
                    df
                )
            )

            monthly_levels = (
                get_monthly_levels(
                    df
                )
            )

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
                            float(
                                df[
                                    "Close"
                                ]
                                .iloc[-1]
                            ),
                            2,
                        ),

                    "Daily STRAT":
                        get_daily_strat(
                            df
                        ),

                    "Current Week STRAT":
                        (
                            weekly_levels[
                                "current_strat"
                            ]
                            if weekly_levels
                            else "N/A"
                        ),

                    "Previous Month STRAT":
                        (
                            monthly_levels[
                                "previous_strat"
                            ]
                            if monthly_levels
                            else "N/A"
                        ),

                    "Current Month STRAT":
                        (
                            monthly_levels[
                                "current_strat"
                            ]
                            if monthly_levels
                            else "N/A"
                        ),

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
                        atr[
                            "atr"
                        ],

                    "ATR %":
                        atr[
                            "atr_pct"
                        ],
                }
            )

        context_df = (
            pd.DataFrame(
                rows
            )
        )

        if context_df.empty:

            st.warning(
                "No market context "
                "data available."
            )

        else:

            st.dataframe(
                context_df,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "⬇️ Download Market Context",
                data=(
                    context_df
                    .to_csv(
                        index=False
                    )
                    .encode("utf-8")
                ),
                file_name=(
                    "market_context.csv"
                ),
                mime="text/csv",
                use_container_width=True,
                key=(
                    "download_market_context"
                ),
            )
