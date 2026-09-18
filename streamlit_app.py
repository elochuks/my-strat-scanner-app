import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Weekly High / Low STRAT Scanner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Weekly High / Low STRAT Scanner")

st.caption(
    "Find stocks that take out the previous week's high or low, "
    "reclaim/reject the level, and identify STRAT + FTFC conditions."
)


# ============================================================
# TICKER UNIVERSE
# ============================================================

@st.cache_data(ttl=86400)
def get_tickers():

    # --------------------------------------------------------
    # Starter universe
    #
    # This intentionally does NOT scrape Wikipedia.
    # Add/remove symbols as desired.
    # --------------------------------------------------------

    tickers = [

        # Mega / Large Cap
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "GOOG", "META", "TSLA", "AVGO", "BRK-B",
        "LLY", "JPM", "V", "MA", "WMT",
        "XOM", "COST", "NFLX", "ORCL", "HD",

        # Technology
        "AMD", "INTC", "QCOM", "MU", "AMAT",
        "LRCX", "KLAC", "MRVL", "ADI", "TXN",
        "CRM", "NOW", "ADBE", "PANW", "CRWD",
        "PLTR", "SNOW", "DDOG", "NET", "MDB",

        # Financial
        "BAC", "WFC", "GS", "MS", "C",
        "SCHW", "AXP", "COF", "BLK", "SPGI",

        # Consumer
        "NKE", "SBUX", "MCD", "TGT", "LOW",
        "TJX", "ROST", "CMG", "BKNG", "ABNB",

        # Healthcare
        "UNH", "JNJ", "ABBV", "MRK", "PFE",
        "TMO", "AMGN", "GILD", "ISRG", "VRTX",

        # Industrial
        "CAT", "DE", "GE", "HON", "UPS",
        "FDX", "BA", "RTX", "LMT", "MMM",

        # Energy
        "CVX", "COP", "SLB", "EOG", "OXY",

        # Communication / Media
        "DIS", "CMCSA", "T", "VZ", "TMUS",

        # Popular Trading Names
        "COIN", "HOOD", "RBLX", "SOFI", "SHOP",
        "UBER", "DASH", "RIVN", "LCID",

        # ETFs
        "SPY", "QQQ", "IWM", "DIA",
        "XLK", "XLF", "XLE", "XLV",
        "XLY", "XLP", "XLI", "XLU",
        "SMH", "ARKK", "TLT", "GLD"
    ]

    return sorted(list(set(tickers)))


# ============================================================
# DOWNLOAD DATA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_market_data(tickers):

    if not tickers:
        return pd.DataFrame()

    try:

        data = yf.download(
            tickers=tickers,
            period="6mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=True,
            progress=False
        )

        return data

    except Exception as e:

        st.error(f"Market data download failed: {e}")

        return pd.DataFrame()


# ============================================================
# GET INDIVIDUAL TICKER DATA
# ============================================================

def get_ticker_dataframe(data, ticker, total_tickers):

    try:

        # Multiple ticker download
        if total_tickers > 1:

            if ticker not in data.columns.get_level_values(0):
                return None

            df = data[ticker].copy()

        # Single ticker download
        else:

            df = data.copy()

        # Flatten columns if necessary
        if isinstance(df.columns, pd.MultiIndex):

            df.columns = df.columns.get_level_values(-1)

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for col in required_columns:

            if col not in df.columns:
                return None

        df = df[required_columns]

        df = df.dropna(
            subset=["Open", "High", "Low", "Close"]
        )

        df.index = pd.to_datetime(df.index)

        return df

    except Exception:

        return None


# ============================================================
# WEEK IDENTIFICATION
# ============================================================

def add_week_columns(df):

    df = df.copy()

    # Monday is start of week
    df["Week"] = df.index.to_period("W-FRI")

    return df


# ============================================================
# PREVIOUS WEEK LEVELS
# ============================================================

