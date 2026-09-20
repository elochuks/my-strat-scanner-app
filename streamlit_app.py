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
    "Weekly and Monthly scanners for previous-period liquidity "
    "sweeps, reclaim/rejection, STRAT patterns, actionable "
    "candles, FTFC and relative volume."
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
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_nasdaq100_tickers():

    # Self-contained list prevents Wikipedia 403 errors.

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
        ticker.strip()
        .upper()
        .replace(".", "-")
        for ticker in tickers
        if ticker.strip()
    ]

    return sorted(set(tickers))


# ============================================================
# MARKET DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    results = {}

    tickers = sorted(set(tickers))

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
                            results[ticker] = ticker_df

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
                    results[ticker] = ticker_df

        except Exception:
            continue

        time.sleep(0.20)

    return results


# ============================================================
# CLEAN TICKER DATA
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
            col in df.columns
            for col in required
        ):
            return None

        df = df[required].copy()

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

        df.index = pd.to_datetime(
            df.index
        )

        try:
            df.index = df.index.tz_localize(None)
        except Exception:
            pass

        return df.sort_index()

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

    # 3 OUTSIDE

    if (
        current_high > previous_high
        and
        current_low < previous_low
    ):
        return "3 Outside"

    # 1 INSIDE

    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):
        return "1 Inside"

    # 2 UP

    if current_high > previous_high:

        if current_close >= current_open:
            return "2U Green"

        return "2U Red"

    # 2 DOWN

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
        current_high - current_low
    )

    if candle_range <= 0:
        return None

    body = abs(
        current_close - current_open
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

    hammer = (
        lower_wick >= 2 * body_for_ratio
        and
        upper_wick <= body_for_ratio
        and
        body <= candle_range * 0.40
    )

    if hammer:
        return "Hammer"

    # SHOOTING STAR

    shooting_star = (
        upper_wick >= 2 * body_for_ratio
        and
        lower_wick <= body_for_ratio
        and
        body <= candle_range * 0.40
    )

    if shooting_star:
        return "Shooting Star"

    return None


# ============================================================
# DAILY STRAT
# ============================================================

def get_daily_strat(df):

    if df is None or len(df) < 2:
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
# BUILD WEEKLY DATAFRAME
# ============================================================

def build_weekly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index.to_period("W-FRI")
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
# BUILD MONTHLY DATAFRAME
# ============================================================

def build_monthly_dataframe(df):

    temp = df.copy()

    temp["Period"] = (
        temp.index.to_period("M")
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

    weekly = build_weekly_dataframe(df)

    if len(weekly) < 3:
        return None

    current_period = (
        df.index[-1]
        .to_period("W-FRI")
    )

    if current_period not in weekly.index:
        return None

    completed = weekly[
        weekly.index < current_period
    ]

    if len(completed) < 2:
        return None

    current = weekly.loc[
        current_period
    ]

    previous = completed.iloc[-1]

    two_back = completed.iloc[-2]

    previous_strat = classify_strat_candle(
        float(previous["Open"]),
        float(previous["High"]),
        float(previous["Low"]),
        float(previous["Close"]),
        float(two_back["High"]),
        float(two_back["Low"])
    )

    current_strat = classify_strat_candle(
        float(current["Open"]),
        float(current["High"]),
        float(current["Low"]),
        float(current["Close"]),
        float(previous["High"]),
        float(previous["Low"])
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

    monthly = build_monthly_dataframe(df)

    if len(monthly) < 3:
        return None

    current_period = (
        df.index[-1]
        .to_period("M")
    )

    if current_period not in monthly.index:
        return None

    completed = monthly[
        monthly.index < current_period
    ]

    if len(completed) < 2:
        return None

    current = monthly.loc[
        current_period
    ]

    previous = completed.iloc[-1]

    two_back = completed.iloc[-2]

    previous_strat = classify_strat_candle(
        float(previous["Open"]),
        float(previous["High"]),
        float(previous["Low"]),
        float(previous["Close"]),
        float(two_back["High"]),
        float(two_back["Low"])
    )

    current_strat = classify_strat_candle(
        float(current["Open"]),
        float(current["High"]),
        float(current["Low"]),
        float(current["Close"]),
        float(previous["High"]),
        float(previous["Low"])
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

    levels = get_weekly_levels(df)

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
            df["Close"].iloc[-1]
        )

        # WEEKLY

        current_week = (
            df.index[-1]
            .to_period("W-FRI")
        )

        week_data = df[
            df.index.to_period("W-FRI")
            == current_week
        ]

        weekly_open = float(
            week_data["Open"].iloc[0]
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
            df.index.to_period("M")
            == current_month
        ]

        monthly_open = float(
            month_data["Open"].iloc[0]
        )

        if price > monthly_open:
            monthly = "Up"

        elif price < monthly_open:
            monthly = "Down"

        else:
            monthly = "Neutral"

        # ALIGNMENT

        if (
            weekly == "Up"
            and
            monthly == "Up"
        ):

            alignment = "FTFC Up"

        elif (
            weekly == "Down"
            and
            monthly == "Down"
        ):

            alignment = "FTFC Down"

        else:

            alignment = "Mixed"

        return {
            "weekly": weekly,
            "monthly": monthly,
            "alignment": alignment
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

        if len(df) < lookback + 1:
            return None

        current_volume = float(
            df["Volume"].iloc[-1]
        )

        average_volume = float(
            df["Volume"]
            .iloc[-(lookback + 1):-1]
            .mean()
        )

        if average_volume <= 0:
            return None

        return (
            current_volume
            / average_volume
        )

    except Exception:

        return None


# ============================================================
# WEEKLY ACTIONABLE SIGNALS
#
# WEEKLY LEVEL -> DAILY ACTIONABLE CANDLE
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
        df.index.to_period("W-FRI")
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

    for date, row in current_data.iterrows():

        o = float(row["Open"])
        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])

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

        location = df.index.get_loc(date)

        if location == 0:
            continue

        previous_row = df.iloc[
            location - 1
        ]

        actionable = classify_actionable_candle(
            o,
            h,
            l,
            c,
            float(previous_row["High"]),
            float(previous_row["Low"])
        )

        if actionable is None:
            continue

        # ====================================================
        # POST-CONFIRMATION
        # ====================================================

        if result["post_signal"] is None:

            candidates = []

            if (
                low_taken
                and
                low_reclaimed
                and
                low_reclaim_date is not None
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
                high_taken
                and
                high_rejected
                and
                high_rejection_date is not None
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
                ] = date.strftime(
                    "%Y-%m-%d"
                )

                result[
                    "post_event"
                ] = candidates[0][1]

        # ====================================================
        # PRE-CONFIRMATION
        # ====================================================

        if result["pre_signal"] is None:

            candidates = []

            if (
                low_taken
                and
                not low_reclaimed
                and
                low_taken_date is not None
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
                high_taken_date is not None
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
                ] = date.strftime(
                    "%Y-%m-%d"
                )

                result[
                    "pre_event"
                ] = candidates[0][1]

    # DATES

    result["low_taken_date"] = (
        low_taken_date.strftime("%Y-%m-%d")
        if low_taken_date is not None
        else None
    )

    result["low_reclaim_date"] = (
        low_reclaim_date.strftime("%Y-%m-%d")
        if low_reclaim_date is not None
        else None
    )

    result["high_taken_date"] = (
        high_taken_date.strftime("%Y-%m-%d")
        if high_taken_date is not None
        else None
    )

    result["high_rejection_date"] = (
        high_rejection_date.strftime("%Y-%m-%d")
        if high_rejection_date is not None
        else None
    )

    return result


# ============================================================
# MONTHLY ACTIONABLE SIGNALS
#
# MONTHLY LEVEL -> WEEKLY ACTIONABLE CANDLE
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
        df.index.to_period("M")
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

    # ========================================================
    # FIND EXACT DAILY SWEEP / CONFIRMATION DATES
    # ========================================================

    for date, row in month_daily.iterrows():

        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])

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

    # ========================================================
    # WEEKLY CANDLES
    # ========================================================

    weekly = build_weekly_dataframe(df)

    weekly_periods = list(
        weekly.index
    )

    # Use weekly candles that overlap current month.

    monthly_weekly = weekly[
        [
            (
                period.start_time.to_period("M")
                == current_month
            )
            or
            (
                period.end_time.to_period("M")
                == current_month
            )
            for period in weekly.index
        ]
    ].copy()

    # ========================================================
    # FIND WEEKLY ACTIONABLE CANDLES
    # ========================================================

    for period, row in monthly_weekly.iterrows():

        try:

            location = weekly_periods.index(
                period
            )

        except ValueError:

            continue

        if location == 0:
            continue

        previous_row = weekly.iloc[
            location - 1
        ]

        actionable = classify_actionable_candle(
            float(row["Open"]),
            float(row["High"]),
            float(row["Low"]),
            float(row["Close"]),
            float(previous_row["High"]),
            float(previous_row["Low"])
        )

        if actionable is None:
            continue

        week_start = period.start_time

        week_end = period.end_time

        # ====================================================
        # POST-CONFIRMATION
        # ====================================================

        if result["post_signal"] is None:

            candidates = []

            if (
                low_reclaim_date is not None
                and
                week_end >= low_reclaim_date
            ):

                candidates.append(
                    (
                        low_reclaim_date,
                        "PML Taken → Reclaimed"
                    )
                )

            if (
                high_rejection_date is not None
                and
                week_end >= high_rejection_date
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
                ] = week_end.strftime(
                    "%Y-%m-%d"
                )

                result[
                    "post_event"
                ] = candidates[0][1]

        # ====================================================
        # PRE-CONFIRMATION
        # ====================================================

        if result["pre_signal"] is None:

            candidates = []

            if (
                low_taken_date is not None
                and
                week_end >= low_taken_date
                and
                (
                    low_reclaim_date is None
                    or
                    week_start < low_reclaim_date
                )
            ):

                candidates.append(
                    (
                        low_taken_date,
                        "PML Taken → Not Yet Reclaimed"
                    )
                )

            if (
                high_taken_date is not None
                and
                week_end >= high_taken_date
                and
                (
                    high_rejection_date is None
                    or
                    week_start < high_rejection_date
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
                ] = week_end.strftime(
                    "%Y-%m-%d"
                )

                result[
                    "pre_event"
                ] = candidates[0][1]

    # ========================================================
    # RETURN DATES
    # ========================================================

    result["low_taken_date"] = (
        low_taken_date.strftime("%Y-%m-%d")
        if low_taken_date is not None
        else None
    )

    result["low_reclaim_date"] = (
        low_reclaim_date.strftime("%Y-%m-%d")
        if low_reclaim_date is not None
        else None
    )

    result["high_taken_date"] = (
        high_taken_date.strftime("%Y-%m-%d")
        if high_taken_date is not None
        else None
    )

    result["high_rejection_date"] = (
        high_rejection_date.strftime("%Y-%m-%d")
        if high_rejection_date is not None
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

    tickers = sorted(set(tickers))

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

    progress = st.progress(0)

    status = st.empty()

    total = len(tickers)

    for i, ticker in enumerate(tickers):

        status.text(
            f"Weekly scan: {ticker} "
            f"({i + 1}/{total})"
        )

        try:

            df = clean_ticker_dataframe(
                market_data,
                ticker
            )

            if (
                df is None
                or
                len(df) < 30
            ):
                continue

            levels = get_weekly_levels(df)

            if levels is None:
                continue

            pwh = levels[
                "previous_high"
            ]

            pwl = levels[
                "previous_low"
            ]

            current_price = float(
                df["Close"].iloc[-1]
            )

            # =================================================
            # WEEKLY SWEEP
            # =================================================

            low_taken = (
                levels["current_low"]
                < pwl
            )

            high_taken = (
                levels["current_high"]
                > pwh
            )

            # Only weekly sweeps enter scanner.

            if not (
                low_taken
                or
                high_taken
            ):
                continue

            low_reclaimed = (
                low_taken
                and
                current_price > pwl
            )

            high_rejected = (
                high_taken
                and
                current_price < pwh
            )

            # =================================================
            # STRAT / FTFC / RVOL
            # =================================================

            daily_strat = (
                get_daily_strat(df)
            )

            ftfc = calculate_ftfc(df)

            rvol = calculate_rvol(df)

            actionable = (
                find_weekly_actionable_signals(
                    df,
                    pwh,
                    pwl
                )
            )

            # =================================================
            # SETUPS
            # =================================================

            bullish = (
                low_reclaimed
                and
                daily_strat in bullish_patterns
                and
                ftfc["weekly"] == "Up"
            )

            bearish = (
                high_rejected
                and
                daily_strat in bearish_patterns
                and
                ftfc["weekly"] == "Down"
            )

            # =================================================
            # SIGNAL
            # =================================================

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

            # =================================================
            # RESULT
            # =================================================

            rows.append({

                "Ticker":
                    ticker,

                "Price":
                    round(
                        current_price,
                        2
                    ),

                "Prev Week Low":
                    round(
                        pwl,
                        2
                    ),

                "Prev Week High":
                    round(
                        pwh,
                        2
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
                    ftfc["weekly"],

                "Monthly FTFC":
                    ftfc["monthly"],

                "FTFC":
                    ftfc["alignment"],

                "RVOL":
                    (
                        round(rvol, 2)
                        if rvol is not None
                        else None
                    ),

                "% From PWL":
                    round(
                        (
                            (
                                current_price
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
                                current_price
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
            })

        except Exception:
            pass

        finally:

            progress.progress(
                (i + 1) / total
            )

    progress.empty()
    status.empty()

    return pd.DataFrame(rows)


# ============================================================
# MONTHLY SCANNER
# ============================================================

def scan_monthly(
    tickers,
    market_data
):

    rows = []

    tickers = sorted(set(tickers))

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

    progress = st.progress(0)

    status = st.empty()

    total = len(tickers)

    for i, ticker in enumerate(tickers):

        status.text(
            f"Monthly scan: {ticker} "
            f"({i + 1}/{total})"
        )

        try:

            df = clean_ticker_dataframe(
                market_data,
                ticker
            )

            if (
                df is None
                or
                len(df) < 60
            ):
                continue

            levels = get_monthly_levels(df)

            if levels is None:
                continue

            pmh = levels[
                "previous_high"
            ]

            pml = levels[
                "previous_low"
            ]

            current_price = float(
                df["Close"].iloc[-1]
            )

            # =================================================
            # MONTHLY SWEEP
            # =================================================

            low_taken = (
                levels["current_low"]
                < pml
            )

            high_taken = (
                levels["current_high"]
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
                current_price > pml
            )

            high_rejected = (
                high_taken
                and
                current_price < pmh
            )

            # =================================================
            # WEEKLY STRAT
            # =================================================

            weekly_strat = (
                get_current_week_strat(
                    df
                )
            )

            ftfc = calculate_ftfc(df)

            rvol = calculate_rvol(df)

            actionable = (
                find_monthly_actionable_signals(
                    df,
                    pmh,
                    pml
                )
            )

            # =================================================
            # SETUPS
            # =================================================

            bullish = (
                low_reclaimed
                and
                weekly_strat in bullish_patterns
                and
                ftfc["monthly"] == "Up"
            )

            bearish = (
                high_rejected
                and
                weekly_strat in bearish_patterns
                and
                ftfc["monthly"] == "Down"
            )

            # =================================================
            # SIGNAL
            # =================================================

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

            # =================================================
            # RESULT
            # =================================================

            rows.append({

                "Ticker":
                    ticker,

                "Price":
                    round(
                        current_price,
                        2
                    ),

                "Prev Month Low":
                    round(
                        pml,
                        2
                    ),

                "Prev Month High":
                    round(
                        pmh,
                        2
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
                    ftfc["weekly"],

                "Monthly FTFC":
                    ftfc["monthly"],

                "FTFC":
                    ftfc["alignment"],

                "RVOL":
                    (
                        round(rvol, 2)
                        if rvol is not None
                        else None
                    ),

                "% From PML":
                    round(
                        (
                            (
                                current_price
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
                                current_price
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
            })

        except Exception:
            pass

        finally:

            progress.progress(
                (i + 1) / total
            )

    progress.empty()
    status.empty()

    return pd.DataFrame(rows)


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


# ============================================================
# COMBINE + REMOVE DUPLICATES
# ============================================================

combined_tickers = sorted(
    set(
        sp500_tickers
        +
        nasdaq100_tickers
    )
)

duplicate_count = (
    len(sp500_tickers)
    +
    len(nasdaq100_tickers)
    -
    len(combined_tickers)
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Market Settings"
)

universe = st.sidebar.selectbox(
    "Market Universe",
    [
        "S&P 500 + Nasdaq-100",
        "S&P 500",
        "Nasdaq-100",
        "Custom Watchlist"
    ]
)


if (
    universe
    == "S&P 500 + Nasdaq-100"
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

else:

    custom = st.sidebar.text_area(
        "Custom Tickers",
        value=(
            "AAPL,MSFT,NVDA,"
            "AMD,TSLA,AMZN,META"
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
# UNIVERSE STATS
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "Universe Statistics"
)

u1, u2 = st.sidebar.columns(2)

u1.metric(
    "S&P 500",
    len(sp500_tickers)
)

u2.metric(
    "Nasdaq-100",
    len(nasdaq100_tickers)
)

u3, u4 = st.sidebar.columns(2)

u3.metric(
    "Duplicates",
    duplicate_count
)

u4.metric(
    "Unique",
    len(combined_tickers)
)

st.sidebar.metric(
    "Stocks Selected",
    len(selected_tickers)
)


# ============================================================
# SESSION STATE
# ============================================================

if "market_data" not in st.session_state:

    st.session_state.market_data = None


if "loaded_universe" not in st.session_state:

    st.session_state.loaded_universe = None


# ============================================================
# LOAD MARKET DATA
# ============================================================

load_market = st.sidebar.button(
    "📥 Load Market Data",
    type="primary",
    use_container_width=True
)


if load_market:

    with st.spinner(
        f"Downloading 1 year of data for "
        f"{len(selected_tickers)} unique stocks..."
    ):

        st.session_state.market_data = (
            download_market_data(
                selected_tickers
            )
        )

        st.session_state.loaded_universe = (
            tuple(selected_tickers)
        )


# ============================================================
# CHECK MARKET DATA
# ============================================================

market_ready = (
    st.session_state.market_data
    is not None
    and
    st.session_state.loaded_universe
    == tuple(selected_tickers)
)


if not market_ready:

    st.info(
        "Select your universe and click "
        "**Load Market Data**. The same download is "
        "used by both scanner tabs."
    )

else:

    st.success(
        f"Market data loaded for "
        f"{len(st.session_state.market_data)} "
        f"stocks."
    )


# ============================================================
# TABS
# ============================================================

weekly_tab, monthly_tab = st.tabs(
    [
        "📅 Weekly Scanner",
        "🗓️ Monthly Scanner"
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

    # ========================================================
    # FILTERS
    # ========================================================

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

    w5, w6 = st.columns(2)

    weekly_actionable_category = (
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

    # ========================================================
    # RUN
    # ========================================================

    run_weekly = st.button(
        "🚀 Run Weekly Scanner",
        type="primary",
        use_container_width=True,
        key="run_weekly"
    )

    if run_weekly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            weekly_results = (
                scan_weekly(
                    selected_tickers,
                    st.session_state.market_data
                )
            )

            # =================================================
            # FILTER RESULTS
            # =================================================

            if not weekly_results.empty:

                # SIGNAL

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

                # CURRENT WEEK STRAT

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

                if daily_filter != "All":

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
                        weekly_actionable_category
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
                        weekly_actionable_category
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
                    weekly_actionable_category
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
                    weekly_actionable_category
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

                # RVOL

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

            # =================================================
            # DISPLAY
            # =================================================

            if weekly_results.empty:

                st.warning(
                    "No weekly signals matched."
                )

            else:

                # =============================================
                # METRICS
                # =============================================

                c1, c2, c3, c4, c5 = (
                    st.columns(5)
                )

                c1.metric(
                    "Matches",
                    len(weekly_results)
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

                # =============================================
                # 1. WEEKLY SCANNER RESULTS
                # =============================================

                st.subheader(
                    "🔎 Weekly Scanner Results"
                )

                weekly_columns = [
                    "Ticker",
                    "Price",
                    "Prev Week Low",
                    "Prev Week High",
                    "Prev Week STRAT",
                    "Current Week Low",
                    "Current Week High",
                    "Current Week STRAT",
                    "Low Taken",
                    "Low Sweep Date",
                    "Low Reclaimed",
                    "Low Reclaim Date",
                    "High Taken",
                    "High Sweep Date",
                    "High Rejected",
                    "High Rejection Date",
                    "First Pre-Confirmation Signal",
                    "Pre-Confirmation Date",
                    "Pre-Confirmation Event",
                    "First Post-Confirmation Signal",
                    "Post-Confirmation Date",
                    "Post-Confirmation Event",
                    "Daily STRAT",
                    "Weekly FTFC",
                    "Monthly FTFC",
                    "FTFC",
                    "RVOL",
                    "% From PWL",
                    "% From PWH",
                    "Signal"
                ]

                st.dataframe(
                    weekly_results[
                        weekly_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )

                # =============================================
                # 2. WEEKLY POST-CONFIRMATION
                # =============================================

                weekly_confirmed = (
                    weekly_results[
                        weekly_results[
                            "First Post-Confirmation Signal"
                        ]
                        .notna()
                    ]
                )

                if not weekly_confirmed.empty:

                    st.subheader(
                        "✅ Weekly Post-Confirmation Signals"
                    )

                    st.caption(
                        "First Hammer, Shooting Star or "
                        "Inside Bar after PWL reclaim or "
                        "PWH rejection."
                    )

                    st.dataframe(
                        weekly_confirmed[
                            [
                                "Ticker",
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

                # =============================================
                # 3. WEEKLY PRE-CONFIRMATION
                # =============================================

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

                    st.caption(
                        "First Hammer, Shooting Star or "
                        "Inside Bar after the previous-week "
                        "level was taken but before the "
                        "reclaim/rejection."
                    )

                    st.dataframe(
                        weekly_pre[
                            [
                                "Ticker",
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

                # =============================================
                # 4. BULLISH WEEKLY SETUPS
                # =============================================

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
                                "RVOL",
                                "% From PWL",
                                "Signal"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                # =============================================
                # 5. BEARISH WEEKLY SETUPS
                # =============================================

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
                                "RVOL",
                                "% From PWH",
                                "Signal"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                # =============================================
                # DOWNLOAD
                # =============================================

                weekly_csv = (
                    weekly_results
                    .to_csv(index=False)
                    .encode("utf-8")
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

    # ========================================================
    # FILTERS
    # ========================================================

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

    m5, m6 = st.columns(2)

    monthly_actionable_category = (
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

    # ========================================================
    # RUN
    # ========================================================

    run_monthly = st.button(
        "🚀 Run Monthly Scanner",
        type="primary",
        use_container_width=True,
        key="run_monthly"
    )

    if run_monthly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            monthly_results = (
                scan_monthly(
                    selected_tickers,
                    st.session_state.market_data
                )
            )

            # =================================================
            # FILTER RESULTS
            # =================================================

            if not monthly_results.empty:

                # SIGNAL

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

                # MONTH STRAT

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

                # WEEK STRAT

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

                # ACTIONABLE

                if (
                    monthly_actionable_filter
                    != "All"
                ):

                    if (
                        monthly_actionable_category
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
                        monthly_actionable_category
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
                    monthly_actionable_category
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
                    monthly_actionable_category
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

                # RVOL

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

            # =================================================
            # DISPLAY
            # =================================================

            if monthly_results.empty:

                st.warning(
                    "No monthly signals matched."
                )

            else:

                # =============================================
                # METRICS
                # =============================================

                c1, c2, c3, c4, c5 = (
                    st.columns(5)
                )

                c1.metric(
                    "Matches",
                    len(monthly_results)
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

                # =============================================
                # 1. MONTHLY SCANNER RESULTS
                # =============================================

                st.subheader(
                    "🔎 Monthly Scanner Results"
                )

                st.dataframe(
                    monthly_results,
                    use_container_width=True,
                    hide_index=True
                )

                # =============================================
                # 2. MONTHLY POST-CONFIRMATION
                # =============================================

                confirmed_monthly = (
                    monthly_results[
                        monthly_results[
                            "First Post-Confirmation Weekly Signal"
                        ]
                        .notna()
                    ]
                )

                if not confirmed_monthly.empty:

                    st.subheader(
                        "✅ Monthly Post-Confirmation Signals"
                    )

                    st.caption(
                        "First weekly Hammer, Shooting Star "
                        "or Inside Bar after PML reclaim or "
                        "PMH rejection."
                    )

                    st.dataframe(
                        confirmed_monthly[
                            [
                                "Ticker",
                                "Price",
                                "Post-Confirmation Event",
                                "First Post-Confirmation Weekly Signal",
                                "Post-Confirmation Week",
                                "Prev Month STRAT",
                                "Current Month STRAT",
                                "Current Week STRAT",
                                "Monthly FTFC",
                                "RVOL",
                                "Signal"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                # =============================================
                # 3. MONTHLY PRE-CONFIRMATION
                # =============================================

                pre_monthly = (
                    monthly_results[
                        monthly_results[
                            "First Pre-Confirmation Weekly Signal"
                        ]
                        .notna()
                    ]
                )

                if not pre_monthly.empty:

                    st.subheader(
                        "⚠️ Monthly Pre-Confirmation Signals"
                    )

                    st.caption(
                        "First weekly Hammer, Shooting Star "
                        "or Inside Bar after PMH/PML was "
                        "taken but before confirmation."
                    )

                    st.dataframe(
                        pre_monthly[
                            [
                                "Ticker",
                                "Price",
                                "Pre-Confirmation Event",
                                "First Pre-Confirmation Weekly Signal",
                                "Pre-Confirmation Week",
                                "Prev Month STRAT",
                                "Current Month STRAT",
                                "Current Week STRAT",
                                "Monthly FTFC",
                                "RVOL",
                                "Signal"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                # =============================================
                # 4. BULLISH MONTHLY SETUPS
                # =============================================

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
                                "Price",
                                "Prev Month Low",
                                "PML Sweep Date",
                                "PML Reclaim Date",
                                "Prev Month STRAT",
                                "Current Month STRAT",
                                "Current Week STRAT",
                                "First Post-Confirmation Weekly Signal",
                                "Post-Confirmation Week",
                                "Monthly FTFC",
                                "RVOL",
                                "% From PML",
                                "Signal"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                # =============================================
                # 5. BEARISH MONTHLY SETUPS
                # =============================================

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
                                "Price",
                                "Prev Month High",
                                "PMH Sweep Date",
                                "PMH Rejection Date",
                                "Prev Month STRAT",
                                "Current Month STRAT",
                                "Current Week STRAT",
                                "First Post-Confirmation Weekly Signal",
                                "Post-Confirmation Week",
                                "Monthly FTFC",
                                "RVOL",
                                "% From PMH",
                                "Signal"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                # =============================================
                # DOWNLOAD
                # =============================================

                monthly_csv = (
                    monthly_results
                    .to_csv(index=False)
                    .encode("utf-8")
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
