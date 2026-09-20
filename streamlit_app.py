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

st.title("📊 STRAT Market Scanner")

st.caption(
    "S&P 500 + Nasdaq-100 + Market ETFs + Sector ETFs | "
    "Weekly / Monthly Liquidity Sweeps + Market Context"
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
# ETF UNIVERSE
# ============================================================

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
            "XLU"
        }
    )


# ============================================================
# ETF NAMES
# ============================================================

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
    "XLU": "Utilities ETF"
}


# ============================================================
# MARKET CONTEXT UNIVERSE
# ============================================================

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
    "XLU"
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
    "XLU": "Utilities"
}


# ============================================================
# ASSET TYPE
# ============================================================

def get_asset_type(ticker):

    if ticker in ETF_NAMES:
        return ETF_NAMES[ticker]

    if ticker == "^VIX":
        return "Volatility Index"

    return "Stock"


# ============================================================
# DOWNLOAD MARKET DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    results = {}

    tickers = sorted(
        set(tickers)
    )

    if not tickers:
        return results

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

            # MULTI-TICKER DOWNLOAD

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

                            results[ticker] = (
                                ticker_df
                            )

                    except Exception:
                        continue

            # SINGLE TICKER

            else:

                ticker = batch[0]

                ticker_df = (
                    data.copy()
                )

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

                    results[ticker] = (
                        ticker_df
                    )

        except Exception:
            continue

        time.sleep(0.20)

    return results


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

        df = (
            market_data[ticker]
            .copy()
        )

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
            col in df.columns
            for col in required
        ):
            return None

        df = df[
            required
        ].copy()

        for col in required:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ]
        )

        if df.empty:
            return None

        df.index = (
            pd.to_datetime(
                df.index
            )
        )

        try:

            df.index = (
                df.index
                .tz_localize(None)
            )

        except Exception:
            pass

        return (
            df.sort_index()
        )

    except Exception:
        return None


# ============================================================
# STRAT CLASSIFICATION
# ============================================================

def classify_strat_candle(
    current_open,
    current_high,
    current_low,
    current_close,
    previous_high,
    previous_low
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


# ============================================================
# ACTIONABLE CANDLE
# ============================================================

def classify_actionable_candle(
    current_open,
    current_high,
    current_low,
    current_close,
    previous_high,
    previous_low
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
            current_close
        )
    )

    lower_wick = (
        min(
            current_open,
            current_close
        )
        - current_low
    )

    body_for_ratio = max(
        body,
        candle_range * 0.05
    )

    # INSIDE BAR

    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):

        return "Inside Bar"

    # HAMMER

    if (
        lower_wick >=
        2 * body_for_ratio
        and
        upper_wick <=
        body_for_ratio
        and
        body <=
        candle_range * 0.40
    ):

        return "Hammer"

    # SHOOTING STAR

    if (
        upper_wick >=
        2 * body_for_ratio
        and
        lower_wick <=
        body_for_ratio
        and
        body <=
        candle_range * 0.40
    ):

        return "Shooting Star"

    return None


# ============================================================
# DAILY STRAT
# ============================================================

def get_daily_strat(df):

    if (
        df is None
        or
        len(df) < 2
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
        float(previous["Low"])
    )


# ============================================================
# WEEKLY DATA
# ============================================================

def build_weekly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index
        .to_period("W-FRI")
    )

    weekly = (
        temp.groupby("Period")
        .agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum")
        )
    )

    return weekly


# ============================================================
# MONTHLY DATA
# ============================================================

def build_monthly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index
        .to_period("M")
    )

    monthly = (
        temp.groupby("Period")
        .agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum")
        )
    )

    return monthly


# ============================================================
# WEEKLY LEVELS
# ============================================================

def get_weekly_levels(df):

    weekly = (
        build_weekly_dataframe(
            df
        )
    )

    if len(weekly) < 3:
        return None

    current_period = (
        df.index[-1]
        .to_period("W-FRI")
    )

    if (
        current_period
        not in weekly.index
    ):
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

    previous = (
        completed.iloc[-1]
    )

    two_back = (
        completed.iloc[-2]
    )

    previous_strat = (
        classify_strat_candle(
            float(previous["Open"]),
            float(previous["High"]),
            float(previous["Low"]),
            float(previous["Close"]),
            float(two_back["High"]),
            float(two_back["Low"])
        )
    )

    current_strat = (
        classify_strat_candle(
            float(current["Open"]),
            float(current["High"]),
            float(current["Low"]),
            float(current["Close"]),
            float(previous["High"]),
            float(previous["Low"])
        )
    )

    return {

        "previous_open":
            float(previous["Open"]),

        "previous_high":
            float(previous["High"]),

        "previous_low":
            float(previous["Low"]),

        "previous_close":
            float(previous["Close"]),

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
            current_period
    }


# ============================================================
# MONTHLY LEVELS
# ============================================================

def get_monthly_levels(df):

    monthly = (
        build_monthly_dataframe(
            df
        )
    )

    if len(monthly) < 3:
        return None

    current_period = (
        df.index[-1]
        .to_period("M")
    )

    if (
        current_period
        not in monthly.index
    ):
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

    previous = (
        completed.iloc[-1]
    )

    two_back = (
        completed.iloc[-2]
    )

    previous_strat = (
        classify_strat_candle(
            float(previous["Open"]),
            float(previous["High"]),
            float(previous["Low"]),
            float(previous["Close"]),
            float(two_back["High"]),
            float(two_back["Low"])
        )
    )

    current_strat = (
        classify_strat_candle(
            float(current["Open"]),
            float(current["High"]),
            float(current["Low"]),
            float(current["Close"]),
            float(previous["High"]),
            float(previous["Low"])
        )
    )

    return {

        "previous_open":
            float(previous["Open"]),

        "previous_high":
            float(previous["High"]),

        "previous_low":
            float(previous["Low"]),

        "previous_close":
            float(previous["Close"]),

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
            current_period
    }


# ============================================================
# CURRENT WEEK STRAT
# ============================================================

