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
    "Scans for previous-week high/low sweeps, reclaims/rejections, "
    "STRAT candles, actionable daily candles, FTFC and relative volume."
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
            raise ValueError("Dataset does not contain Symbol column.")

        tickers = (
            df["Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
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

                            all_data[
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

                    all_data[
                        ticker
                    ] = ticker_df

        except Exception:

            continue

        time.sleep(0.25)

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
# WEEKLY DATA
# ============================================================

def get_weekly_levels(df):

    if df is None or len(df) < 15:
        return None

    temp = df.copy()

    temp["Week"] = (
        temp.index.to_period(
            "W-FRI"
        )
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

    current_week_period = (
        temp["Week"]
        .iloc[-1]
    )

    current_week_data = temp[
        temp["Week"]
        == current_week_period
    ].copy()

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

    # Previous week
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

    # Two weeks ago
    two_weeks_ago_high = float(
        two_weeks_ago["High"]
    )

    two_weeks_ago_low = float(
        two_weeks_ago["Low"]
    )

    # Previous Week STRAT
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

    # Current week
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

    # Current Week STRAT
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
# ACTIONABLE CANDLE
#
# Hammer
# Shooting Star
# Inside Bar
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
    # Small upper wick
    # Small real body
    # ========================================================

    hammer = (
        lower_wick
        >= (2 * body_for_ratio)
        and
        upper_wick
        <= body_for_ratio
        and
        body
        <= candle_range * 0.40
    )

    if hammer:

        return "Hammer"

    # ========================================================
    # SHOOTING STAR
    #
    # Long upper wick
    # Small lower wick
    # Small real body
    # ========================================================

    shooting_star = (
        upper_wick
        >= (2 * body_for_ratio)
        and
        lower_wick
        <= body_for_ratio
        and
        body
        <= candle_range * 0.40
    )

    if shooting_star:

        return "Shooting Star"

    return None


# ============================================================
# ACTIONABLE SIGNAL HISTORY
#
# CATEGORY 2:
# PWL/PWH taken but not yet reclaimed/rejected
#
# CATEGORY 1:
# PWL taken + reclaimed
# PWH taken + rejected
#
# We retain BOTH first signals independently.
# ============================================================

def find_actionable_signals(
    df,
    previous_week_high,
    previous_week_low
):

    empty_result = {

        "pre_signal": None,
        "pre_date": None,
        "pre_event": None,

        "post_signal": None,
        "post_date": None,
        "post_event": None,

        "low_taken_date": None,
        "low_reclaim_date": None,

        "high_taken_date": None,
        "high_rejection_date": None
    }

    if df is None or len(df) < 2:
        return empty_result

    current_period = (
        df.index[-1]
        .to_period("W-FRI")
    )

    current_week = df[
        df.index.to_period("W-FRI")
        == current_period
    ].copy()

    if current_week.empty:
        return empty_result

    # ========================================================
    # STATE
    # ========================================================

    low_taken = False
    high_taken = False

    low_reclaimed = False
    high_rejected = False

    low_taken_date = None
    high_taken_date = None

    low_reclaim_date = None
    high_rejection_date = None

    pre_signal = None
    pre_signal_date = None
    pre_event = None

    post_signal = None
    post_signal_date = None
    post_event = None

    # ========================================================
    # WALK CURRENT WEEK CHRONOLOGICALLY
    # ========================================================

    for current_date, current_row in (
        current_week.iterrows()
    ):

        current_open = float(
            current_row["Open"]
        )

        current_high = float(
            current_row["High"]
        )

        current_low = float(
            current_row["Low"]
        )

        current_close = float(
            current_row["Close"]
        )

        # ====================================================
        # LEVEL TAKEN
        # ====================================================

        if (
            not low_taken
            and
            current_low
            < previous_week_low
        ):

            low_taken = True

            low_taken_date = (
                current_date
            )

        if (
            not high_taken
            and
            current_high
            > previous_week_high
        ):

            high_taken = True

            high_taken_date = (
                current_date
            )

        # ====================================================
        # RECLAIM / REJECTION
        #
        # Determined using daily close.
        # ====================================================

        if (
            low_taken
            and
            not low_reclaimed
            and
            current_close
            > previous_week_low
        ):

            low_reclaimed = True

            low_reclaim_date = (
                current_date
            )

        if (
            high_taken
            and
            not high_rejected
            and
            current_close
            < previous_week_high
        ):

            high_rejected = True

            high_rejection_date = (
                current_date
            )

        # ====================================================
        # PREVIOUS DAILY CANDLE
        # ====================================================

        location = (
            df.index.get_loc(
                current_date
            )
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
                )
            )
        )

        if actionable is None:
            continue

        # ====================================================
        # CATEGORY 1
        #
        # POST-CONFIRMATION
        #
        # Once reclaim/rejection has occurred, this candle
        # can become the first confirmed actionable signal.
        # ====================================================

        if post_signal is None:

            post_candidates = []

            if (
                low_taken
                and
                low_reclaimed
                and
                low_reclaim_date
                is not None
                and
                current_date
                >= low_reclaim_date
            ):

                post_candidates.append(
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
                high_rejection_date
                is not None
                and
                current_date
                >= high_rejection_date
            ):

                post_candidates.append(
                    (
                        high_rejection_date,
                        "PWH Taken → Rejected"
                    )
                )

            if post_candidates:

                post_candidates.sort(
                    key=lambda x: x[0]
                )

                post_signal = actionable

                post_signal_date = (
                    current_date
                )

                post_event = (
                    post_candidates[0][1]
                )

        # ====================================================
        # CATEGORY 2
        #
        # PRE-CONFIRMATION
        #
        # Level was taken but NOT yet reclaimed/rejected.
        # ====================================================

        if pre_signal is None:

            pre_candidates = []

            if (
                low_taken
                and
                not low_reclaimed
                and
                low_taken_date
                is not None
                and
                current_date
                >= low_taken_date
            ):

                pre_candidates.append(
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
                and
                current_date
                >= high_taken_date
            ):

                pre_candidates.append(
                    (
                        high_taken_date,
                        "PWH Taken → Not Yet Rejected"
                    )
                )

            if pre_candidates:

                pre_candidates.sort(
                    key=lambda x: x[0]
                )

                pre_signal = actionable

                pre_signal_date = (
                    current_date
                )

                pre_event = (
                    pre_candidates[0][1]
                )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "pre_signal":
            pre_signal,

        "pre_date":
            (
                pre_signal_date.strftime(
                    "%Y-%m-%d"
                )
                if pre_signal_date
                is not None
                else None
            ),

        "pre_event":
            pre_event,

        "post_signal":
            post_signal,

        "post_date":
            (
                post_signal_date.strftime(
                    "%Y-%m-%d"
                )
                if post_signal_date
                is not None
                else None
            ),

        "post_event":
            post_event,

        "low_taken_date":
            (
                low_taken_date.strftime(
                    "%Y-%m-%d"
                )
                if low_taken_date
                is not None
                else None
            ),

        "low_reclaim_date":
            (
                low_reclaim_date.strftime(
                    "%Y-%m-%d"
                )
                if low_reclaim_date
                is not None
                else None
            ),

        "high_taken_date":
            (
                high_taken_date.strftime(
                    "%Y-%m-%d"
                )
                if high_taken_date
                is not None
                else None
            ),

        "high_rejection_date":
            (
                high_rejection_date.strftime(
                    "%Y-%m-%d"
                )
                if high_rejection_date
                is not None
                else None
            )
    }


# ============================================================
# FTFC
# ============================================================

def calculate_ftfc(
    df,
    weekly_levels
):

    try:

        current_price = float(
            df["Close"]
            .iloc[-1]
        )

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
        # ALIGNMENT
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
# RVOL
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
            # DATA
            # =================================================

            df = clean_ticker_dataframe(
                market_data,
                ticker
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

            levels = get_weekly_levels(
                df
            )

            if levels is None:

                progress.progress(
                    (index + 1)
                    / total
                )

                continue

            # =================================================
            # LEVELS
            # =================================================

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

            current_week_strat = (
                levels[
                    "current_week_strat"
                ]
            )

            current_price = float(
                df["Close"]
                .iloc[-1]
            )

            # =================================================
            # LEVEL TAKEN
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
            # CURRENT STATUS
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
            # ACTIONABLE SIGNAL HISTORY
            # =================================================

            actionable = (
                find_actionable_signals(
                    df,
                    previous_week_high,
                    previous_week_low
                )
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

            ftfc = calculate_ftfc(
                df,
                levels
            )

            # =================================================
            # RVOL
            # =================================================

            rvol = calculate_rvol(
                df
            )

            # =================================================
            # DISTANCE
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
            # ONLY WEEKLY SWEEPS
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
                    f"PWL Taken → Reclaimed → "
                    f"Daily {daily_strat} → "
                    f"Weekly FTFC Up"
                )

            elif bearish_setup:

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
                # PWL
                # =============================================

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

                # =============================================
                # PWH
                # =============================================

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

                # =============================================
                # CATEGORY 2
                #
                # BEFORE CONFIRMATION
                # =============================================

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

                # =============================================
                # CATEGORY 1
                #
                # AFTER CONFIRMATION
                # =============================================

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

                # =============================================
                # CURRENT DAILY STRAT
                # =============================================

                "Daily STRAT":
                    daily_strat,

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
                # RVOL
                # =============================================

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
# LOAD UNIVERSE
# ============================================================

with st.spinner(
    "Loading S&P 500 universe..."
):

    sp500_tickers = (
        get_sp500_tickers()
    )


# ============================================================
# UNIVERSE
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
        "Actionable Signal",
        [
            "All",
            "Hammer",
            "Shooting Star",
            "Inside Bar"
        ]
    )
)