def get_weekly_levels(df):

    df = add_week_columns(df)

    weekly = df.groupby("Week").agg({

        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"

    })

    if len(weekly) < 2:
        return None

    current_week_period = df["Week"].iloc[-1]

    current_week_data = df[
        df["Week"] == current_week_period
    ]

    previous_weeks = weekly[
        weekly.index < current_week_period
    ]

    if previous_weeks.empty:
        return None

    previous_week = previous_weeks.iloc[-1]

    return {

        "previous_week_high":
            float(previous_week["High"]),

        "previous_week_low":
            float(previous_week["Low"]),

        "previous_week_open":
            float(previous_week["Open"]),

        "previous_week_close":
            float(previous_week["Close"]),

        "current_week_high":
            float(current_week_data["High"].max()),

        "current_week_low":
            float(current_week_data["Low"].min()),

        "current_week_open":
            float(current_week_data["Open"].iloc[0]),

        "current_week_close":
            float(current_week_data["Close"].iloc[-1]),

        "current_week_period":
            str(current_week_period),

        "current_week_data":
            current_week_data
    }


# ============================================================
# DAILY STRAT
# ============================================================

def get_daily_strat(df):

    if len(df) < 2:
        return None

    previous = df.iloc[-2]

    current = df.iloc[-1]

    previous_high = float(previous["High"])
    previous_low = float(previous["Low"])

    current_open = float(current["Open"])
    current_high = float(current["High"])
    current_low = float(current["Low"])
    current_close = float(current["Close"])

    # --------------------------------------------------------
    # STRAT candle type
    # --------------------------------------------------------

    if (
        current_high < previous_high
        and current_low > previous_low
    ):

        pattern = "1 Inside"

    elif (
        current_high > previous_high
        and current_low < previous_low
    ):

        pattern = "3 Outside"

    elif current_high > previous_high:

        if current_close >= current_open:
            pattern = "2U Green"
        else:
            pattern = "2U Red"

    elif current_low < previous_low:

        if current_close >= current_open:
            pattern = "2D Green"
        else:
            pattern = "2D Red"

    else:

        pattern = "Undefined"

    return {

        "pattern": pattern,

        "previous_day_high":
            previous_high,

        "previous_day_low":
            previous_low,

        "current_day_high":
            current_high,

        "current_day_low":
            current_low,

        "current_day_open":
            current_open,

        "current_day_close":
            current_close
    }


# ============================================================
# FTFC
# ============================================================

def calculate_ftfc(df, weekly_levels):

    try:

        current_price = float(
            df["Close"].iloc[-1]
        )

        # ----------------------------------------------------
        # Weekly FTFC
        #
        # Current price relative to current weekly open
        # ----------------------------------------------------

        weekly_open = weekly_levels[
            "current_week_open"
        ]

        if current_price > weekly_open:

            weekly_ftfc = "Up"

        elif current_price < weekly_open:

            weekly_ftfc = "Down"

        else:

            weekly_ftfc = "Neutral"


        # ----------------------------------------------------
        # Monthly FTFC
        # ----------------------------------------------------

        current_month = df.index[-1].to_period("M")

        month_data = df[
            df.index.to_period("M") == current_month
        ]

        if month_data.empty:

            monthly_ftfc = "N/A"
            monthly_open = None

        else:

            monthly_open = float(
                month_data["Open"].iloc[0]
            )

            if current_price > monthly_open:

                monthly_ftfc = "Up"

            elif current_price < monthly_open:

                monthly_ftfc = "Down"

            else:

                monthly_ftfc = "Neutral"


        # ----------------------------------------------------
        # M + W FTFC
        # ----------------------------------------------------

        if (
            weekly_ftfc == "Up"
            and monthly_ftfc == "Up"
        ):

            ftfc = "FTFC Up"

        elif (
            weekly_ftfc == "Down"
            and monthly_ftfc == "Down"
        ):

            ftfc = "FTFC Down"

        else:

            ftfc = "Mixed"


        return {

            "weekly_ftfc":
                weekly_ftfc,

            "monthly_ftfc":
                monthly_ftfc,

            "ftfc":
                ftfc,

            "weekly_open":
                weekly_open,

            "monthly_open":
                monthly_open
        }

    except Exception:

        return {

            "weekly_ftfc": "N/A",
            "monthly_ftfc": "N/A",
            "ftfc": "N/A",
            "weekly_open": None,
            "monthly_open": None
        }


# ============================================================
# RELATIVE VOLUME
# ============================================================

def calculate_relative_volume(df, lookback=20):

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

        if average_volume == 0:
            return None

        return current_volume / average_volume

    except Exception:

        return None


# ============================================================
# MAIN SCANNER
# ============================================================