def get_current_week_strat(df):

    levels = (
        get_weekly_levels(
            df
        )
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

        # WEEKLY

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
            week_data[
                "Open"
            ].iloc[0]
        )

        if price > weekly_open:

            weekly = "Up"

        elif price < weekly_open:

            weekly = "Down"

        else:

            weekly = "Neutral"

        # MONTHLY

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
            month_data[
                "Open"
            ].iloc[0]
        )

        if price > monthly_open:

            monthly = "Up"

        elif price < monthly_open:

            monthly = "Down"

        else:

            monthly = "Neutral"

        if (
            weekly == "Up"
            and
            monthly == "Up"
        ):

            alignment = (
                "FTFC Up"
            )

        elif (
            weekly == "Down"
            and
            monthly == "Down"
        ):

            alignment = (
                "FTFC Down"
            )

        else:

            alignment = (
                "Mixed"
            )

        return {

            "weekly":
                weekly,

            "monthly":
                monthly,

            "alignment":
                alignment
        }

    except Exception:

        return {

            "weekly": "N/A",
            "monthly": "N/A",
            "alignment": "N/A"
        }


# ============================================================
# RVOL
# ============================================================

def calculate_rvol(
    df,
    lookback=20
):

    try:

        if (
            len(df)
            < lookback + 1
        ):
            return None

        current_volume = float(
            df["Volume"]
            .iloc[-1]
        )

        average_volume = float(
            df["Volume"]
            .iloc[
                -(lookback + 1):-1
            ]
            .mean()
        )

        if average_volume <= 0:
            return None

        return (
            current_volume
            /
            average_volume
        )

    except Exception:

        return None


# ============================================================
# MOVING AVERAGE CONTEXT
# ============================================================

def calculate_ma_context(df):

    result = {

        "MA20": None,
        "MA50": None,
        "MA200": None,

        "Above MA20": False,
        "Above MA50": False,
        "Above MA200": False,

        "Trend": "N/A"
    }

    if (
        df is None
        or
        df.empty
    ):
        return result

    close = (
        df["Close"]
    )

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

        result[
            "MA20"
        ] = ma20

        result[
            "Above MA20"
        ] = (
            price > ma20
        )

    if len(close) >= 50:

        ma50 = float(
            close
            .rolling(50)
            .mean()
            .iloc[-1]
        )

        result[
            "MA50"
        ] = ma50

        result[
            "Above MA50"
        ] = (
            price > ma50
        )

    if len(close) >= 200:

        ma200 = float(
            close
            .rolling(200)
            .mean()
            .iloc[-1]
        )

        result[
            "MA200"
        ] = ma200

        result[
            "Above MA200"
        ] = (
            price > ma200
        )

    if (
        result["MA20"]
        is not None
        and
        result["MA50"]
        is not None
        and
        result["MA200"]
        is not None
    ):

        if (
            price > result["MA20"]
            > result["MA50"]
            > result["MA200"]
        ):

            result[
                "Trend"
            ] = "Strong Uptrend"

        elif (
            price < result["MA20"]
            < result["MA50"]
            < result["MA200"]
        ):

            result[
                "Trend"
            ] = "Strong Downtrend"

        elif (
            price > result["MA50"]
            and
            price > result["MA200"]
        ):

            result[
                "Trend"
            ] = "Bullish"

        elif (
            price < result["MA50"]
            and
            price < result["MA200"]
        ):

            result[
                "Trend"
            ] = "Bearish"

        else:

            result[
                "Trend"
            ] = "Mixed"

    return result


# ============================================================
# RETURN CALCULATION
# ============================================================

def calculate_return(
    df,
    sessions
):

    try:

        if len(df) <= sessions:
            return None

        current = float(
            df["Close"]
            .iloc[-1]
        )

        previous = float(
            df["Close"]
            .iloc[
                -sessions - 1
            ]
        )

        if previous == 0:
            return None

        return (
            (
                current
                /
                previous
            )
            - 1
        ) * 100

    except Exception:

        return None


# ============================================================
# RELATIVE STRENGTH VS SPY
# ============================================================

def calculate_relative_strength(
    asset_df,
    spy_df,
    sessions=20
):

    asset_return = (
        calculate_return(
            asset_df,
            sessions
        )
    )

    spy_return = (
        calculate_return(
            spy_df,
            sessions
        )
    )

    if (
        asset_return is None
        or
        spy_return is None
    ):

        return None

    return (
        asset_return
        -
        spy_return
    )


# ============================================================
# WEEKLY ACTIONABLE SIGNALS
# ============================================================

