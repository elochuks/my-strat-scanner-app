import streamlit as st
import yfinance as yf
import pandas as pd
import time


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="S&P 500 Weekly Sweep Scanner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 S&P 500 Weekly High / Low STRAT Scanner")

st.caption(
    "Scans for previous-week high/low sweeps, STRAT candles, "
    "FTFC, relative volume, and the first actionable daily "
    "candle after a weekly level is taken."
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
                "S&P 500 dataset does not contain a Symbol column."
            )

        tickers = (
            df["Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

        # Yahoo Finance format:
        # BRK.B -> BRK-B
        tickers = [
            ticker.replace(".", "-")
            for ticker in tickers
        ]

        return sorted(set(tickers))

    except Exception as e:

        st.error(
            f"Unable to load S&P 500 ticker dataset: {e}"
        )

        return []


# ============================================================
# DOWNLOAD MARKET DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    all_data = {}

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
                period="6mo",
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

                level_0 = (
                    data.columns
                    .get_level_values(0)
                    .unique()
                    .tolist()
                )

                level_1 = (
                    data.columns
                    .get_level_values(1)
                    .unique()
                    .tolist()
                )

                for ticker in batch:

                    try:

                        if ticker in level_0:

                            ticker_df = (
                                data[ticker]
                                .copy()
                            )

                        elif ticker in level_1:

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
                            all_data[ticker] = ticker_df

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
                    all_data[ticker] = ticker_df

        except Exception:
            continue

        time.sleep(0.25)

    return all_data


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

    # ========================================================
    # 3 OUTSIDE
    # ========================================================

    if (
        current_high > previous_high
        and
        current_low < previous_low
    ):
        return "3 Outside"

    # ========================================================
    # 1 INSIDE
    # ========================================================

    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):
        return "1 Inside"

    # ========================================================
    # 2 UP
    # ========================================================

    if current_high > previous_high:

        if current_close >= current_open:
            return "2U Green"

        return "2U Red"

    # ========================================================
    # 2 DOWN
    # ========================================================

    if current_low < previous_low:

        if current_close >= current_open:
            return "2D Green"

        return "2D Red"

    return "N/A"


# ============================================================
# WEEKLY LEVELS + WEEKLY STRAT
# ============================================================

def get_weekly_levels(df):

    if df is None or len(df) < 15:
        return None

    temp = df.copy()

    temp["Week"] = (
        temp.index.to_period("W-FRI")
    )

    weekly = (
        temp.groupby("Week")
        .agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum")
        )
    )

    if len(weekly) < 3:
        return None

    # ========================================================
    # CURRENT WEEK
    # ========================================================

    current_week_period = (
        temp["Week"].iloc[-1]
    )

    current_week_data = temp[
        temp["Week"]
        == current_week_period
    ].copy()

    # ========================================================
    # COMPLETED WEEKS
    # ========================================================

    completed_weeks = weekly[
        weekly.index
        < current_week_period
    ]

    if len(completed_weeks) < 2:
        return None

    previous_week = (
        completed_weeks.iloc[-1]
    )

    two_weeks_ago = (
        completed_weeks.iloc[-2]
    )

    # ========================================================
    # PREVIOUS WEEK VALUES
    # ========================================================

    previous_week_open = float(
        previous_week["Open"]
    )

    previous_week_high = float(
        previous_week["High"]
    )

    previous_week_low = float(
        previous_week["Low"]
    )

    previous_week_close = float(
        previous_week["Close"]
    )

    # ========================================================
    # TWO WEEKS AGO
    # ========================================================

    two_weeks_ago_high = float(
        two_weeks_ago["High"]
    )

    two_weeks_ago_low = float(
        two_weeks_ago["Low"]
    )

    # ========================================================
    # PREVIOUS WEEK STRAT
    #
    # Previous completed week vs week before it
    # ========================================================

    previous_week_strat = (
        classify_strat_candle(
            previous_week_open,
            previous_week_high,
            previous_week_low,
            previous_week_close,
            two_weeks_ago_high,
            two_weeks_ago_low
        )
    )

    # ========================================================
    # CURRENT WEEK VALUES
    # ========================================================

    current_week_open = float(
        current_week_data[
            "Open"
        ].iloc[0]
    )

    current_week_high = float(
        current_week_data[
            "High"
        ].max()
    )

    current_week_low = float(
        current_week_data[
            "Low"
        ].min()
    )

    current_week_close = float(
        current_week_data[
            "Close"
        ].iloc[-1]
    )

    # ========================================================
    # CURRENT WEEK STRAT
    #
    # Current developing week vs previous completed week
    # ========================================================

    current_week_strat = (
        classify_strat_candle(
            current_week_open,
            current_week_high,
            current_week_low,
            current_week_close,
            previous_week_high,
            previous_week_low
        )
    )

    return {

        "previous_week_open":
            previous_week_open,

        "previous_week_high":
            previous_week_high,

        "previous_week_low":
            previous_week_low,

        "previous_week_close":
            previous_week_close,

        "previous_week_strat":
            previous_week_strat,

        "two_weeks_ago_high":
            two_weeks_ago_high,

        "two_weeks_ago_low":
            two_weeks_ago_low,

        "current_week_open":
            current_week_open,

        "current_week_high":
            current_week_high,

        "current_week_low":
            current_week_low,

        "current_week_close":
            current_week_close,

        "current_week_strat":
            current_week_strat,

        "current_week":
            str(current_week_period)
    }


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
# ACTIONABLE DAILY CANDLE CLASSIFICATION
# ============================================================