def scan_market(tickers, data):

    results = []

    total_tickers = len(tickers)

    progress_bar = st.progress(0)

    status = st.empty()

    for i, ticker in enumerate(tickers):

        status.text(
            f"Scanning {ticker} "
            f"({i + 1}/{total_tickers})"
        )

        try:

            df = get_ticker_dataframe(
                data,
                ticker,
                total_tickers
            )

            if df is None or len(df) < 30:

                progress_bar.progress(
                    (i + 1) / total_tickers
                )

                continue


            # =================================================
            # WEEKLY LEVELS
            # =================================================

            weekly_levels = get_weekly_levels(df)

            if weekly_levels is None:

                progress_bar.progress(
                    (i + 1) / total_tickers
                )

                continue


            previous_week_high = weekly_levels[
                "previous_week_high"
            ]

            previous_week_low = weekly_levels[
                "previous_week_low"
            ]

            current_week_high = weekly_levels[
                "current_week_high"
            ]

            current_week_low = weekly_levels[
                "current_week_low"
            ]


            current_price = float(
                df["Close"].iloc[-1]
            )


            # =================================================
            # HIGH / LOW TAKEN
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
                and current_price
                > previous_week_low
            )

            high_rejected = (
                high_taken
                and current_price
                < previous_week_high
            )


            # =================================================
            # DISTANCE FROM LEVEL
            # =================================================

            low_distance_pct = (
                (
                    current_price
                    - previous_week_low
                )
                / previous_week_low
            ) * 100


            high_distance_pct = (
                (
                    current_price
                    - previous_week_high
                )
                / previous_week_high
            ) * 100


            # =================================================
            # DAILY STRAT
            # =================================================

            daily_strat = get_daily_strat(df)

            if daily_strat:

                daily_pattern = daily_strat[
                    "pattern"
                ]

            else:

                daily_pattern = "N/A"


            # =================================================
            # FTFC
            # =================================================

            ftfc_data = calculate_ftfc(
                df,
                weekly_levels
            )

            weekly_ftfc = ftfc_data[
                "weekly_ftfc"
            ]

            monthly_ftfc = ftfc_data[
                "monthly_ftfc"
            ]

            ftfc = ftfc_data[
                "ftfc"
            ]


            # =================================================
            # RELATIVE VOLUME
            # =================================================

            rvol = calculate_relative_volume(df)

            if rvol is not None:
                rvol_display = round(rvol, 2)
            else:
                rvol_display = None


            # =================================================
            # BULLISH COMPOSITE SETUP
            # =================================================

            bullish_setup = (

                low_taken
                and low_reclaimed
                and daily_pattern == "2U Green"
                and weekly_ftfc == "Up"

            )


            # =================================================
            # BEARISH COMPOSITE SETUP
            # =================================================

            bearish_setup = (

                high_taken
                and high_rejected
                and daily_pattern == "2D Red"
                and weekly_ftfc == "Down"

            )


            # =================================================
            # SIGNAL
            # =================================================

            if bullish_setup:

                signal = (
                    "Previous Week Low Taken → "
                    "Reclaimed → "
                    "Daily 2U Green → "
                    "Weekly FTFC Up"
                )

            elif bearish_setup:

                signal = (
                    "Previous Week High Taken → "
                    "Rejected → "
                    "Daily 2D Red → "
                    "Weekly FTFC Down"
                )

            elif low_reclaimed:

                signal = (
                    "Previous Week Low "
                    "Taken → Reclaimed"
                )

            elif high_rejected:

                signal = (
                    "Previous Week High "
                    "Taken → Rejected"
                )

            elif low_taken and high_taken:

                signal = "Both Weekly Levels Taken"

            elif low_taken:

                signal = "Previous Week Low Taken"

            elif high_taken:

                signal = "Previous Week High Taken"

            else:

                # We only want stocks that interacted
                # with previous weekly levels
                progress_bar.progress(
                    (i + 1) / total_tickers
                )

                continue


            # =================================================
            # ADD RESULT
            # =================================================

            results.append({

                "Ticker":
                    ticker,

                "Price":
                    round(current_price, 2),

                "Prev Week High":
                    round(previous_week_high, 2),

                "Prev Week Low":
                    round(previous_week_low, 2),

                "Current Week High":
                    round(current_week_high, 2),

                "Current Week Low":
                    round(current_week_low, 2),

                "High Taken":
                    high_taken,

                "Low Taken":
                    low_taken,

                "High Rejected":
                    high_rejected,

                "Low Reclaimed":
                    low_reclaimed,

                "Daily STRAT":
                    daily_pattern,

                "Weekly FTFC":
                    weekly_ftfc,

                "Monthly FTFC":
                    monthly_ftfc,

                "FTFC":
                    ftfc,

                "RVOL":
                    rvol_display,

                "% From Prev Low":
                    round(low_distance_pct, 2),

                "% From Prev High":
                    round(high_distance_pct, 2),

                "Bullish Setup":
                    bullish_setup,

                "Bearish Setup":
                    bearish_setup,

                "Signal":
                    signal

            })


        except Exception:

            pass


        progress_bar.progress(
            (i + 1) / total_tickers
        )


    progress_bar.empty()

    status.empty()

    return pd.DataFrame(results)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Scanner Settings")