# ============================================================
# ACTIONABLE CATEGORY
# ============================================================

actionable_category_filter = (
    st.sidebar.selectbox(
        "Actionable Category",
        [
            "All",
            "Pre-Confirmation",
            "Post-Confirmation"
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
# RVOL
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


st.sidebar.metric(
    "Stocks to Scan",
    len(selected_tickers)
)


run_scan = (
    st.sidebar.button(
        "🚀 Scan Market",
        type="primary",
        use_container_width=True
    )
)


# ============================================================
# RUN SCAN
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
    # FILTERS
    # ========================================================

    if not results.empty:

        # WEEKLY SIGNAL
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
                results["Prev Week STRAT"]
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
                results["Current Week STRAT"]
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
                results["Daily STRAT"]
                == daily_strat_filter
            ]

        # ====================================================
        # ACTIONABLE SIGNAL
        # ====================================================

        if actionable_filter != "All":

            if (
                actionable_category_filter
                == "Pre-Confirmation"
            ):

                results = results[
                    results[
                        "First Pre-Confirmation Signal"
                    ]
                    == actionable_filter
                ]

            elif (
                actionable_category_filter
                == "Post-Confirmation"
            ):

                results = results[
                    results[
                        "First Post-Confirmation Signal"
                    ]
                    == actionable_filter
                ]

            else:

                results = results[
                    (
                        results[
                            "First Pre-Confirmation Signal"
                        ]
                        == actionable_filter
                    )
                    |
                    (
                        results[
                            "First Post-Confirmation Signal"
                        ]
                        == actionable_filter
                    )
                ]

        # ====================================================
        # CATEGORY WITHOUT SPECIFIC CANDLE
        # ====================================================

        elif (
            actionable_category_filter
            == "Pre-Confirmation"
        ):

            results = results[
                results[
                    "First Pre-Confirmation Signal"
                ].notna()
            ]

        elif (
            actionable_category_filter
            == "Post-Confirmation"
        ):

            results = results[
                results[
                    "First Post-Confirmation Signal"
                ].notna()
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
            "Pre-Confirm Signals",
            int(
                results[
                    "First Pre-Confirmation Signal"
                ]
                .notna()
                .sum()
            )
        )

        c5.metric(
            "Post-Confirm Signals",
            int(
                results[
                    "First Post-Confirmation Signal"
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

            "Current Week STRAT",

            "Low Taken",

            "Low Sweep Date",

            "Low Reclaimed",

            "Low Reclaim Date",

            "High Taken",

            "High Sweep Date",

            "High Rejected",

            "High Rejection Date",

            # CATEGORY 2
            "First Pre-Confirmation Signal",

            "Pre-Confirmation Date",

            "Pre-Confirmation Event",

            # CATEGORY 1
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
        # POST-CONFIRMATION SIGNALS
        # ====================================================

        confirmed = results[
            results[
                "First Post-Confirmation Signal"
            ].notna()
        ]

        if not confirmed.empty:

            st.subheader(
                "✅ Post-Confirmation Actionable Signals"
            )

            st.caption(
                "First Hammer, Shooting Star or Inside Bar "
                "after a PWL reclaim or PWH rejection."
            )

            st.dataframe(
                confirmed[
                    [
                        "Ticker",
                        "Price",
                        "Post-Confirmation Event",
                        "First Post-Confirmation Signal",
                        "Post-Confirmation Date",
                        "Current Week STRAT",
                        "Daily STRAT",
                        "Weekly FTFC",
                        "RVOL"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # PRE-CONFIRMATION SIGNALS
        # ====================================================

        unconfirmed = results[
            results[
                "First Pre-Confirmation Signal"
            ].notna()
        ]

        if not unconfirmed.empty:

            st.subheader(
                "⚠️ Pre-Confirmation Actionable Signals"
            )

            st.caption(
                "First Hammer, Shooting Star or Inside Bar "
                "after the weekly level was taken but before "
                "a reclaim/rejection occurred."
            )

            st.dataframe(
                unconfirmed[
                    [
                        "Ticker",
                        "Price",
                        "Pre-Confirmation Event",
                        "First Pre-Confirmation Signal",
                        "Pre-Confirmation Date",
                        "Current Week STRAT",
                        "Daily STRAT",
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

            st.dataframe(
                bullish[
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

            st.dataframe(
                bearish[
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
                        "Signal"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

        # ====================================================
        # CSV
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


### ⚠️ Pre-Confirmation Actionable Signal

The scanner starts watching after:

**PWL Taken → Not Yet Reclaimed**

or

**PWH Taken → Not Yet Rejected**

It records the first:

- Hammer
- Shooting Star
- Inside Bar


### ✅ Post-Confirmation Actionable Signal

The scanner separately records the first actionable candle after:

**PWL Taken → Reclaimed**

or

**PWH Taken → Rejected**

Actionable candles:

- Hammer
- Shooting Star
- Inside Bar


### Weekly STRAT

The scanner calculates:

**Previous Week STRAT**

and

**Current Week STRAT**

Available classifications:

- 1 Inside
- 2U Green
- 2U Red
- 2D Green
- 2D Red
- 3 Outside
"""
    )