def classify_actionable_candle(
    current_open,
    current_high,
    current_low,
    current_close,
    previous_high,
    previous_low
):

    """
    Actionable daily signals:

    - Hammer
    - Shooter
    - Inside Bar
    """

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

    # Prevent near-zero bodies from
    # distorting wick/body calculations.
    effective_body = max(
        body,
        candle_range * 0.05
    )

    # ========================================================
    # INSIDE BAR
    # ========================================================

    inside_bar = (
        current_high <= previous_high
        and
        current_low >= previous_low
    )

    if inside_bar:
        return "Inside Bar"

    # ========================================================
    # HAMMER
    #
    # Long lower wick
    # Relatively small upper wick
    # ========================================================

    hammer = (
        lower_wick
        >= (2 * effective_body)
        and
        upper_wick
        <= effective_body
        and
        lower_wick
        >= (candle_range * 0.50)
    )

    if hammer:
        return "Hammer"

    # ========================================================
    # SHOOTER / SHOOTING STAR
    #
    # Long upper wick
    # Relatively small lower wick
    # ========================================================

    shooter = (
        upper_wick
        >= (2 * effective_body)
        and
        lower_wick
        <= effective_body
        and
        upper_wick
        >= (candle_range * 0.50)
    )

    if shooter:
        return "Shooter"

    return None


# ============================================================
# FTFC
# ============================================================

def calculate_ftfc(
    df,
    weekly_levels
):

    try:

        current_price = float(
            df["Close"].iloc[-1]
        )

        # ====================================================
        # WEEKLY
        # ====================================================

        weekly_open = (
            weekly_levels[
                "current_week_open"
            ]
        )

        if current_price > weekly_open:

            weekly_ftfc = "Up"

        elif current_price < weekly_open:

            weekly_ftfc = "Down"

        else:

            weekly_ftfc = "Neutral"

        # ====================================================
        # MONTHLY
        # ====================================================

        current_month = (
            df.index[-1]
            .to_period("M")
        )

        month_data = df[
            df.index.to_period("M")
            == current_month
        ]

        if month_data.empty:

            monthly_ftfc = "N/A"
            monthly_open = None

        else:

            monthly_open = float(
                month_data[
                    "Open"
                ].iloc[0]
            )

            if current_price > monthly_open:

                monthly_ftfc = "Up"

            elif current_price < monthly_open:

                monthly_ftfc = "Down"

            else:

                monthly_ftfc = "Neutral"

        # ====================================================
        # MONTHLY + WEEKLY ALIGNMENT
        # ====================================================

        if (
            weekly_ftfc == "Up"
            and
            monthly_ftfc == "Up"
        ):

            alignment = "FTFC Up"

        elif (
            weekly_ftfc == "Down"
            and
            monthly_ftfc == "Down"
        ):

            alignment = "FTFC Down"

        else:

            alignment = "Mixed"

        return {

            "weekly":
                weekly_ftfc,

            "monthly":
                monthly_ftfc,

            "alignment":
                alignment,

            "weekly_open":
                weekly_open,

            "monthly_open":
                monthly_open
        }

    except Exception:

        return {

            "weekly": "N/A",

            "monthly": "N/A",

            "alignment": "N/A",

            "weekly_open": None,

            "monthly_open": None
        }