all_tickers = get_tickers()


# ============================================================
# UNIVERSE
# ============================================================

universe = st.sidebar.selectbox(

    "Market Universe",

    [
        "Default Universe",
        "Custom Watchlist"
    ]

)


if universe == "Custom Watchlist":

    custom_input = st.sidebar.text_area(

        "Enter tickers",

        value="AAPL,MSFT,NVDA,AMD,TSLA",

        help=(
            "Separate symbols using commas. "
            "Example: AAPL, MSFT, NVDA"
        )

    )

    selected_tickers = [

        x.strip().upper()

        for x in custom_input.split(",")

        if x.strip()

    ]

else:

    selected_tickers = all_tickers


# ============================================================
# SIGNAL FILTER
# ============================================================

signal_filter = st.sidebar.selectbox(

    "Signal",

    [
        "All Weekly Sweeps",

        "Previous Week Low Taken",

        "Previous Week High Taken",

        "Low Taken + Reclaimed",

        "High Taken + Rejected",

        "Bullish STRAT Setup",

        "Bearish STRAT Setup",

        "Both Weekly Levels Taken"
    ]

)


# ============================================================
# FTFC FILTER
# ============================================================

ftfc_filter = st.sidebar.selectbox(

    "FTFC Filter",

    [
        "All",
        "FTFC Up",
        "FTFC Down",
        "Mixed"
    ]

)


# ============================================================
# DAILY STRAT FILTER
# ============================================================

