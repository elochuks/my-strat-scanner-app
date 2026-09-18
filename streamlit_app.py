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

st.title("📊 S&P 500 Weekly High / Low Scanner")

st.caption(
    "Scans the S&P 500 for stocks that take out the previous "
    "week's high or low."
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
                "The S&P 500 dataset does not contain "
                "a Symbol column."
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
        # BF.B  -> BF-B
        tickers = [
            ticker.replace(".", "-")
            for ticker in tickers
        ]

        tickers = sorted(set(tickers))

        return tickers

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

    # Smaller batches are generally more reliable
    # than requesting the entire S&P 500 at once.
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

            # ------------------------------------------------
            # Multiple symbols
            # ------------------------------------------------

            if len(batch) > 1:

                if not isinstance(
                    data.columns,
                    pd.MultiIndex
                ):
                    continue

                level_zero = (
                    data.columns
                    .get_level_values(0)
                    .unique()
                )

                for ticker in batch:

                    try:

                        if ticker not in level_zero:
                            continue

                        ticker_df = (
                            data[ticker]
                            .copy()
                        )

                        if not ticker_df.empty:
                            all_data[ticker] = ticker_df

                    except Exception:
                        continue

            # ------------------------------------------------
            # Single symbol
            # ------------------------------------------------

            else:

                ticker = batch[0]

                ticker_df = data.copy()

                if isinstance(
                    ticker_df.columns,
                    pd.MultiIndex
                ):

                    ticker_df.columns = (
                        ticker_df.columns
                        .get_level_values(-1)
                    )

                if not ticker_df.empty:
                    all_data[ticker] = ticker_df

        except Exception:
            continue

        # Small pause between Yahoo requests
        time.sleep(0.25)

    return all_data


# ============================================================
# CLEAN TICKER DATA
# ============================================================

def clean_ticker_dataframe(data, ticker):

    try:

        if ticker not in data:
            return None

        df = data[ticker].copy()

        # Flatten columns if necessary
        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = (
                df.columns
                .get_level_values(-1)
            )

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

        # Convert everything to numeric
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

        # Remove timezone if Yahoo returns one
        try:
            df.index = df.index.tz_localize(None)
        except Exception:
            pass

        df = df.sort_index()

        return df

    except Exception:

        return None


# ============================================================
# WEEKLY LEVELS
# ============================================================

def get_weekly_levels(df):

    if df is None or len(df) < 10:
        return None

    temp = df.copy()

    # W-FRI gives trading weeks ending Friday.
    temp["Week"] = (
        temp.index.to_period("W-FRI")
    )

    weekly = temp.groupby(
        "Week"
    ).agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        Volume=("Volume", "sum")
    )

    if len(weekly) < 2:
        return None

    # Current trading week
    current_week_period = (
        temp["Week"].iloc[-1]
    )

    current_week_data = temp[
        temp["Week"]
        == current_week_period
    ].copy()

    # All weeks before current week
    previous_weeks = weekly[
        weekly.index
        < current_week_period
    ]

    if previous_weeks.empty:
        return None

    # Most recent completed week
    previous_week = (
        previous_weeks.iloc[-1]
    )

    return {

        "previous_week_high":
            float(
                previous_week["High"]
            ),

        "previous_week_low":
            float(
                previous_week["Low"]
            ),

        "previous_week_open":
            float(
                previous_week["Open"]
            ),

        "previous_week_close":
            float(
                previous_week["Close"]
            ),

        "current_week_open":
            float(
                current_week_data[
                    "Open"
                ].iloc[0]
            ),

        "current_week_high":
            float(
                current_week_data[
                    "High"
                ].max()
            ),

        "current_week_low":
            float(
                current_week_data[
                    "Low"
                ].min()
            ),

        "current_week_close":
            float(
                current_week_data[
                    "Close"
                ].iloc[-1]
            ),

        "current_week":
            str(
                current_week_period
            )
    }


# ============================================================
# DAILY STRAT PATTERN
# ============================================================