def find_weekly_actionable_signals(
    df,
    previous_high,
    previous_low
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
        "post_event": None
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

    for (
        date,
        row
    ) in current_data.iterrows():

        o = float(
            row["Open"]
        )

        h = float(
            row["High"]
        )

        l = float(
            row["Low"]
        )

        c = float(
            row["Close"]
        )

        # PWL TAKEN

        if (
            not low_taken
            and
            l < previous_low
        ):

            low_taken = True
            low_taken_date = date

        # PWH TAKEN

        if (
            not high_taken
            and
            h > previous_high
        ):

            high_taken = True
            high_taken_date = date

        # PWL RECLAIM

        if (
            low_taken
            and
            not low_reclaimed
            and
            c > previous_low
        ):

            low_reclaimed = True
            low_reclaim_date = date

        # PWH REJECTION

        if (
            high_taken
            and
            not high_rejected
            and
            c < previous_high
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
                o,
                h,
                l,
                c,
                float(
                    previous_row[
                        "High"
                    ]
                ),
                float(
                    previous_row[
                        "Low"
                    ]
                )
            )
        )

        if actionable is None:
            continue

        # POST CONFIRMATION

        if (
            result[
                "post_signal"
            ]
            is None
        ):

            candidates = []

            if (
                low_reclaimed
                and
                low_reclaim_date
                is not None
                and
                date >= low_reclaim_date
            ):

                candidates.append(
                    (
                        low_reclaim_date,
                        "PWL Taken → Reclaimed"
                    )
                )

            if (
                high_rejected
                and
                high_rejection_date
                is not None
                and
                date >= high_rejection_date
            ):

                candidates.append(
                    (
                        high_rejection_date,
                        "PWH Taken → Rejected"
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda x: x[0]
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

        # PRE CONFIRMATION

        if (
            result[
                "pre_signal"
            ]
            is None
        ):

            candidates = []

            if (
                low_taken
                and
                not low_reclaimed
                and
                low_taken_date
                is not None
            ):

                candidates.append(
                    (
                        low_taken_date,
                        "PWL Taken → Not Yet Reclaimed"
                    )
                )

            if (
                high_taken
                and
                not high_rejected
                and
                high_taken_date
                is not None
            ):

                candidates.append(
                    (
                        high_taken_date,
                        "PWH Taken → Not Yet Rejected"
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda x: x[0]
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

    result[
        "low_taken_date"
    ] = (
        low_taken_date.strftime(
            "%Y-%m-%d"
        )
        if low_taken_date
        is not None
        else None
    )

    result[
        "low_reclaim_date"
    ] = (
        low_reclaim_date.strftime(
            "%Y-%m-%d"
        )
        if low_reclaim_date
        is not None
        else None
    )

    result[
        "high_taken_date"
    ] = (
        high_taken_date.strftime(
            "%Y-%m-%d"
        )
        if high_taken_date
        is not None
        else None
    )

    result[
        "high_rejection_date"
    ] = (
        high_rejection_date.strftime(
            "%Y-%m-%d"
        )
        if high_rejection_date
        is not None
        else None
    )

    return result


# ============================================================
# MONTHLY ACTIONABLE SIGNALS
# ============================================================

def find_monthly_actionable_signals(
    df,
    previous_high,
    previous_low
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
        "post_event": None
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

    # EXACT DAILY EVENT DATES

    for (
        date,
        row
    ) in month_daily.iterrows():

        h = float(
            row["High"]
        )

        l = float(
            row["Low"]
        )

        c = float(
            row["Close"]
        )

        if (
            not low_taken
            and
            l < previous_low
        ):

            low_taken = True
            low_taken_date = date

        if (
            not high_taken
            and
            h > previous_high
        ):

            high_taken = True
            high_taken_date = date

        if (
            low_taken
            and
            not low_reclaimed
            and
            c > previous_low
        ):

            low_reclaimed = True
            low_reclaim_date = date

        if (
            high_taken
            and
            not high_rejected
            and
            c < previous_high
        ):

            high_rejected = True
            high_rejection_date = date

    # WEEKLY CANDLES

    weekly = (
        build_weekly_dataframe(
            df
        )
    )

    weekly_periods = list(
        weekly.index
    )

    monthly_weekly = weekly[
        [
            (
                period
                .start_time
                .to_period("M")
                == current_month
            )
            or
            (
                period
                .end_time
                .to_period("M")
                == current_month
            )
            for period
            in weekly.index
        ]
    ].copy()

    for (
        period,
        row
    ) in monthly_weekly.iterrows():

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
                )
            )
        )

        if actionable is None:
            continue

        week_start = (
            period.start_time
        )

        week_end = (
            period.end_time
        )

        # POST

        if (
            result[
                "post_signal"
            ]
            is None
        ):

            candidates = []

            if (
                low_reclaim_date
                is not None
                and
                week_end
                >= low_reclaim_date
            ):

                candidates.append(
                    (
                        low_reclaim_date,
                        "PML Taken → Reclaimed"
                    )
                )

            if (
                high_rejection_date
                is not None
                and
                week_end
                >= high_rejection_date
            ):

                candidates.append(
                    (
                        high_rejection_date,
                        "PMH Taken → Rejected"
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda x: x[0]
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

        # PRE

        if (
            result[
                "pre_signal"
            ]
            is None
        ):

            candidates = []

            if (
                low_taken_date
                is not None
                and
                week_end >= low_taken_date
                and
                (
                    low_reclaim_date
                    is None
                    or
                    week_start
                    < low_reclaim_date
                )
            ):

                candidates.append(
                    (
                        low_taken_date,
                        "PML Taken → Not Yet Reclaimed"
                    )
                )

            if (
                high_taken_date
                is not None
                and
                week_end >= high_taken_date
                and
                (
                    high_rejection_date
                    is None
                    or
                    week_start
                    < high_rejection_date
                )
            ):

                candidates.append(
                    (
                        high_taken_date,
                        "PMH Taken → Not Yet Rejected"
                    )
                )

            if candidates:

                candidates.sort(
                    key=lambda x: x[0]
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

    result[
        "low_taken_date"
    ] = (
        low_taken_date.strftime(
            "%Y-%m-%d"
        )
        if low_taken_date
        is not None
        else None
    )

    result[
        "low_reclaim_date"
    ] = (
        low_reclaim_date.strftime(
            "%Y-%m-%d"
        )
        if low_reclaim_date
        is not None
        else None
    )

    result[
        "high_taken_date"
    ] = (
        high_taken_date.strftime(
            "%Y-%m-%d"
        )
        if high_taken_date
        is not None
        else None
    )

    result[
        "high_rejection_date"
    ] = (
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
    market_data
):

    rows = []

    bullish_patterns = [
        "2U Green",
        "2D Green",
        "2U Red",
        "1 Inside",
        "3 Outside"
    ]

    bearish_patterns = [
        "2D Red",
        "2U Red",
        "2D Green",
        "1 Inside",
        "3 Outside"
    ]

    tickers = sorted(
        set(tickers)
    )

    total = len(tickers)

    progress = (
        st.progress(0)
    )

    status = (
        st.empty()
    )

    for (
        i,
        ticker
    ) in enumerate(tickers):

        status.text(
            f"Weekly scan: "
            f"{ticker} "
            f"({i + 1}/{total})"
        )

        try:

            df = (
                clean_ticker_dataframe(
                    market_data,
                    ticker
                )
            )

            if (
                df is None
                or
                len(df) < 30
            ):
                continue

            levels = (
                get_weekly_levels(
                    df
                )
            )

            if levels is None:
                continue

            pwh = (
                levels[
                    "previous_high"
                ]
            )

            pwl = (
                levels[
                    "previous_low"
                ]
            )

            price = float(
                df["Close"]
                .iloc[-1]
            )

            low_taken = (
                levels[
                    "current_low"
                ]
                < pwl
            )

            high_taken = (
                levels[
                    "current_high"
                ]
                > pwh
            )

            if not (
                low_taken
                or
                high_taken
            ):
                continue

            low_reclaimed = (
                low_taken
                and
                price > pwl
            )

            high_rejected = (
                high_taken
                and
                price < pwh
            )

            daily_strat = (
                get_daily_strat(
                    df
                )
            )

            ftfc = (
                calculate_ftfc(
                    df
                )
            )

            rvol = (
                calculate_rvol(
                    df
                )
            )

            actionable = (
                find_weekly_actionable_signals(
                    df,
                    pwh,
                    pwl
                )
            )

            bullish = (
                low_reclaimed
                and
                daily_strat
                in bullish_patterns
                and
                ftfc[
                    "weekly"
                ] == "Up"
            )

            bearish = (
                high_rejected
                and
                daily_strat
                in bearish_patterns
                and
                ftfc[
                    "weekly"
                ] == "Down"
            )

            if bullish:

                signal = (
                    f"PWL Taken → Reclaimed → "
                    f"Daily {daily_strat} → "
                    f"Weekly FTFC Up"
                )

            elif bearish:

                signal = (
                    f"PWH Taken → Rejected → "
                    f"Daily {daily_strat} → "
                    f"Weekly FTFC Down"
                )

            elif (
                low_taken
                and
                high_taken
            ):

                signal = (
                    "Both Weekly Levels Taken"
                )

            elif low_reclaimed:

                signal = (
                    "PWL Taken → Reclaimed"
                )

            elif high_rejected:

                signal = (
                    "PWH Taken → Rejected"
                )

            elif low_taken:

                signal = (
                    "Previous Week Low Taken"
                )

            else:

                signal = (
                    "Previous Week High Taken"
                )

            rows.append(
                {

                    "Ticker":
                        ticker,

                    "Asset":
                        get_asset_type(
                            ticker
                        ),

                    "Price":
                        round(price, 2),

                    "Prev Week Low":
                        round(pwl, 2),

                    "Prev Week High":
                        round(pwh, 2),

                    "Prev Week STRAT":
                        levels[
                            "previous_strat"
                        ],

                    "Current Week Low":
                        round(
                            levels[
                                "current_low"
                            ],
                            2
                        ),

                    "Current Week High":
                        round(
                            levels[
                                "current_high"
                            ],
                            2
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
                                2
                            )
                            if rvol
                            is not None
                            else None
                        ),

                    "% From PWL":
                        round(
                            (
                                (
                                    price
                                    - pwl
                                )
                                / pwl
                            )
                            * 100,
                            2
                        ),

                    "% From PWH":
                        round(
                            (
                                (
                                    price
                                    - pwh
                                )
                                / pwh
                            )
                            * 100,
                            2
                        ),

                    "Bullish Setup":
                        bullish,

                    "Bearish Setup":
                        bearish,

                    "Signal":
                        signal
                }
            )

        except Exception:
            pass

        finally:

            if total > 0:

                progress.progress(
                    (i + 1)
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
    market_data
):

    rows = []

    bullish_patterns = [
        "2U Green",
        "2D Green",
        "2U Red",
        "1 Inside",
        "3 Outside"
    ]

    bearish_patterns = [
        "2D Red",
        "2U Red",
        "2D Green",
        "1 Inside",
        "3 Outside"
    ]

    tickers = sorted(
        set(tickers)
    )

    total = len(tickers)

    progress = (
        st.progress(0)
    )

    status = (
        st.empty()
    )

    for (
        i,
        ticker
    ) in enumerate(tickers):

        status.text(
            f"Monthly scan: "
            f"{ticker} "
            f"({i + 1}/{total})"
        )

        try:

            df = (
                clean_ticker_dataframe(
                    market_data,
                    ticker
                )
            )

            if (
                df is None
                or
                len(df) < 60
            ):
                continue

            levels = (
                get_monthly_levels(
                    df
                )
            )

            if levels is None:
                continue

            pmh = (
                levels[
                    "previous_high"
                ]
            )

            pml = (
                levels[
                    "previous_low"
                ]
            )

            price = float(
                df["Close"]
                .iloc[-1]
            )

            low_taken = (
                levels[
                    "current_low"
                ]
                < pml
            )

            high_taken = (
                levels[
                    "current_high"
                ]
                > pmh
            )

            if not (
                low_taken
                or
                high_taken
            ):
                continue

            low_reclaimed = (
                low_taken
                and
                price > pml
            )

            high_rejected = (
                high_taken
                and
                price < pmh
            )

            weekly_strat = (
                get_current_week_strat(
                    df
                )
            )

            ftfc = (
                calculate_ftfc(
                    df
                )
            )

            rvol = (
                calculate_rvol(
                    df
                )
            )

            actionable = (
                find_monthly_actionable_signals(
                    df,
                    pmh,
                    pml
                )
            )

            bullish = (
                low_reclaimed
                and
                weekly_strat
                in bullish_patterns
                and
                ftfc[
                    "monthly"
                ] == "Up"
            )

            bearish = (
                high_rejected
                and
                weekly_strat
                in bearish_patterns
                and
                ftfc[
                    "monthly"
                ] == "Down"
            )

            if bullish:

                signal = (
                    f"PML Taken → Reclaimed → "
                    f"Weekly {weekly_strat} → "
                    f"Monthly FTFC Up"
                )

            elif bearish:

                signal = (
                    f"PMH Taken → Rejected → "
                    f"Weekly {weekly_strat} → "
                    f"Monthly FTFC Down"
                )

            elif (
                low_taken
                and
                high_taken
            ):

                signal = (
                    "Both Monthly Levels Taken"
                )

            elif low_reclaimed:

                signal = (
                    "PML Taken → Reclaimed"
                )

            elif high_rejected:

                signal = (
                    "PMH Taken → Rejected"
                )

            elif low_taken:

                signal = (
                    "Previous Month Low Taken"
                )

            else:

                signal = (
                    "Previous Month High Taken"
                )

            rows.append(
                {

                    "Ticker":
                        ticker,

                    "Asset":
                        get_asset_type(
                            ticker
                        ),

                    "Price":
                        round(price, 2),

                    "Prev Month Low":
                        round(pml, 2),

                    "Prev Month High":
                        round(pmh, 2),

                    "Prev Month STRAT":
                        levels[
                            "previous_strat"
                        ],

                    "Current Month Low":
                        round(
                            levels[
                                "current_low"
                            ],
                            2
                        ),

                    "Current Month High":
                        round(
                            levels[
                                "current_high"
                            ],
                            2
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
                                2
                            )
                            if rvol
                            is not None
                            else None
                        ),

                    "% From PML":
                        round(
                            (
                                (
                                    price
                                    - pml
                                )
                                / pml
                            )
                            * 100,
                            2
                        ),

                    "% From PMH":
                        round(
                            (
                                (
                                    price
                                    - pmh
                                )
                                / pmh
                            )
                            * 100,
                            2
                        ),

                    "Bullish Setup":
                        bullish,

                    "Bearish Setup":
                        bearish,

                    "Signal":
                        signal
                }
            )

        except Exception:
            pass

        finally:

            if total > 0:

                progress.progress(
                    (i + 1)
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
    market_data
):

    rows = []

    spy_df = (
        clean_ticker_dataframe(
            market_data,
            "SPY"
        )
    )

    for ticker in (
        MARKET_CONTEXT_TICKERS
    ):

        try:

            df = (
                clean_ticker_dataframe(
                    market_data,
                    ticker
                )
            )

            if (
                df is None
                or
                len(df) < 30
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

            weekly = (
                get_weekly_levels(
                    df
                )
            )

            monthly = (
                get_monthly_levels(
                    df
                )
            )

            ftfc = (
                calculate_ftfc(
                    df
                )
            )

            ma = (
                calculate_ma_context(
                    df
                )
            )

            rvol = (
                calculate_rvol(
                    df
                )
            )

            return_5d = (
                calculate_return(
                    df,
                    5
                )
            )

            return_20d = (
                calculate_return(
                    df,
                    20
                )
            )

            rs20 = None

            if (
                ticker not in [
                    "SPY",
                    "^VIX"
                ]
                and
                spy_df is not None
            ):

                rs20 = (
                    calculate_relative_strength(
                        df,
                        spy_df,
                        20
                    )
                )

            # WEEKLY LEVELS

            if weekly:

                pwl = (
                    weekly[
                        "previous_low"
                    ]
                )

                pwh = (
                    weekly[
                        "previous_high"
                    ]
                )

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
                        price - pwl
                    )
                    / pwl
                ) * 100

                pct_pwh = (
                    (
                        price - pwh
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

            # MONTHLY LEVELS

            if monthly:

                pml = (
                    monthly[
                        "previous_low"
                    ]
                )

                pmh = (
                    monthly[
                        "previous_high"
                    ]
                )

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
                        price - pml
                    )
                    / pml
                ) * 100

                pct_pmh = (
                    (
                        price - pmh
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

            # CONTEXT

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

                context = (
                    "Bullish"
                )

            elif points <= -4:

                context = (
                    "Strong Bearish"
                )

            elif points <= -2:

                context = (
                    "Bearish"
                )

            else:

                context = (
                    "Mixed"
                )

            if ticker == "^VIX":

                context = (
                    "Volatility"
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
                            price,
                            2
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
                                2
                            )
                            if return_5d
                            is not None
                            else None
                        ),

                    "20D Return %":
                        (
                            round(
                                return_20d,
                                2
                            )
                            if return_20d
                            is not None
                            else None
                        ),

                    "20D RS vs SPY":
                        (
                            round(
                                rs20,
                                2
                            )
                            if rs20
                            is not None
                            else None
                        ),

                    "RVOL":
                        (
                            round(
                                rvol,
                                2
                            )
                            if rvol
                            is not None
                            else None
                        ),

                    "Prev Week Low":
                        (
                            round(
                                pwl,
                                2
                            )
                            if pwl
                            is not None
                            else None
                        ),

                    "Prev Week High":
                        (
                            round(
                                pwh,
                                2
                            )
                            if pwh
                            is not None
                            else None
                        ),

                    "% From PWL":
                        (
                            round(
                                pct_pwl,
                                2
                            )
                            if pct_pwl
                            is not None
                            else None
                        ),

                    "% From PWH":
                        (
                            round(
                                pct_pwh,
                                2
                            )
                            if pct_pwh
                            is not None
                            else None
                        ),

                    "Prev Month Low":
                        (
                            round(
                                pml,
                                2
                            )
                            if pml
                            is not None
                            else None
                        ),

                    "Prev Month High":
                        (
                            round(
                                pmh,
                                2
                            )
                            if pmh
                            is not None
                            else None
                        ),

                    "% From PML":
                        (
                            round(
                                pct_pml,
                                2
                            )
                            if pct_pml
                            is not None
                            else None
                        ),

                    "% From PMH":
                        (
                            round(
                                pct_pmh,
                                2
                            )
                            if pct_pmh
                            is not None
                            else None
                        )
                }
            )

        except Exception:
            continue

    return pd.DataFrame(
        rows
    )


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


# ============================================================
# COMBINED SCANNER UNIVERSE
# ============================================================

combined_tickers = sorted(
    set(
        sp500_tickers
        +
        nasdaq100_tickers
        +
        etf_tickers
    )
)


duplicate_count = (
    len(sp500_tickers)
    +
    len(nasdaq100_tickers)
    +
    len(etf_tickers)
    -
    len(combined_tickers)
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
            "Custom Watchlist"
        ]
    )
)