strat_filter = st.sidebar.selectbox(

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


# ============================================================
# RVOL FILTER
# ============================================================

minimum_rvol = st.sidebar.number_input(

    "Minimum RVOL",

    min_value=0.0,

    max_value=10.0,

    value=0.0,

    step=0.1

)


# ============================================================
# DISPLAY UNIVERSE SIZE
# ============================================================

st.sidebar.metric(
    "Stocks to Scan",
    len(selected_tickers)
)


# ============================================================
# RUN SCANNER
# ============================================================

run_scan = st.sidebar.button(
    "🚀 Run Scanner",
    type="primary",
    use_container_width=True
)


# ============================================================
# MAIN APP
# ============================================================

if run_scan:

    if not selected_tickers:

        st.error(
            "Please enter at least one ticker."
        )

        st.stop()


    # ========================================================
    # DOWNLOAD
    # ========================================================

    with st.spinner(
        f"Downloading data for "
        f"{len(selected_tickers)} symbols..."
    ):

        market_data = download_market_data(
            selected_tickers
        )


    if market_data.empty:

        st.error(
            "No market data was downloaded. "
            "Try again in a few minutes."
        )

        st.stop()


    # ========================================================
    # SCAN
    # ========================================================

    results = scan_market(
        selected_tickers,
        market_data
    )


    # ========================================================
    # FILTER RESULTS
    # ========================================================

    if not results.empty:


        if signal_filter == "Previous Week Low Taken":

            results = results[
                results["Low Taken"] == True
            ]


        elif signal_filter == "Previous Week High Taken":

            results = results[
                results["High Taken"] == True
            ]


        elif signal_filter == "Low Taken + Reclaimed":

            results = results[
                results["Low Reclaimed"] == True
            ]


        elif signal_filter == "High Taken + Rejected":

            results = results[
                results["High Rejected"] == True
            ]


        elif signal_filter == "Bullish STRAT Setup":

            results = results[
                results["Bullish Setup"] == True
            ]


        elif signal_filter == "Bearish STRAT Setup":

            results = results[
                results["Bearish Setup"] == True
            ]


        elif signal_filter == "Both Weekly Levels Taken":

            results = results[
                (
                    results["Low Taken"] == True
                )
                &
                (
                    results["High Taken"] == True
                )
            ]


        # ====================================================
        # FTFC FILTER
        # ====================================================

        if ftfc_filter != "All":

            results = results[
                results["FTFC"] == ftfc_filter
            ]


        # ====================================================
        # STRAT FILTER
        # ====================================================

        if strat_filter != "All":

            results = results[
                results["Daily STRAT"]
                == strat_filter
            ]


        # ====================================================
        # RVOL FILTER
        # ====================================================

        if minimum_rvol > 0:

            results = results[
                results["RVOL"].fillna(0)
                >= minimum_rvol
            ]


    # ========================================================
    # RESULTS
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

        col1, col2, col3, col4 = st.columns(4)


        col1.metric(
            "Matches",
            len(results)
        )


        col2.metric(
            "Weekly Lows Taken",
            int(
                results[
                    "Low Taken"
                ].sum()
            )
        )


        col3.metric(
            "Weekly Highs Taken",
            int(
                results[
                    "High Taken"
                ].sum()
            )
        )


        col4.metric(
            "Composite Setups",
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


        # ====================================================
        # SORT
        # ====================================================

        results = results.sort_values(

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


        # ====================================================
        # TABLE
        # ====================================================

        st.subheader("Scanner Results")


        display_columns = [

            "Ticker",

            "Price",

            "Prev Week Low",

            "Prev Week High",

            "Current Week Low",

            "Current Week High",

            "Low Taken",

            "Low Reclaimed",

            "High Taken",

            "High Rejected",

            "Daily STRAT",

            "Weekly FTFC",

            "Monthly FTFC",

            "FTFC",

            "RVOL",

            "% From Prev Low",

            "% From Prev High",

            "Signal"

        ]


        st.dataframe(

            results[display_columns],

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

                "% From Prev Low":
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),

                "% From Prev High":
                    st.column_config.NumberColumn(
                        format="%.2f%%"
                    )

            }

        )


        # ====================================================
        # COMPOSITE SETUPS
        # ====================================================

        bullish = results[
            results["Bullish Setup"] == True
        ]


        bearish = results[
            results["Bearish Setup"] == True
        ]


        if not bullish.empty:

            st.subheader(
                "🟢 Bullish STRAT Setups"
            )

            for _, row in bullish.iterrows():

                st.success(

                    f"{row['Ticker']} — "
                    f"Previous Week Low Taken → "
                    f"Reclaimed → "
                    f"Daily 2U Green → "
                    f"Weekly FTFC Up"
                )


        if not bearish.empty:

            st.subheader(
                "🔴 Bearish STRAT Setups"
            )

            for _, row in bearish.iterrows():

                st.error(

                    f"{row['Ticker']} — "
                    f"Previous Week High Taken → "
                    f"Rejected → "
                    f"Daily 2D Red → "
                    f"Weekly FTFC Down"
                )


        # ====================================================
        # DOWNLOAD CSV
        # ====================================================

        csv = results.to_csv(
            index=False
        ).encode("utf-8")


        st.download_button(

            label="⬇️ Download Results",

            data=csv,

            file_name=(
                "weekly_strat_scanner_results.csv"
            ),

            mime="text/csv",

            use_container_width=True

        )


# ============================================================
# INITIAL SCREEN
# ============================================================

else:

    st.info(
        "Configure the scanner in the sidebar "
        "and click **Run Scanner**."
    )

    st.markdown(
        """
### Scanner Logic

**Bullish setup**

`Previous Week Low Taken → Reclaimed → Daily 2U Green → Weekly FTFC Up`

**Bearish setup**

`Previous Week High Taken → Rejected → Daily 2D Red → Weekly FTFC Down`

### Definitions

**Previous Week Low Taken**

Current week's low trades below the completed previous week's low.

**Previous Week High Taken**

Current week's high trades above the completed previous week's high.

**Low Reclaimed**

The previous week's low was taken and price is now back above it.

**High Rejected**

The previous week's high was taken and price is now back below it.

**Weekly FTFC Up**

Current price is above the current week's open.

**Weekly FTFC Down**

Current price is below the current week's open.
"""
    )