def get_daily_strat(df):

    if df is None or len(df) < 2:
        return "N/A"

    previous = df.iloc[-2]
    current = df.iloc[-1]

    previous_high = float(
        previous["High"]
    )

    previous_low = float(
        previous["Low"]
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

    # --------------------------------------------------------
    # Outside bar
    # --------------------------------------------------------

    if (
        current_high > previous_high
        and
        current_low < previous_low
    ):

        return "3 Outside"

    # --------------------------------------------------------
    # Inside bar
    # --------------------------------------------------------

    if (
        current_high <= previous_high
        and
        current_low >= previous_low
    ):

        return "1 Inside"

    # --------------------------------------------------------
    # Directional up
    # --------------------------------------------------------

    if current_high > previous_high:

        if current_close >= current_open:
            return "2U Green"

        return "2U Red"

    # --------------------------------------------------------
    # Directional down
    # --------------------------------------------------------

    if current_low < previous_low:

        if current_close >= current_open:
            return "2D Green"

        return "2D Red"

    return "N/A"


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

        # ----------------------------------------------------
        # WEEKLY
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # MONTHLY
        # ----------------------------------------------------

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

            if (
                current_price
                > monthly_open
            ):

                monthly_ftfc = "Up"

            elif (
                current_price
                < monthly_open
            ):

                monthly_ftfc = "Down"

            else:

                monthly_ftfc = (
                    "Neutral"
                )

        # ----------------------------------------------------
        # M + W ALIGNMENT
        # ----------------------------------------------------

        if (
            weekly_ftfc == "Up"
            and
            monthly_ftfc == "Up"
        ):

            ftfc = "FTFC Up"

        elif (
            weekly_ftfc == "Down"
            and
            monthly_ftfc == "Down"
        ):

            ftfc = "FTFC Down"

        else:

            ftfc = "Mixed"

        return {

            "weekly":
                weekly_ftfc,

            "monthly":
                monthly_ftfc,

            "alignment":
                ftfc,

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
# FIND EXACT SWEEP DATE
# ============================================================

def find_sweep_dates(
    df,
    previous_week_high,
    previous_week_low
):

    temp = df.copy()

    current_period = (
        temp.index[-1]
        .to_period("W-FRI")
    )

    current_week = temp[
        temp.index.to_period(
            "W-FRI"
        )
        == current_period
    ]

    high_sweep_date = None
    low_sweep_date = None

    # --------------------------------------------------------
    # Find first day that took the level
    # --------------------------------------------------------

    for date, row in (
        current_week.iterrows()
    ):

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

    for index, ticker in enumerate(
        tickers
    ):

        status.text(
            f"Scanning {ticker} "
            f"({index + 1}/{total})"
        )

        try:

            # ------------------------------------------------
            # DATA
            # ------------------------------------------------

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

            # ------------------------------------------------
            # WEEKLY LEVELS
            # ------------------------------------------------

            levels = get_weekly_levels(
                df
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
                df["Close"].iloc[-1]
            )

            # ------------------------------------------------
            # SWEEP LOGIC
            # ------------------------------------------------

            high_taken = (
                current_week_high
                > previous_week_high
            )

            low_taken = (
                current_week_low
                < previous_week_low
            )

            # ------------------------------------------------
            # RECLAIM / REJECTION
            # ------------------------------------------------

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

            # ------------------------------------------------
            # SWEEP DATE
            # ------------------------------------------------

            (
                low_sweep_date,
                high_sweep_date
            ) = find_sweep_dates(

                df,
                previous_week_high,
                previous_week_low
            )

            # ------------------------------------------------
            # DAILY STRAT
            # ------------------------------------------------

            daily_strat = (
                get_daily_strat(df)
            )

            # ------------------------------------------------
            # FTFC
            # ------------------------------------------------

            ftfc = calculate_ftfc(
                df,
                levels
            )

            # ------------------------------------------------
            # RVOL
            # ------------------------------------------------

            rvol = calculate_rvol(df)

            # ------------------------------------------------
            # DISTANCE
            # ------------------------------------------------

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

            # ------------------------------------------------
            # COMPOSITE BULLISH
            # ------------------------------------------------

            bullish_setup = (

                low_taken

                and low_reclaimed

                and daily_strat
                == "2U Green"

                and ftfc["weekly"]
                == "Up"
            )

            # ------------------------------------------------
            # COMPOSITE BEARISH
            # ------------------------------------------------

            bearish_setup = (

                high_taken

                and high_rejected

                and daily_strat
                == "2D Red"

                and ftfc["weekly"]
                == "Down"
            )

            # ------------------------------------------------
            # ONLY RETURN SWEEPS
            # ------------------------------------------------

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

            # ------------------------------------------------
            # SIGNAL
            # ------------------------------------------------

            if bullish_setup:

                signal = (
                    "PWL Taken → "
                    "Reclaimed → "
                    "Daily 2U Green → "
                    "Weekly FTFC Up"
                )

            elif bearish_setup:

                signal = (
                    "PWH Taken → "
                    "Rejected → "
                    "Daily 2D Red → "
                    "Weekly FTFC Down"
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

            # ------------------------------------------------
            # RESULT
            # ------------------------------------------------

            results.append({

                "Ticker":
                    ticker,

                "Price":
                    round(
                        current_price,
                        2
                    ),

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

                "Low Taken":
                    low_taken,

                "Low Sweep Date":
                    low_sweep_date,

                "Low Reclaimed":
                    low_reclaimed,

                "High Taken":
                    high_taken,

                "High Sweep Date":
                    high_sweep_date,

                "High Rejected":
                    high_rejected,

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
                        pct_from_low,
                        2
                    ),

                "% From PWH":
                    round(
                        pct_from_high,
                        2
                    ),

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

universe = st.sidebar.selectbox(

    "Market Universe",

    [
        "S&P 500",
        "Custom Watchlist"
    ]
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
                "Separate symbols "
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
# SIGNAL FILTER
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
# DAILY STRAT FILTER
# ============================================================

strat_filter = (
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
# UNIVERSE COUNT
# ============================================================

st.sidebar.metric(
    "Stocks to Scan",
    len(selected_tickers)
)


# ============================================================
# RUN BUTTON
# ============================================================

run_scan = st.sidebar.button(

    "🚀 Scan Market",

    type="primary",

    use_container_width=True
)


# ============================================================
# MAIN
# ============================================================

if run_scan:

    if not selected_tickers:

        st.error(
            "No ticker symbols available."
        )

        st.stop()

    # ========================================================
    # DOWNLOAD MARKET DATA
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
            "Yahoo Finance did not return "
            "market data. Try again shortly."
        )

        st.stop()

    st.caption(
        f"Successfully downloaded "
        f"{len(market_data)} / "
        f"{len(selected_tickers)} symbols."
    )

    # ========================================================
    # RUN SCANNER
    # ========================================================

    results = scan_market(
        selected_tickers,
        market_data
    )

    # ========================================================
    # APPLY FILTERS
    # ========================================================

    if not results.empty:

        if (
            signal_filter
            == "Previous Week Low Taken"
        ):

            results = results[
                results[
                    "Low Taken"
                ]
            ]

        elif (
            signal_filter
            == "Previous Week High Taken"
        ):

            results = results[
                results[
                    "High Taken"
                ]
            ]

        elif (
            signal_filter
            == "Low Taken + Reclaimed"
        ):

            results = results[
                results[
                    "Low Reclaimed"
                ]
            ]

        elif (
            signal_filter
            == "High Taken + Rejected"
        ):

            results = results[
                results[
                    "High Rejected"
                ]
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
                results[
                    "Bullish Setup"
                ]
            ]

        elif (
            signal_filter
            == "Bearish STRAT Setup"
        ):

            results = results[
                results[
                    "Bearish Setup"
                ]
            ]

        # FTFC
        if ftfc_filter != "All":

            results = results[
                results["FTFC"]
                == ftfc_filter
            ]

        # STRAT
        if strat_filter != "All":

            results = results[
                results["Daily STRAT"]
                == strat_filter
            ]

        # RVOL
        if minimum_rvol > 0:

            results = results[
                results["RVOL"]
                .fillna(0)
                >= minimum_rvol
            ]


    # ========================================================
    # RESULTS
    # ========================================================

    st.divider()

    if results.empty:

        st.warning(
            "No stocks matched "
            "your selected conditions."
        )

    else:

        # ====================================================
        # METRICS
        # ====================================================

        c1, c2, c3, c4 = (
            st.columns(4)
        )

        c1.metric(
            "Total Matches",
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

        composite_count = int(
            results[
                "Bullish Setup"
            ].sum()
            +
            results[
                "Bearish Setup"
            ].sum()
        )

        c4.metric(
            "STRAT Setups",
            composite_count
        )

        # ====================================================
        # SORT RESULTS
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
        # MAIN RESULTS TABLE
        # ====================================================

        st.subheader(
            "🔎 Scanner Results"
        )

        display_columns = [

            "Ticker",

            "Price",

            "Prev Week Low",

            "Prev Week High",

            "Current Week Low",

            "Current Week High",

            "Low Taken",

            "Low Sweep Date",

            "Low Reclaimed",

            "High Taken",

            "High Sweep Date",

            "High Rejected",

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
        # BULLISH SETUPS
        # ====================================================

        bullish = results[
            results[
                "Bullish Setup"
            ]
        ]

        if not bullish.empty:

            st.subheader(
                "🟢 Bullish Setups"
            )

            st.dataframe(

                bullish[
                    [
                        "Ticker",
                        "Price",
                        "Prev Week Low",
                        "Low Sweep Date",
                        "Daily STRAT",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "RVOL"
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
                "🔴 Bearish Setups"
            )

            st.dataframe(

                bearish[
                    [
                        "Ticker",
                        "Price",
                        "Prev Week High",
                        "High Sweep Date",
                        "Daily STRAT",
                        "Weekly FTFC",
                        "Monthly FTFC",
                        "RVOL"
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
            .to_csv(index=False)
            .encode("utf-8")
        )

        st.download_button(

            "⬇️ Download Scanner Results",

            data=csv,

            file_name=(
                "sp500_weekly_sweep_scanner.csv"
            ),

            mime="text/csv",

            use_container_width=True
        )


# ============================================================
# HOME SCREEN
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
### Scanner

The scanner looks through the **S&P 500** for stocks
interacting with the previous completed week's range.

#### 🟢 Bullish sequence

**Previous Week Low Taken**

↓

**Previous Week Low Reclaimed**

↓

**Daily 2U Green**

↓

**Weekly FTFC Up**


#### 🔴 Bearish sequence

**Previous Week High Taken**

↓

**Previous Week High Rejected**

↓

**Daily 2D Red**

↓

**Weekly FTFC Down**


### Weekly sweep definition

A previous-week low is considered taken when:

`Current Week Low < Previous Week Low`

A previous-week high is considered taken when:

`Current Week High > Previous Week High`

The scanner remembers a sweep that occurred earlier in the
current week. For example, if a stock takes the previous week's
low on Monday and rallies above it by Friday, it will still be
reported as having taken the weekly low.
"""
    )