if (
    universe
    == "S&P 500 + Nasdaq-100 + ETFs"
):

    selected_tickers = (
        combined_tickers
    )

elif (
    universe
    == "S&P 500"
):

    selected_tickers = (
        sp500_tickers
    )

elif (
    universe
    == "Nasdaq-100"
):

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
            )
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

s1, s2 = (
    st.sidebar.columns(2)
)

s1.metric(
    "S&P 500",
    len(
        sp500_tickers
    )
)

s2.metric(
    "Nasdaq-100",
    len(
        nasdaq100_tickers
    )
)

s3, s4 = (
    st.sidebar.columns(2)
)

s3.metric(
    "ETFs",
    len(
        etf_tickers
    )
)

s4.metric(
    "Duplicates",
    duplicate_count
)

st.sidebar.metric(
    "Scanner Universe",
    len(
        selected_tickers
    )
)


with st.sidebar.expander(
    "📈 ETFs Included"
):

    st.write(
        "**Broad Market**"
    )

    st.write(
        "SPY · QQQ · IWM"
    )

    st.write(
        "**Sector ETFs**"
    )

    st.write(
        "XLC · XLY · XLP · XLE · "
        "XLF · XLV · XLI · XLB · "
        "XLRE · XLK · XLU"
    )

    st.write(
        "**Market Context Only**"
    )

    st.write(
        "^VIX"
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
    "weekly_results"
    not in st.session_state
):

    st.session_state[
        "weekly_results"
    ] = None