# ============================================================
# RELATIVE VOLUME
# ============================================================

def calculate_rvol(
    df,
    lookback=20
):

    try:

        if len(df) < (
            lookback + 1
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
            / average_volume
        )

    except Exception:

        return None


# ============================================================
# FIND WEEKLY SWEEP DATES
# ============================================================

def find_sweep_dates(
    df,
    previous_week_high,
    previous_week_low
):

    current_period = (
        df.index[-1]
        .to_period("W-FRI")
    )

    current_week = df[
        df.index.to_period("W-FRI")
        == current_period
    ]

    high_sweep_date = None
    low_sweep_date = None

    for date, row in (
        current_week.iterrows()
    ):

        # ====================================================
        # PWL TAKEN
        # ====================================================

        if (
            low_sweep_date is None
            and
            float(row["Low"])
            < previous_week_low
        ):

            low_sweep_date = (
                date.strftime(
                    "%Y-%m-%d"
                )
            )

        # ====================================================
        # PWH TAKEN
        # ====================================================

        if (
            high_sweep_date is None
            and
            float(row["High"])
            > previous_week_high
        ):

            high_sweep_date = (
                date.strftime(
                    "%Y-%m-%d"
                )
            )

    return (
        low_sweep_date,
        high_sweep_date
    )


# ============================================================
# FIRST ACTIONABLE SIGNAL AFTER WEEKLY SWEEP
# ============================================================

def find_first_actionable_signal(
    df,
    low_sweep_date,
    high_sweep_date
):

    """
    Searches for the FIRST actionable DAILY candle
    after a previous-week level has been taken.

    Reclaim/rejection is NOT required.

    Actionable signals:

    - Hammer
    - Shooter
    - Inside Bar

    The sweep candle itself can qualify because the
    level was taken intraday before the daily candle closed.
    """

    if (
        low_sweep_date is None
        and
        high_sweep_date is None
    ):

        return None, None, None

    # ========================================================
    # CONVERT DATES
    # ========================================================

    low_date = (
        pd.Timestamp(
            low_sweep_date
        )
        if low_sweep_date
        else None
    )

    high_date = (
        pd.Timestamp(
            high_sweep_date
        )
        if high_sweep_date
        else None
    )

    sweep_dates = [
        date
        for date in [
            low_date,
            high_date
        ]
        if date is not None
    ]

    if not sweep_dates:

        return None, None, None

    # Start searching from earliest sweep
    first_sweep_date = min(
        sweep_dates
    )

    # ========================================================
    # SEARCH DAILY CANDLES
    # ========================================================

    for i in range(
        1,
        len(df)
    ):

        current_date = (
            df.index[i]
        )

        if (
            current_date
            < first_sweep_date
        ):
            continue

        previous = (
            df.iloc[i - 1]
        )

        current = (
            df.iloc[i]
        )

        actionable_signal = (
            classify_actionable_candle(
                float(current["Open"]),
                float(current["High"]),
                float(current["Low"]),
                float(current["Close"]),
                float(previous["High"]),
                float(previous["Low"])
            )
        )

        if actionable_signal is None:
            continue

        # ====================================================
        # WHICH WEEKLY LEVEL(S) HAD BEEN TAKEN
        # BEFORE/ON THIS SIGNAL DATE?
        # ====================================================

        low_active = (
            low_date is not None
            and
            current_date >= low_date
        )

        high_active = (
            high_date is not None
            and
            current_date >= high_date
        )

        if (
            low_active
            and
            high_active
        ):

            context = (
                "PWL + PWH Taken"
            )

        elif low_active:

            context = (
                "PWL Taken"
            )

        elif high_active:

            context = (
                "PWH Taken"
            )

        else:

            continue

        return (
            actionable_signal,
            current_date.strftime(
                "%Y-%m-%d"
            ),
            context
        )

    return (
        None,
        None,
        None
    )


# ============================================================
# MAIN SCANNER
# ============================================================