if (
    "monthly_results"
    not in st.session_state
):

    st.session_state[
        "monthly_results"
    ] = None


# ============================================================
# LOAD MARKET DATA
# ============================================================

load_market = (
    st.sidebar.button(
        "📥 Load Market Data",
        type="primary",
        use_container_width=True
    )
)


if load_market:

    # Always include context assets in download,
    # regardless of scanner universe.

    download_tickers = sorted(
        set(
            selected_tickers
            +
            MARKET_CONTEXT_TICKERS
        )
    )

    with st.spinner(
        f"Downloading 1 year of data "
        f"for {len(download_tickers)} "
        f"unique symbols..."
    ):

        st.session_state[
            "market_data"
        ] = (
            download_market_data(
                download_tickers
            )
        )

        st.session_state[
            "loaded_universe"
        ] = (
            tuple(
                selected_tickers
            )
        )

        # Reset scanner results when
        # changing universe.

        st.session_state[
            "weekly_results"
        ] = None

        st.session_state[
            "monthly_results"
        ] = None


# ============================================================
# MARKET READY
# ============================================================

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
        "Select your universe and click "
        "**Load Market Data**."
    )

else:

    st.success(
        f"Market data loaded for "
        f"{len(st.session_state['market_data'])} "
        f"symbols."
    )