def scan_market(
    tickers,
    market_data
):

    results = []

    total = len(tickers)

    progress = st.progress(0)
    status = st.empty()

    # ========================================================
    # BULLISH DAILY STRAT PATTERNS
    # ========================================================

    bullish_daily_patterns = [

        "2U Green",

        "2D Green",

        "2U Red",

        "1 Inside",

        "3 Outside"
    ]

    # ========================================================
    # BEARISH DAILY STRAT PATTERNS
    # ========================================================

    bearish_daily_patterns = [

        "2D Red",

        "2U Red",

        "2D Green",

        "1 Inside",

        "3 Outside"
    ]

    for index, ticker in enumerate(
        tickers
    ):

        status.text(
            f"Scanning {ticker} "
            f"({index + 1}/{total})"
        )

        try:

            # =================================================
            # CLEAN DATA
            # =================================================

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

                progress.progress(
                    (index + 1)
                    / total
                )

                continue

            # =================================================
            # WEEKLY LEVELS
            # =================================================

            levels = (
                get_weekly_levels(
                    df
                )
            )

            if levels is None:

                progress.progress(
                    (index + 1)
                    / total
                )

                continue

            previous_week_high = (
                levels[
                    "previous_week_high"
                ]
            )

            previous_week_low = (
                levels[
                    "previous_week_low"
                ]
            )

            previous_week_strat = (
                levels[
                    "previous_week_strat"
                ]
            )

            current_week_strat = (
                levels[
                    "current_week_strat"
                ]
            )

            current_week_high = (
                levels[
                    "current_week_high"
                ]
            )

            current_week_low = (
                levels[
                    "current_week_low"
                ]
            )

            current_price = float(
                df["Close"]
                .iloc[-1]
            )

            # =================================================
            # WEEKLY LEVEL TAKEN
            # =================================================

            high_taken = (
                current_week_high
                > previous_week_high
            )

            low_taken = (
                current_week_low
                < previous_week_low
            )

            # =================================================
            # RECLAIM / REJECTION
            # =================================================

            low_reclaimed = (
                low_taken
                and
                current_price
                > previous_week_low
            )

            high_rejected = (
                high_taken
                and
                current_price
                < previous_week_high
            )

            # =================================================
            # SWEEP DATES
            # =================================================

            (
                low_sweep_date,
                high_sweep_date
            ) = find_sweep_dates(
                df,
                previous_week_high,
                previous_week_low
            )

            # =================================================
            # FIRST ACTIONABLE DAILY SIGNAL
            #
            # Starts looking only after PWL/PWH is taken.
            #
            # Reclaim/rejection is NOT required.
            # =================================================

            (
                first_actionable_signal,
                actionable_signal_date,
                actionable_after
            ) = find_first_actionable_signal(
                df,
                low_sweep_date,
                high_sweep_date
            )

            # =================================================
            # DAILY STRAT
            # =================================================

            daily_strat = (
                get_daily_strat(
                    df
                )
            )

            # =================================================
            # FTFC
            # =================================================

            ftfc = (
                calculate_ftfc(
                    df,
                    levels
                )
            )

            # =================================================
            # RVOL
            # =================================================

            rvol = (
                calculate_rvol(
                    df
                )
            )

            # =================================================
            # DISTANCE FROM LEVELS
            # =================================================

            pct_from_low = (
                (
                    current_price
                    - previous_week_low
                )
                / previous_week_low
            ) * 100

            pct_from_high = (
                (
                    current_price
                    - previous_week_high
                )
                / previous_week_high
            ) * 100

            # =================================================
            # BULLISH SETUP
            # =================================================

            bullish_setup = (
                low_taken
                and
                low_reclaimed
                and
                daily_strat
                in bullish_daily_patterns
                and
                ftfc["weekly"]
                == "Up"
            )

            # =================================================
            # BEARISH SETUP
            # =================================================

            bearish_setup = (
                high_taken
                and
                high_rejected
                and
                daily_strat
                in bearish_daily_patterns
                and
                ftfc["weekly"]
                == "Down"
            )

            # =================================================
            # ONLY RETURN WEEKLY SWEEPS
            # =================================================

            if not (
                low_taken
                or
                high_taken
            ):

                progress.progress(
                    (index + 1)
                    / total
                )

                continue

            # =================================================
            # SIGNAL
            # =================================================

            if bullish_setup:

                signal = (
                    f"PWL Taken → "
                    f"Reclaimed → "
                    f"Daily {daily_strat} → "
                    f"Weekly FTFC Up"
                )

            elif bearish_setup:

                signal = (
                    f"PWH Taken → "
                    f"Rejected → "
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
            # RESULTS
            # =================================================

            results.append({

                "Ticker":
                    ticker,

                "Price":
                    round(
                        current_price,
                        2
                    ),

                # =============================================
                # PREVIOUS WEEK
                # =============================================

                "Prev Week Low":
                    round(
                        previous_week_low,
                        2
                    ),

                "Prev Week High":
                    round(
                        previous_week_high,
                        2
                    ),

                "Prev Week STRAT":
                    previous_week_strat,

                # =============================================
                # CURRENT WEEK
                # =============================================

                "Current Week Low":
                    round(
                        current_week_low,
                        2
                    ),

                "Current Week High":
                    round(
                        current_week_high,
                        2
                    ),

                "Current Week STRAT":
                    current_week_strat,

                # =============================================
                # LOW SWEEP
                # =============================================

                "Low Taken":
                    low_taken,

                "Low Sweep Date":
                    low_sweep_date,

                "Low Reclaimed":
                    low_reclaimed,

                # =============================================
                # HIGH SWEEP
                # =============================================

                "High Taken":
                    high_taken,

                "High Sweep Date":
                    high_sweep_date,

                "High Rejected":
                    high_rejected,

                # =============================================
                # DAILY STRAT
                # =============================================

                "Daily STRAT":
                    daily_strat,

                # =============================================
                # FIRST ACTIONABLE SIGNAL
                # =============================================

                "First Actionable Signal":
                    first_actionable_signal,

                "Actionable Signal Date":
                    actionable_signal_date,

                "Actionable After":
                    actionable_after,

                # =============================================
                # FTFC
                # =============================================

                "Weekly FTFC":
                    ftfc["weekly"],

                "Monthly FTFC":
                    ftfc["monthly"],

                "FTFC":
                    ftfc["alignment"],

                # =============================================
                # VOLUME
                # =============================================

                "RVOL":
                    (
                        round(
                            rvol,
                            2
                        )
                        if rvol is not None
                        else None
                    ),

                # =============================================
                # DISTANCE
                # =============================================

                "% From PWL":
                    round(
                        pct_from_low,
                        2
                    ),

                "% From PWH":
                    round(
                        pct_from_high,
                        2
                    ),

                # =============================================
                # SETUPS
                # =============================================

                "Bullish Setup":
                    bullish_setup,

                "Bearish Setup":
                    bearish_setup,

                "Signal":
                    signal
            })

        except Exception:
            pass

        progress.progress(
            (index + 1)
            / total
        )

    progress.empty()
    status.empty()

    return pd.DataFrame(
        results
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "⚙️ Scanner Settings"
)


# ============================================================
# LOAD S&P 500
# ============================================================

with st.spinner(
    "Loading S&P 500 universe..."
):

    sp500_tickers = (
        get_sp500_tickers()
    )


# ============================================================
# MARKET UNIVERSE
# ============================================================

universe = (
    st.sidebar.selectbox(
        "Market Universe",
        [
            "S&P 500",
            "Custom Watchlist"
        ]
    )
)


if universe == "S&P 500":

    selected_tickers = (
        sp500_tickers
    )

else:

    custom_input = (
        st.sidebar.text_area(
            "Enter tickers",
            value=(
                "AAPL,MSFT,NVDA,"
                "AMD,TSLA,AMZN,META"
            ),
            help=(
                "Separate ticker symbols "
                "with commas."
            )
        )
    )

    selected_tickers = [
        ticker.strip().upper()
        for ticker
        in custom_input.split(",")
        if ticker.strip()
    ]


# ============================================================
# WEEKLY SIGNAL FILTER
# ============================================================

signal_filter = (
    st.sidebar.selectbox(
        "Weekly Signal",
        [
            "All Sweeps",
            "Previous Week Low Taken",
            "Previous Week High Taken",
            "Low Taken + Reclaimed",
            "High Taken + Rejected",
            "Both Weekly Levels Taken",
            "Bullish STRAT Setup",
            "Bearish STRAT Setup"
        ]
    )
)


# ============================================================
# PREVIOUS WEEK STRAT FILTER
# ============================================================

prev_week_strat_filter = (
    st.sidebar.selectbox(
        "Previous Week STRAT",
        [
            "All",
            "1 Inside",
            "2U Green",
            "2U Red",
            "2D Green",
            "2D Red",
            "3 Outside"
        ]
    )
)


# ============================================================
# CURRENT WEEK STRAT FILTER
# ============================================================

current_week_strat_filter = (
    st.sidebar.selectbox(
        "Current Week STRAT",
        [
            "All",
            "1 Inside",
            "2U Green",
            "2U Red",
            "2D Green",
            "2D Red",
            "3 Outside"
        ]
    )
)


# ============================================================
# DAILY STRAT FILTER
# ============================================================

daily_strat_filter = (
    st.sidebar.selectbox(
        "Daily STRAT",
        [
            "All",
            "1 Inside",
            "2U Green",
            "2U Red",
            "2D Green",
            "2D Red",
            "3 Outside"
        ]
    )
)


# ============================================================
# ACTIONABLE SIGNAL FILTER
# ============================================================

actionable_filter = (
    st.sidebar.selectbox(
        "First Actionable Signal",
        [
            "All",
            "Has Actionable Signal",
            "No Actionable Signal",
            "Hammer",
            "Shooter",
            "Inside Bar"
        ]
    )
)


# ============================================================
# ACTIONABLE CONTEXT FILTER
# ============================================================

actionable_after_filter = (
    st.sidebar.selectbox(
        "Actionable After",
        [
            "All",
            "PWL Taken",
            "PWH Taken",
            "PWL + PWH Taken"
        ]
    )
)


# ============================================================
# FTFC FILTER
# ============================================================

ftfc_filter = (
    st.sidebar.selectbox(
        "M/W FTFC",
        [
            "All",
            "FTFC Up",
            "FTFC Down",
            "Mixed"
        ]
    )
)


# ============================================================
# MINIMUM RVOL
# ============================================================

minimum_rvol = (
    st.sidebar.number_input(
        "Minimum RVOL",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.1
    )
)


# ============================================================
# STOCK COUNT
# ============================================================

st.sidebar.metric(
    "Stocks to Scan",
    len(selected_tickers)
)


# ============================================================
# RUN BUTTON
# ============================================================

run_scan = (
    st.sidebar.button(
        "🚀 Scan Market",
        type="primary",
        use_container_width=True
    )
)


# ============================================================
# RUN SCANNER
# ============================================================

if run_scan:

    if not selected_tickers:

        st.error(
            "No ticker symbols available."
        )

        st.stop()

    # ========================================================
    # DOWNLOAD
    # ========================================================

    with st.spinner(
        f"Downloading market data for "
        f"{len(selected_tickers)} stocks..."
    ):

        market_data = (
            download_market_data(
                selected_tickers
            )
        )

    if not market_data:

        st.error(
            "Yahoo Finance did not return market data."
        )

        st.stop()

    st.caption(
        f"Downloaded "
        f"{len(market_data)} / "
        f"{len(selected_tickers)} symbols."
    )

    # ========================================================
    # SCAN
    # ========================================================

    results = scan_market(
        selected_tickers,
        market_data
    )

    # ========================================================
    # APPLY FILTERS
    # ========================================================

    if not results.empty:

        # ====================================================
        # SIGNAL FILTER
        # ====================================================

        if (
            signal_filter
            == "Previous Week Low Taken"
        ):

            results = results[
                results["Low Taken"]
            ]

        elif (
            signal_filter
            == "Previous Week High Taken"
        ):

            results = results[
                results["High Taken"]
            ]

        elif (
            signal_filter
            == "Low Taken + Reclaimed"
        ):

            results = results[
                results["Low Reclaimed"]
            ]

        elif (
            signal_filter
            == "High Taken + Rejected"
        ):

            results = results[
                results["High Rejected"]
            ]

        elif (
            signal_filter
            == "Both Weekly Levels Taken"
        ):

            results = results[
                results["Low Taken"]
                &
                results["High Taken"]
            ]

        elif (
            signal_filter
            == "Bullish STRAT Setup"
        ):

            results = results[
                results["Bullish Setup"]
            ]

        elif (
            signal_filter
            == "Bearish STRAT Setup"
        ):

            results = results[
                results["Bearish Setup"]
            ]

        # ====================================================
        # PREVIOUS WEEK STRAT
        # ====================================================

        if (
            prev_week_strat_filter
            != "All"
        ):

            results = results[
                results[
                    "Prev Week STRAT"
                ]
                == prev_week_strat_filter
            ]

        # ====================================================
        # CURRENT WEEK STRAT
        # ====================================================

        if (
            current_week_strat_filter
            != "All"
        ):

            results = results[
                results[
                    "Current Week STRAT"
                ]
                == current_week_strat_filter
            ]

        # ====================================================
        # DAILY STRAT
        # ====================================================

        if (
            daily_strat_filter
            != "All"
        ):

            results = results[
                results[
                    "Daily STRAT"
                ]
                == daily_strat_filter
            ]

        # ====================================================
        # ACTIONABLE SIGNAL
        # ====================================================

        if (
            actionable_filter
            == "Has Actionable Signal"
        ):

            results = results[
                results[
                    "First Actionable Signal"
                ].notna()
            ]

        elif (
            actionable_filter
            == "No Actionable Signal"
        ):

            results = results[
                results[
                    "First Actionable Signal"
                ].isna()
            ]

        elif actionable_filter in [
            "Hammer",
            "Shooter",
            "Inside Bar"
        ]:

            results = results[
                results[
                    "First Actionable Signal"
                ]
                == actionable_filter
            ]

        # ====================================================
        # ACTIONABLE AFTER FILTER
        # ====================================================

        if (
            actionable_after_filter
            != "All"
        ):

            results = results[
                results[
                    "Actionable After"
                ]
                == actionable_after_filter
            ]

        # ====================================================
        # FTFC
        # ====================================================

        if ftfc_filter != "All":

            results = results[
                results["FTFC"]
                == ftfc_filter
            ]

        # ====================================================
        # RVOL
        # ====================================================

        if minimum_rvol > 0:

            results = results[
                results["RVOL"]
                .fillna(0)
                >= minimum_rvol
            ]

    # ========================================================
    # OUTPUT
    # ========================================================

    st.divider()

    if results.empty:

        st.warning(
            "No stocks matched the selected conditions."
        )

    else:

        # ====================================================
        # METRICS
        # ====================================================

        c1, c2, c3, c4, c5 = (
            st.columns(5)
        )

        c1.metric(
            "Matches",
            len(results)
        )

        c2.metric(
            "PWL Taken",
            int(
                results[
                    "Low Taken"
                ].sum()
            )
        )

        c3.metric(
            "PWH Taken",
            int(
                results[
                    "High Taken"
                ].sum()
            )
        )

        c4.metric(
            "STRAT Setups",
            int(
                results[
                    "Bullish Setup"
                ].sum()
                +
                results[
                    "Bearish Setup"
                ].sum()
            )
        )

        c5.metric(
            "Actionable Signals",
            int(
                results[
                    "First Actionable Signal"
                ]
                .notna()
                .sum()
            )
        )

        # ====================================================
        # SORT
        # ====================================================

        results = (
            results.sort_values(
                by=[
                    "Bullish Setup",
                    "Bearish Setup",
                    "Actionable Signal Date",
                    "RVOL"
                ],
                ascending=[
                    False,
                    False,
                    True,
                    False
                ],
                na_position="last"
            )
        )

        # ====================================================
        # MAIN RESULTS
        # ====================================================

        st.subheader(
            "🔎 Scanner Results"
        )

        display_columns = [

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

            "High Taken",

            "High Sweep Date",

            "High Rejected",

            "Daily STRAT",

            # ================================================
            # ACTIONABLE SIGNAL
            # ================================================

            "First Actionable Signal",

            "Actionable Signal Date",

            "Actionable After",

            # ================================================
            # FTFC / VOLUME
            # ================================================

            "Weekly FTFC",

            "Monthly FTFC",

            "FTFC",

            "RVOL",

            "% From PWL",

            "% From PWH",

            "Signal"
        ]

        st.dataframe(
            results[
                display_columns
            ],
            use_container_width=True,
            hide_index=True,
            column_config={

                "Price":
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    ),

                "Prev Week Low":
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    ),

                "Prev Week High":
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    ),

                "Current Week Low":
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    ),

                "Current Week High":
                    st.column_config.NumberColumn(
                        format="$%.2f"
                    ),

                "RVOL":
                    st.column_config.NumberColumn(
                        format="%.2fx"
                    ),

                "% From PWL":
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),

                "% From PWH":
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    )
            }
        )

        # ====================================================
        # ACTIONABLE SIGNALS TABLE
        # ====================================================

        actionable = results[
            results[
                "First Actionable Signal"
            ].notna()
        ]

        if not actionable.empty:

            st.subheader(
                "⚡ First Actionable Signals"
            )

            st.caption(
                "First Hammer, Shooter, or Inside Bar identified "
                "on or after PWL/PWH was taken. "
                "Reclaim/rejection is not required."
            )

            st.dataframe(
                actionable[
                    [
                        "Ticker",
                        "Price",
                        "Low Sweep Date",
                        "High Sweep Date",
                        "First Actionable Signal",
                        "Actionable Signal Date",
                        "Actionable After",
                        "Daily STRAT",
                        "Current Week STRAT",
                        "Weekly FTFC",
                        "RVOL"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # BULLISH SETUPS
        # ====================================================

        bullish = results[
            results[
                "Bullish Setup"
            ]
        ]

        if not bullish.empty:

            st.subheader(
                "🟢 Bullish STRAT Setups"
            )

            st.caption(
                "PWL Taken → Reclaimed → "
                "Daily 2U Green / 2D Green / "
                "2U Red / 1 Inside / 3 Outside → "
                "Weekly FTFC Up"
            )

            st.dataframe(
                bullish[
                    [
                        "Ticker",
                        "Price",
                        "Prev Week Low",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "Low Sweep Date",
                        "Daily STRAT",
                        "First Actionable Signal",
                        "Actionable Signal Date",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "RVOL",
                        "Signal"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # BEARISH SETUPS
        # ====================================================

        bearish = results[
            results[
                "Bearish Setup"
            ]
        ]

        if not bearish.empty:

            st.subheader(
                "🔴 Bearish STRAT Setups"
            )

            st.caption(
                "PWH Taken → Rejected → "
                "Daily 2D Red / 2U Red / "
                "2D Green / 1 Inside / 3 Outside → "
                "Weekly FTFC Down"
            )

            st.dataframe(
                bearish[
                    [
                        "Ticker",
                        "Price",
                        "Prev Week High",
                        "Prev Week STRAT",
                        "Current Week STRAT",
                        "High Sweep Date",
                        "Daily STRAT",
                        "First Actionable Signal",
                        "Actionable Signal Date",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "RVOL",
                        "Signal"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # CSV DOWNLOAD
        # ====================================================

        csv = (
            results
            .to_csv(
                index=False
            )
            .encode("utf-8")
        )

        st.download_button(
            "⬇️ Download Results",
            data=csv,
            file_name=(
                "sp500_weekly_strat_scanner.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )


# ============================================================
# HOME PAGE
# ============================================================

else:

    if sp500_tickers:

        st.success(
            f"✓ Loaded "
            f"{len(sp500_tickers)} "
            f"S&P 500 symbols."
        )

    st.markdown(
        """
### ⚡ Actionable Signal Logic

After the **Previous Week Low (PWL)** or **Previous Week High (PWH)**
is taken, the scanner begins looking for the first actionable
daily candle.

A reclaim or rejection is **not required**.

The actionable candles are:

- **Hammer**
- **Shooter**
- **Inside Bar**

The scanner records:

- **First Actionable Signal**
- **Actionable Signal Date**
- **Actionable After** — PWL Taken, PWH Taken, or both

The sweep candle itself can qualify as the first actionable signal
because the weekly level can be taken intraday before the daily
candle closes.


### 🟢 Bullish STRAT Setup

**PWL Taken → Reclaimed → Daily STRAT → Weekly FTFC Up**

Accepted Daily STRAT:

- 2U Green
- 2D Green
- 2U Red
- 1 Inside
- 3 Outside


### 🔴 Bearish STRAT Setup

**PWH Taken → Rejected → Daily STRAT → Weekly FTFC Down**

Accepted Daily STRAT:

- 2D Red
- 2U Red
- 2D Green
- 1 Inside
- 3 Outside


### 📊 Weekly STRAT

The scanner calculates:

**Previous Week STRAT**
- Previous completed week compared with the week before it.

**Current Week STRAT**
- Current developing week compared with the previous completed week.
"""
    )