# ============================================================
# TABS
# ============================================================

(
    weekly_tab,
    monthly_tab,
    market_context_tab
) = st.tabs(
    [
        "📅 Weekly Scanner",
        "🗓️ Monthly Scanner",
        "🌎 Market Context"
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

    # FILTERS

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
                "Bearish Setup"
            ],
            key="weekly_signal_filter"
        )
    )

    weekly_strat_filter = (
        w2.selectbox(
            "Current Week STRAT",
            [
                "All",
                "1 Inside",
                "2U Green",
                "2U Red",
                "2D Green",
                "2D Red",
                "3 Outside"
            ],
            key="weekly_strat_filter"
        )
    )

    daily_filter = (
        w3.selectbox(
            "Daily STRAT",
            [
                "All",
                "1 Inside",
                "2U Green",
                "2U Red",
                "2D Green",
                "2D Red",
                "3 Outside"
            ],
            key="daily_filter"
        )
    )

    weekly_actionable_filter = (
        w4.selectbox(
            "Actionable Candle",
            [
                "All",
                "Hammer",
                "Shooting Star",
                "Inside Bar"
            ],
            key="weekly_actionable_filter"
        )
    )

    w5, w6 = (
        st.columns(2)
    )

    weekly_category = (
        w5.selectbox(
            "Actionable Category",
            [
                "All",
                "Pre-Confirmation",
                "Post-Confirmation"
            ],
            key="weekly_category"
        )
    )

    weekly_min_rvol = (
        w6.number_input(
            "Minimum RVOL",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.1,
            key="weekly_rvol"
        )
    )

    run_weekly = (
        st.button(
            "🚀 Run Weekly Scanner",
            type="primary",
            use_container_width=True,
            key="run_weekly"
        )
    )

    if run_weekly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            st.session_state[
                "weekly_results"
            ] = (
                scan_weekly(
                    selected_tickers,
                    st.session_state[
                        "market_data"
                    ]
                )
            )

    # ========================================================
    # DISPLAY SAVED WEEKLY RESULTS
    # ========================================================

    if (
        st.session_state[
            "weekly_results"
        ]
        is not None
    ):

        weekly_results = (
            st.session_state[
                "weekly_results"
            ]
            .copy()
        )

        if not weekly_results.empty:

            # SIGNAL FILTER

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

            # WEEKLY STRAT

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

            # DAILY STRAT

            if (
                daily_filter
                != "All"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "Daily STRAT"
                        ]
                        == daily_filter
                    ]
                )

            # ACTIONABLE

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

            elif (
                weekly_category
                == "Pre-Confirmation"
            ):

                weekly_results = (
                    weekly_results[
                        weekly_results[
                            "First Pre-Confirmation Signal"
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
                            "First Post-Confirmation Signal"
                        ]
                        .notna()
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

        if weekly_results.empty:

            st.warning(
                "No weekly signals matched."
            )

        else:

            weekly_results = (
                weekly_results
                .sort_values(
                    [
                        "Bullish Setup",
                        "Bearish Setup",
                        "RVOL"
                    ],
                    ascending=[
                        False,
                        False,
                        False
                    ],
                    na_position="last"
                )
            )

            # METRICS

            c1, c2, c3, c4, c5 = (
                st.columns(5)
            )

            c1.metric(
                "Matches",
                len(
                    weekly_results
                )
            )

            c2.metric(
                "PWL Taken",
                int(
                    weekly_results[
                        "Low Taken"
                    ].sum()
                )
            )

            c3.metric(
                "PWH Taken",
                int(
                    weekly_results[
                        "High Taken"
                    ].sum()
                )
            )

            c4.metric(
                "Bullish",
                int(
                    weekly_results[
                        "Bullish Setup"
                    ].sum()
                )
            )

            c5.metric(
                "Bearish",
                int(
                    weekly_results[
                        "Bearish Setup"
                    ].sum()
                )
            )

            # 1 RESULTS

            st.subheader(
                "🔎 Weekly Scanner Results"
            )

            st.dataframe(
                weekly_results,
                use_container_width=True,
                hide_index=True
            )

            # 2 POST CONFIRMATION

            weekly_post = (
                weekly_results[
                    weekly_results[
                        "First Post-Confirmation Signal"
                    ]
                    .notna()
                ]
            )

            if not weekly_post.empty:

                st.subheader(
                    "✅ Weekly Post-Confirmation Signals"
                )

                st.dataframe(
                    weekly_post[
                        [
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
                            "RVOL",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            # 3 PRE CONFIRMATION

            weekly_pre = (
                weekly_results[
                    weekly_results[
                        "First Pre-Confirmation Signal"
                    ]
                    .notna()
                ]
            )

            if not weekly_pre.empty:

                st.subheader(
                    "⚠️ Weekly Pre-Confirmation Signals"
                )

                st.dataframe(
                    weekly_pre[
                        [
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
                            "RVOL",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            # 4 BULLISH

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

                st.caption(
                    "PWL Taken → Reclaimed → "
                    "Daily STRAT → Weekly FTFC Up"
                )

                st.dataframe(
                    weekly_bullish[
                        [
                            "Ticker",
                            "Asset",
                            "Price",
                            "Prev Week Low",
                            "Low Sweep Date",
                            "Low Reclaim Date",
                            "Current Week STRAT",
                            "Daily STRAT",
                            "First Post-Confirmation Signal",
                            "Post-Confirmation Date",
                            "Weekly FTFC",
                            "Monthly FTFC",
                            "RVOL",
                            "% From PWL",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            # 5 BEARISH

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

                st.caption(
                    "PWH Taken → Rejected → "
                    "Daily STRAT → Weekly FTFC Down"
                )

                st.dataframe(
                    weekly_bearish[
                        [
                            "Ticker",
                            "Asset",
                            "Price",
                            "Prev Week High",
                            "High Sweep Date",
                            "High Rejection Date",
                            "Current Week STRAT",
                            "Daily STRAT",
                            "First Post-Confirmation Signal",
                            "Post-Confirmation Date",
                            "Weekly FTFC",
                            "Monthly FTFC",
                            "RVOL",
                            "% From PWH",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            weekly_csv = (
                weekly_results
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8"
                )
            )

            st.download_button(
                "⬇️ Download Weekly Results",
                data=weekly_csv,
                file_name=(
                    "weekly_strat_scanner.csv"
                ),
                mime="text/csv",
                use_container_width=True
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
                "Bearish Setup"
            ],
            key="monthly_signal_filter"
        )
    )

    month_strat_filter = (
        m2.selectbox(
            "Current Month STRAT",
            [
                "All",
                "1 Inside",
                "2U Green",
                "2U Red",
                "2D Green",
                "2D Red",
                "3 Outside"
            ],
            key="month_strat_filter"
        )
    )

    month_weekly_filter = (
        m3.selectbox(
            "Current Week STRAT",
            [
                "All",
                "1 Inside",
                "2U Green",
                "2U Red",
                "2D Green",
                "2D Red",
                "3 Outside"
            ],
            key="month_weekly_filter"
        )
    )

    monthly_actionable_filter = (
        m4.selectbox(
            "Weekly Actionable Signal",
            [
                "All",
                "Hammer",
                "Shooting Star",
                "Inside Bar"
            ],
            key="monthly_actionable"
        )
    )

    m5, m6 = (
        st.columns(2)
    )

    monthly_category = (
        m5.selectbox(
            "Actionable Category",
            [
                "All",
                "Pre-Confirmation",
                "Post-Confirmation"
            ],
            key="monthly_category"
        )
    )

    monthly_min_rvol = (
        m6.number_input(
            "Minimum RVOL",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.1,
            key="monthly_rvol"
        )
    )

    run_monthly = (
        st.button(
            "🚀 Run Monthly Scanner",
            type="primary",
            use_container_width=True,
            key="run_monthly"
        )
    )

    if run_monthly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            st.session_state[
                "monthly_results"
            ] = (
                scan_monthly(
                    selected_tickers,
                    st.session_state[
                        "market_data"
                    ]
                )
            )

    # ========================================================
    # DISPLAY MONTHLY RESULTS
    # ========================================================

    if (
        st.session_state[
            "monthly_results"
        ]
        is not None
    ):

        monthly_results = (
            st.session_state[
                "monthly_results"
            ]
            .copy()
        )

        if not monthly_results.empty:

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
                                "First Pre-Confirmation Weekly Signal"
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
                                "First Post-Confirmation Weekly Signal"
                            ]
                            == monthly_actionable_filter
                        ]
                    )

                else:

                    monthly_results = (
                        monthly_results[
                            (
                                monthly_results[
                                    "First Pre-Confirmation Weekly Signal"
                                ]
                                == monthly_actionable_filter
                            )
                            |
                            (
                                monthly_results[
                                    "First Post-Confirmation Weekly Signal"
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
                            "First Pre-Confirmation Weekly Signal"
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
                            "First Post-Confirmation Weekly Signal"
                        ]
                        .notna()
                    ]
                )

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

        if monthly_results.empty:

            st.warning(
                "No monthly signals matched."
            )

        else:

            monthly_results = (
                monthly_results
                .sort_values(
                    [
                        "Bullish Setup",
                        "Bearish Setup",
                        "RVOL"
                    ],
                    ascending=[
                        False,
                        False,
                        False
                    ],
                    na_position="last"
                )
            )

            c1, c2, c3, c4, c5 = (
                st.columns(5)
            )

            c1.metric(
                "Matches",
                len(
                    monthly_results
                )
            )

            c2.metric(
                "PML Taken",
                int(
                    monthly_results[
                        "Low Taken"
                    ].sum()
                )
            )

            c3.metric(
                "PMH Taken",
                int(
                    monthly_results[
                        "High Taken"
                    ].sum()
                )
            )

            c4.metric(
                "Bullish",
                int(
                    monthly_results[
                        "Bullish Setup"
                    ].sum()
                )
            )

            c5.metric(
                "Bearish",
                int(
                    monthly_results[
                        "Bearish Setup"
                    ].sum()
                )
            )

            # 1 RESULTS

            st.subheader(
                "🔎 Monthly Scanner Results"
            )

            st.dataframe(
                monthly_results,
                use_container_width=True,
                hide_index=True
            )

            # 2 POST

            monthly_post = (
                monthly_results[
                    monthly_results[
                        "First Post-Confirmation Weekly Signal"
                    ]
                    .notna()
                ]
            )

            if not monthly_post.empty:

                st.subheader(
                    "✅ Monthly Post-Confirmation Signals"
                )

                st.dataframe(
                    monthly_post[
                        [
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
                            "RVOL",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            # 3 PRE

            monthly_pre = (
                monthly_results[
                    monthly_results[
                        "First Pre-Confirmation Weekly Signal"
                    ]
                    .notna()
                ]
            )

            if not monthly_pre.empty:

                st.subheader(
                    "⚠️ Monthly Pre-Confirmation Signals"
                )

                st.dataframe(
                    monthly_pre[
                        [
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
                            "RVOL",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            # 4 BULLISH

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

                st.caption(
                    "PML Taken → Reclaimed → "
                    "Weekly STRAT → Monthly FTFC Up"
                )

                st.dataframe(
                    monthly_bullish[
                        [
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
                            "RVOL",
                            "% From PML",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            # 5 BEARISH

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

                st.caption(
                    "PMH Taken → Rejected → "
                    "Weekly STRAT → Monthly FTFC Down"
                )

                st.dataframe(
                    monthly_bearish[
                        [
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
                            "RVOL",
                            "% From PMH",
                            "Signal"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            monthly_csv = (
                monthly_results
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8"
                )
            )

            st.download_button(
                "⬇️ Download Monthly Results",
                data=monthly_csv,
                file_name=(
                    "monthly_strat_scanner.csv"
                ),
                mime="text/csv",
                use_container_width=True
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
                "No market context data available."
            )

        else:

            # =================================================
            # INDEX SNAPSHOT
            # =================================================

            st.subheader(
                "🧭 Index Snapshot"
            )

            i1, i2, i3, i4 = (
                st.columns(4)
            )

            index_cards = [
                ("SPY", i1),
                ("QQQ", i2),
                ("IWM", i3),
                ("^VIX", i4)
            ]

            for (
                ticker,
                column
            ) in index_cards:

                row = (
                    context_df[
                        context_df[
                            "Ticker"
                        ]
                        == ticker
                    ]
                )

                if not row.empty:

                    row = (
                        row.iloc[0]
                    )

                    return5 = (
                        row[
                            "5D Return %"
                        ]
                    )

                    delta = (
                        f"{return5:.2f}% 5D"
                        if pd.notna(
                            return5
                        )
                        else None
                    )

                    column.metric(
                        ticker.replace(
                            "^",
                            ""
                        ),
                        f'{row["Price"]:.2f}',
                        delta
                    )

                    column.caption(
                        f'{row["Context"]} | '
                        f'W: {row["Weekly FTFC"]} | '
                        f'M: {row["Monthly FTFC"]}'
                    )

            # =================================================
            # MAJOR MARKET CONTEXT
            # =================================================

            st.subheader(
                "📊 Major Market Context"
            )

            major = (
                context_df[
                    context_df[
                        "Ticker"
                    ].isin(
                        [
                            "SPY",
                            "QQQ",
                            "IWM",
                            "^VIX"
                        ]
                    )
                ]
            )

            st.dataframe(
                major[
                    [
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
                        "RVOL"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            # =================================================
            # SECTORS
            # =================================================

            st.subheader(
                "🏭 Sector ETF Context"
            )

            sector_tickers = [
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
                "XLU"
            ]

            sectors = (
                context_df[
                    context_df[
                        "Ticker"
                    ].isin(
                        sector_tickers
                    )
                ]
                .copy()
            )

            sectors = (
                sectors.sort_values(
                    "20D RS vs SPY",
                    ascending=False,
                    na_position="last"
                )
            )

            st.dataframe(
                sectors[
                    [
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
                        "RVOL"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            # =================================================
            # SECTOR RELATIVE STRENGTH
            # =================================================

            st.subheader(
                "🚀 Sector Relative Strength vs SPY"
            )

            st.caption(
                "20D RS vs SPY = sector 20-session "
                "return minus SPY's 20-session return. "
                "Positive values indicate relative "
                "outperformance; negative values indicate "
                "relative underperformance."
            )

            sector_rs = (
                sectors[
                    [
                        "Ticker",
                        "Market",
                        "5D Return %",
                        "20D Return %",
                        "20D RS vs SPY",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "Current Week STRAT",
                        "Current Month STRAT"
                    ]
                ]
                .sort_values(
                    "20D RS vs SPY",
                    ascending=False,
                    na_position="last"
                )
            )

            st.dataframe(
                sector_rs,
                use_container_width=True,
                hide_index=True
            )

            # =================================================
            # MARKET BREADTH
            # =================================================

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
                f"{above20}/{total_assets}"
            )

            b2.metric(
                "Above 50D MA",
                f"{above50}/{total_assets}"
            )

            b3.metric(
                "Above 200D MA",
                f"{above200}/{total_assets}"
            )

            # =================================================
            # PREVIOUS WEEK LEVELS
            # =================================================

            st.subheader(
                "📅 Previous Week Levels"
            )

            st.dataframe(
                context_df[
                    [
                        "Ticker",
                        "Market",
                        "Price",
                        "Prev Week Low",
                        "% From PWL",
                        "Prev Week High",
                        "% From PWH",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "Weekly FTFC"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            # =================================================
            # PREVIOUS MONTH LEVELS
            # =================================================

            st.subheader(
                "🗓️ Previous Month Levels"
            )

            st.dataframe(
                context_df[
                    [
                        "Ticker",
                        "Market",
                        "Price",
                        "Prev Month Low",
                        "% From PML",
                        "Prev Month High",
                        "% From PMH",
                        "Prev Month STRAT",
                        "Current Month STRAT",
                        "Monthly FTFC"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            # =================================================
            # DOWNLOAD
            # =================================================

            context_csv = (
                context_df
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8"
                )
            )

            st.download_button(
                "⬇️ Download Market Context",
                data=context_csv,
                file_name=(
                    "market_context.csv"
                ),
                mime="text/csv",
                use_container_width=True
            )
