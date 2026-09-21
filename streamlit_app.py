# ============================================================
# LOAD UNIVERSES
# ============================================================

with st.spinner("Loading market universes..."):

    sp500_tickers = get_sp500_tickers()
    nasdaq100_tickers = get_nasdaq100_tickers()
    etf_tickers = get_etf_tickers()


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

st.sidebar.header("⚙️ Market Settings")


universe = st.sidebar.selectbox(
    "Market Universe",
    [
        "S&P 500 + Nasdaq-100 + ETFs",
        "S&P 500",
        "Nasdaq-100",
        "Market + Sector ETFs",
        "Custom Watchlist"
    ],
    key="sidebar_market_universe"
)


if universe == "S&P 500 + Nasdaq-100 + ETFs":

    selected_tickers = combined_tickers

elif universe == "S&P 500":

    selected_tickers = sp500_tickers

elif universe == "Nasdaq-100":

    selected_tickers = nasdaq100_tickers

elif universe == "Market + Sector ETFs":

    selected_tickers = etf_tickers

else:

    custom = st.sidebar.text_area(
        "Custom Tickers",
        value=(
            "AAPL,MSFT,NVDA,AMD,"
            "TSLA,AMZN,META,SPY,"
            "QQQ,IWM"
        ),
        key="sidebar_custom_watchlist"
    )

    selected_tickers = sorted(
        set(
            ticker
            .strip()
            .upper()
            .replace(".", "-")

            for ticker in custom.split(",")

            if ticker.strip()
        )
    )


# ============================================================
# SIDEBAR STATISTICS
# ============================================================

st.sidebar.divider()

st.sidebar.caption("Universe Statistics")


s1, s2 = st.sidebar.columns(2)

s1.metric(
    "S&P 500",
    len(sp500_tickers)
)

s2.metric(
    "Nasdaq-100",
    len(nasdaq100_tickers)
)


s3, s4 = st.sidebar.columns(2)

s3.metric(
    "ETFs",
    len(etf_tickers)
)

s4.metric(
    "Duplicates",
    duplicate_count
)


st.sidebar.metric(
    "Scanner Universe",
    len(selected_tickers)
)


with st.sidebar.expander(
    "📈 ETFs Included"
):

    st.write(
        """
**Broad Market**

SPY — S&P 500  
QQQ — Nasdaq-100  
IWM — Russell 2000

**Sectors**

XLC — Communication Services  
XLY — Consumer Discretionary  
XLP — Consumer Staples  
XLE — Energy  
XLF — Financials  
XLV — Health Care  
XLI — Industrials  
XLB — Materials  
XLRE — Real Estate  
XLK — Technology  
XLU — Utilities
"""
    )


# ============================================================
# SESSION STATE
# ============================================================

if "market_data" not in st.session_state:
    st.session_state.market_data = None


if "loaded_universe" not in st.session_state:
    st.session_state.loaded_universe = None


if "weekly_results_raw" not in st.session_state:
    st.session_state.weekly_results_raw = None


if "monthly_results_raw" not in st.session_state:
    st.session_state.monthly_results_raw = None


# ============================================================
# LOAD MARKET DATA
# ============================================================

load_market = st.sidebar.button(
    "📥 Load Market Data",
    type="primary",
    use_container_width=True,
    key="sidebar_load_market_data"
)


if load_market:

    download_tickers = sorted(
        set(
            selected_tickers
            + MARKET_CONTEXT_TICKERS
        )
    )

    with st.spinner(
        f"Downloading 1 year of market data "
        f"for {len(download_tickers)} symbols..."
    ):

        market_data = download_market_data(
            download_tickers
        )

        st.session_state.market_data = (
            market_data
        )

        st.session_state.loaded_universe = (
            tuple(selected_tickers)
        )

        # Clear old scans because universe changed/reloaded
        st.session_state.weekly_results_raw = None
        st.session_state.monthly_results_raw = None

    if market_data:

        st.sidebar.success(
            f"Loaded data for "
            f"{len(market_data)} symbols."
        )

    else:

        st.sidebar.error(
            "No market data was downloaded."
        )


# ============================================================
# MARKET READY
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
        "**📥 Load Market Data**."
    )


# ============================================================
# TABS
# ============================================================

weekly_tab, monthly_tab, market_context_tab = st.tabs(
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
        "Previous Week High/Low → Sweep → "
        "Reclaim/Reject → Daily STRAT → "
        "Weekly FTFC"
    )

    # --------------------------------------------------------
    # WEEKLY FILTER ROW 1
    # --------------------------------------------------------

    w1, w2, w3, w4 = st.columns(4)


    weekly_signal_filter = w1.selectbox(
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


    weekly_strat_filter = w2.selectbox(
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
        key="weekly_current_week_strat_filter"
    )


    daily_filter = w3.selectbox(
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
        key="weekly_daily_strat_filter"
    )


    weekly_actionable_filter = w4.selectbox(
        "Actionable Candle",
        [
            "All",
            "Hammer",
            "Shooting Star",
            "Inside Bar"
        ],
        key="weekly_actionable_candle_filter"
    )


    # --------------------------------------------------------
    # WEEKLY FILTER ROW 2
    # --------------------------------------------------------

    w5, w6, w7 = st.columns(3)


    weekly_category = w5.selectbox(
        "Actionable Category",
        [
            "All",
            "Pre-Confirmation",
            "Post-Confirmation"
        ],
        key="weekly_actionable_category_filter"
    )


    weekly_min_rvol = w6.number_input(
        "Minimum RVOL",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.1,
        key="weekly_minimum_rvol"
    )


    weekly_min_atr = w7.number_input(
        "Minimum ATR %",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.1,
        key="weekly_minimum_atr_pct"
    )


    # --------------------------------------------------------
    # RUN WEEKLY
    # --------------------------------------------------------

    run_weekly = st.button(
        "🚀 Run Weekly Scanner",
        type="primary",
        use_container_width=True,
        key="run_weekly_scanner_button"
    )


    if run_weekly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            st.session_state.weekly_results_raw = (
                scan_weekly(
                    selected_tickers,
                    st.session_state.market_data
                )
            )


    # ========================================================
    # DISPLAY WEEKLY RESULTS
    # ========================================================

    if (
        st.session_state.weekly_results_raw
        is not None
    ):

        weekly_results = (
            st.session_state.weekly_results_raw
            .copy()
        )


        # ----------------------------------------------------
        # WEEKLY SIGNAL FILTER
        # ----------------------------------------------------

        if (
            weekly_signal_filter
            == "PWL Taken"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "Low Taken"
                ]
            ]


        elif (
            weekly_signal_filter
            == "PWH Taken"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "High Taken"
                ]
            ]


        elif (
            weekly_signal_filter
            == "PWL Reclaimed"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "Low Reclaimed"
                ]
            ]


        elif (
            weekly_signal_filter
            == "PWH Rejected"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "High Rejected"
                ]
            ]


        elif (
            weekly_signal_filter
            == "Bullish Setup"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "Bullish Setup"
                ]
            ]


        elif (
            weekly_signal_filter
            == "Bearish Setup"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "Bearish Setup"
                ]
            ]


        # ----------------------------------------------------
        # CURRENT WEEK STRAT FILTER
        # ----------------------------------------------------

        if (
            weekly_strat_filter
            != "All"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "Current Week STRAT"
                ]
                == weekly_strat_filter
            ]


        # ----------------------------------------------------
        # DAILY STRAT FILTER
        # ----------------------------------------------------

        if (
            daily_filter
            != "All"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "Daily STRAT"
                ]
                == daily_filter
            ]


        # ----------------------------------------------------
        # ACTIONABLE CANDLE + CATEGORY
        # ----------------------------------------------------

        if (
            weekly_actionable_filter
            != "All"
        ):

            if (
                weekly_category
                == "Pre-Confirmation"
            ):

                weekly_results = weekly_results[
                    weekly_results[
                        "First Pre-Confirmation Signal"
                    ]
                    == weekly_actionable_filter
                ]


            elif (
                weekly_category
                == "Post-Confirmation"
            ):

                weekly_results = weekly_results[
                    weekly_results[
                        "First Post-Confirmation Signal"
                    ]
                    == weekly_actionable_filter
                ]


            else:

                weekly_results = weekly_results[
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


        elif (
            weekly_category
            == "Pre-Confirmation"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "First Pre-Confirmation Signal"
                ]
                .notna()
            ]


        elif (
            weekly_category
            == "Post-Confirmation"
        ):

            weekly_results = weekly_results[
                weekly_results[
                    "First Post-Confirmation Signal"
                ]
                .notna()
            ]


        # ----------------------------------------------------
        # RVOL FILTER
        # ----------------------------------------------------

        if weekly_min_rvol > 0:

            weekly_results = weekly_results[
                weekly_results[
                    "RVOL"
                ]
                .fillna(0)
                >= weekly_min_rvol
            ]


        # ----------------------------------------------------
        # ATR % FILTER
        # ----------------------------------------------------

        if weekly_min_atr > 0:

            weekly_results = weekly_results[
                weekly_results[
                    "ATR %"
                ]
                .fillna(0)
                >= weekly_min_atr
            ]


        # ----------------------------------------------------
        # WEEKLY OUTPUT
        # ----------------------------------------------------

        if weekly_results.empty:

            st.warning(
                "No weekly signals matched "
                "the current filters."
            )

        else:

            weekly_results = (
                weekly_results
                .sort_values(
                    [
                        "Bullish Setup",
                        "Bearish Setup",
                        "ATR %",
                        "RVOL"
                    ],
                    ascending=[
                        False,
                        False,
                        False,
                        False
                    ],
                    na_position="last"
                )
            )


            # ------------------------------------------------
            # WEEKLY METRICS
            # ------------------------------------------------

            wc1, wc2, wc3, wc4, wc5 = (
                st.columns(5)
            )


            wc1.metric(
                "Matches",
                len(weekly_results)
            )


            wc2.metric(
                "PWL Taken",
                int(
                    weekly_results[
                        "Low Taken"
                    ].sum()
                )
            )


            wc3.metric(
                "PWH Taken",
                int(
                    weekly_results[
                        "High Taken"
                    ].sum()
                )
            )


            wc4.metric(
                "Bullish",
                int(
                    weekly_results[
                        "Bullish Setup"
                    ].sum()
                )
            )


            wc5.metric(
                "Bearish",
                int(
                    weekly_results[
                        "Bearish Setup"
                    ].sum()
                )
            )


            # ------------------------------------------------
            # ALL WEEKLY RESULTS
            # ------------------------------------------------

            st.subheader(
                "🔎 Weekly Scanner Results"
            )

            st.dataframe(
                weekly_results,
                use_container_width=True,
                hide_index=True
            )


            # ------------------------------------------------
            # POST CONFIRMATION
            # ------------------------------------------------

            weekly_post = weekly_results[
                weekly_results[
                    "First Post-Confirmation Signal"
                ]
                .notna()
            ]


            if not weekly_post.empty:

                st.subheader(
                    "✅ Weekly Post-Confirmation Signals"
                )

                weekly_post_columns = [
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
                    "Signal"
                ]

                weekly_post_columns = [
                    column
                    for column
                    in weekly_post_columns
                    if column in weekly_post.columns
                ]

                st.dataframe(
                    weekly_post[
                        weekly_post_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # PRE CONFIRMATION
            # ------------------------------------------------

            weekly_pre = weekly_results[
                weekly_results[
                    "First Pre-Confirmation Signal"
                ]
                .notna()
            ]


            if not weekly_pre.empty:

                st.subheader(
                    "⚠️ Weekly Pre-Confirmation Signals"
                )

                weekly_pre_columns = [
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
                    "Signal"
                ]

                weekly_pre_columns = [
                    column
                    for column
                    in weekly_pre_columns
                    if column in weekly_pre.columns
                ]

                st.dataframe(
                    weekly_pre[
                        weekly_pre_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # BULLISH WEEKLY
            # ------------------------------------------------

            weekly_bullish = weekly_results[
                weekly_results[
                    "Bullish Setup"
                ]
            ]


            if not weekly_bullish.empty:

                st.subheader(
                    "🟢 Bullish Weekly Setups"
                )

                bullish_columns = [
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
                    "Signal"
                ]

                bullish_columns = [
                    column
                    for column
                    in bullish_columns
                    if column in weekly_bullish.columns
                ]

                st.dataframe(
                    weekly_bullish[
                        bullish_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # BEARISH WEEKLY
            # ------------------------------------------------

            weekly_bearish = weekly_results[
                weekly_results[
                    "Bearish Setup"
                ]
            ]


            if not weekly_bearish.empty:

                st.subheader(
                    "🔴 Bearish Weekly Setups"
                )

                bearish_columns = [
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
                    "Signal"
                ]

                bearish_columns = [
                    column
                    for column
                    in bearish_columns
                    if column in weekly_bearish.columns
                ]

                st.dataframe(
                    weekly_bearish[
                        bearish_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # WEEKLY CSV
            # ------------------------------------------------

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
                file_name="weekly_strat_scanner.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_weekly_results_csv"
            )


# ============================================================
# MONTHLY TAB
# ============================================================

with monthly_tab:

    st.header(
        "🗓️ Monthly Sweep Scanner"
    )

    st.caption(
        "Previous Month High/Low → Sweep → "
        "Reclaim/Reject → Weekly STRAT → "
        "Monthly FTFC"
    )


    # --------------------------------------------------------
    # MONTHLY FILTER ROW 1
    # --------------------------------------------------------

    m1, m2, m3, m4 = st.columns(4)


    monthly_signal_filter = m1.selectbox(
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


    month_strat_filter = m2.selectbox(
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
        key="monthly_current_month_strat_filter"
    )


    # THIS WAS THE WIDGET CAUSING YOUR ERROR.
    # IT NOW HAS ITS OWN UNIQUE KEY.

    month_weekly_filter = m3.selectbox(
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
        key="monthly_current_week_strat_filter"
    )


    monthly_actionable_filter = m4.selectbox(
        "Weekly Actionable Signal",
        [
            "All",
            "Hammer",
            "Shooting Star",
            "Inside Bar"
        ],
        key="monthly_weekly_actionable_filter"
    )


    # --------------------------------------------------------
    # MONTHLY FILTER ROW 2
    # --------------------------------------------------------

    m5, m6, m7 = st.columns(3)


    monthly_category = m5.selectbox(
        "Actionable Category",
        [
            "All",
            "Pre-Confirmation",
            "Post-Confirmation"
        ],
        key="monthly_actionable_category_filter"
    )


    monthly_min_rvol = m6.number_input(
        "Minimum RVOL",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.1,
        key="monthly_minimum_rvol"
    )


    monthly_min_atr = m7.number_input(
        "Minimum ATR %",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.1,
        key="monthly_minimum_atr_pct"
    )


    # --------------------------------------------------------
    # RUN MONTHLY
    # --------------------------------------------------------

    run_monthly = st.button(
        "🚀 Run Monthly Scanner",
        type="primary",
        use_container_width=True,
        key="run_monthly_scanner_button"
    )


    if run_monthly:

        if not market_ready:

            st.warning(
                "Load market data first."
            )

        else:

            st.session_state.monthly_results_raw = (
                scan_monthly(
                    selected_tickers,
                    st.session_state.market_data
                )
            )


    # ========================================================
    # DISPLAY MONTHLY RESULTS
    # ========================================================

    if (
        st.session_state.monthly_results_raw
        is not None
    ):

        monthly_results = (
            st.session_state.monthly_results_raw
            .copy()
        )


        # ----------------------------------------------------
        # MONTHLY SIGNAL FILTER
        # ----------------------------------------------------

        if (
            monthly_signal_filter
            == "PML Taken"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "Low Taken"
                ]
            ]


        elif (
            monthly_signal_filter
            == "PMH Taken"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "High Taken"
                ]
            ]


        elif (
            monthly_signal_filter
            == "PML Reclaimed"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "Low Reclaimed"
                ]
            ]


        elif (
            monthly_signal_filter
            == "PMH Rejected"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "High Rejected"
                ]
            ]


        elif (
            monthly_signal_filter
            == "Bullish Setup"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "Bullish Setup"
                ]
            ]


        elif (
            monthly_signal_filter
            == "Bearish Setup"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "Bearish Setup"
                ]
            ]


        # ----------------------------------------------------
        # CURRENT MONTH STRAT FILTER
        # ----------------------------------------------------

        if (
            month_strat_filter
            != "All"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "Current Month STRAT"
                ]
                == month_strat_filter
            ]


        # ----------------------------------------------------
        # CURRENT WEEK STRAT FILTER
        # ----------------------------------------------------

        if (
            month_weekly_filter
            != "All"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "Current Week STRAT"
                ]
                == month_weekly_filter
            ]


        # ----------------------------------------------------
        # MONTHLY ACTIONABLE FILTER
        # ----------------------------------------------------

        if (
            monthly_actionable_filter
            != "All"
        ):

            if (
                monthly_category
                == "Pre-Confirmation"
            ):

                monthly_results = monthly_results[
                    monthly_results[
                        "First Pre-Confirmation Weekly Signal"
                    ]
                    == monthly_actionable_filter
                ]


            elif (
                monthly_category
                == "Post-Confirmation"
            ):

                monthly_results = monthly_results[
                    monthly_results[
                        "First Post-Confirmation Weekly Signal"
                    ]
                    == monthly_actionable_filter
                ]


            else:

                monthly_results = monthly_results[
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


        elif (
            monthly_category
            == "Pre-Confirmation"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "First Pre-Confirmation Weekly Signal"
                ]
                .notna()
            ]


        elif (
            monthly_category
            == "Post-Confirmation"
        ):

            monthly_results = monthly_results[
                monthly_results[
                    "First Post-Confirmation Weekly Signal"
                ]
                .notna()
            ]


        # ----------------------------------------------------
        # MONTHLY RVOL FILTER
        # ----------------------------------------------------

        if monthly_min_rvol > 0:

            monthly_results = monthly_results[
                monthly_results[
                    "RVOL"
                ]
                .fillna(0)
                >= monthly_min_rvol
            ]


        # ----------------------------------------------------
        # MONTHLY ATR FILTER
        # ----------------------------------------------------

        if monthly_min_atr > 0:

            monthly_results = monthly_results[
                monthly_results[
                    "ATR %"
                ]
                .fillna(0)
                >= monthly_min_atr
            ]


        # ----------------------------------------------------
        # MONTHLY OUTPUT
        # ----------------------------------------------------

        if monthly_results.empty:

            st.warning(
                "No monthly signals matched "
                "the current filters."
            )

        else:

            monthly_results = (
                monthly_results
                .sort_values(
                    [
                        "Bullish Setup",
                        "Bearish Setup",
                        "ATR %",
                        "RVOL"
                    ],
                    ascending=[
                        False,
                        False,
                        False,
                        False
                    ],
                    na_position="last"
                )
            )


            # ------------------------------------------------
            # MONTHLY METRICS
            # ------------------------------------------------

            mc1, mc2, mc3, mc4, mc5 = (
                st.columns(5)
            )


            mc1.metric(
                "Matches",
                len(monthly_results)
            )


            mc2.metric(
                "PML Taken",
                int(
                    monthly_results[
                        "Low Taken"
                    ].sum()
                )
            )


            mc3.metric(
                "PMH Taken",
                int(
                    monthly_results[
                        "High Taken"
                    ].sum()
                )
            )


            mc4.metric(
                "Bullish",
                int(
                    monthly_results[
                        "Bullish Setup"
                    ].sum()
                )
            )


            mc5.metric(
                "Bearish",
                int(
                    monthly_results[
                        "Bearish Setup"
                    ].sum()
                )
            )


            # ------------------------------------------------
            # ALL MONTHLY
            # ------------------------------------------------

            st.subheader(
                "🔎 Monthly Scanner Results"
            )


            st.dataframe(
                monthly_results,
                use_container_width=True,
                hide_index=True
            )


            # ------------------------------------------------
            # POST CONFIRMATION
            # ------------------------------------------------

            monthly_post = monthly_results[
                monthly_results[
                    "First Post-Confirmation Weekly Signal"
                ]
                .notna()
            ]


            if not monthly_post.empty:

                st.subheader(
                    "✅ Monthly Post-Confirmation Signals"
                )

                monthly_post_columns = [
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
                    "Signal"
                ]

                monthly_post_columns = [
                    column
                    for column
                    in monthly_post_columns
                    if column in monthly_post.columns
                ]

                st.dataframe(
                    monthly_post[
                        monthly_post_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # PRE CONFIRMATION
            # ------------------------------------------------

            monthly_pre = monthly_results[
                monthly_results[
                    "First Pre-Confirmation Weekly Signal"
                ]
                .notna()
            ]


            if not monthly_pre.empty:

                st.subheader(
                    "⚠️ Monthly Pre-Confirmation Signals"
                )

                monthly_pre_columns = [
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
                    "Signal"
                ]

                monthly_pre_columns = [
                    column
                    for column
                    in monthly_pre_columns
                    if column in monthly_pre.columns
                ]

                st.dataframe(
                    monthly_pre[
                        monthly_pre_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # BULLISH MONTHLY
            # ------------------------------------------------

            monthly_bullish = monthly_results[
                monthly_results[
                    "Bullish Setup"
                ]
            ]


            if not monthly_bullish.empty:

                st.subheader(
                    "🟢 Bullish Monthly Setups"
                )

                monthly_bullish_columns = [
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
                    "Signal"
                ]

                monthly_bullish_columns = [
                    column
                    for column
                    in monthly_bullish_columns
                    if column in monthly_bullish.columns
                ]

                st.dataframe(
                    monthly_bullish[
                        monthly_bullish_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # BEARISH MONTHLY
            # ------------------------------------------------

            monthly_bearish = monthly_results[
                monthly_results[
                    "Bearish Setup"
                ]
            ]


            if not monthly_bearish.empty:

                st.subheader(
                    "🔴 Bearish Monthly Setups"
                )

                monthly_bearish_columns = [
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
                    "Signal"
                ]

                monthly_bearish_columns = [
                    column
                    for column
                    in monthly_bearish_columns
                    if column in monthly_bearish.columns
                ]

                st.dataframe(
                    monthly_bearish[
                        monthly_bearish_columns
                    ],
                    use_container_width=True,
                    hide_index=True
                )


            # ------------------------------------------------
            # MONTHLY CSV
            # ------------------------------------------------

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
                file_name="monthly_strat_scanner.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_monthly_results_csv"
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

        context_df = build_market_context(
            st.session_state.market_data
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


            for ticker, column in index_cards:

                card = context_df[
                    context_df[
                        "Ticker"
                    ]
                    == ticker
                ]


                if card.empty:
                    continue


                row = card.iloc[0]


                return5 = row[
                    "5D Return %"
                ]


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
                    delta
                )


                atr_value = row[
                    "ATR %"
                ]


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
                    f'ATR: {atr_text} | '
                    f'W: {row["Weekly FTFC"]} | '
                    f'M: {row["Monthly FTFC"]}'
                )


            # =================================================
            # MAJOR MARKET CONTEXT
            # =================================================

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
                        "^VIX"
                    ]
                )
            ].copy()


            major_columns = [
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
                "ATR %"
            ]


            major_columns = [
                column
                for column
                in major_columns
                if column in major.columns
            ]


            st.dataframe(
                major[
                    major_columns
                ],
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # SECTOR ETF CONTEXT
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


            sectors = context_df[
                context_df[
                    "Ticker"
                ]
                .isin(
                    sector_tickers
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
                        na_position="last"
                    )
                )


            sector_columns = [
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
                "ATR %"
            ]


            sector_columns = [
                column
                for column
                in sector_columns
                if column in sectors.columns
            ]


            st.dataframe(
                sectors[
                    sector_columns
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


            rs_columns = [
                "Ticker",
                "Market",
                "5D Return %",
                "20D Return %",
                "20D RS vs SPY",
                "ATR %",
                "Weekly FTFC",
                "Monthly FTFC",
                "Current Week STRAT",
                "Current Month STRAT"
            ]


            rs_columns = [
                column
                for column
                in rs_columns
                if column in sectors.columns
            ]


            sector_rs = sectors[
                rs_columns
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
                        na_position="last"
                    )
                )


            st.dataframe(
                sector_rs,
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # MARKET TREND BREADTH
            # =================================================

            st.subheader(
                "📈 Market Trend Breadth"
            )


            equity_context = context_df[
                context_df[
                    "Ticker"
                ]
                != "^VIX"
            ].copy()


            total_assets = len(
                equity_context
            )


            above20 = (
                int(
                    equity_context[
                        "Above MA20"
                    ]
                    .sum()
                )
                if (
                    "Above MA20"
                    in equity_context.columns
                )
                else 0
            )


            above50 = (
                int(
                    equity_context[
                        "Above MA50"
                    ]
                    .sum()
                )
                if (
                    "Above MA50"
                    in equity_context.columns
                )
                else 0
            )


            above200 = (
                int(
                    equity_context[
                        "Above MA200"
                    ]
                    .sum()
                )
                if (
                    "Above MA200"
                    in equity_context.columns
                )
                else 0
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


            weekly_context_columns = [
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
                "ATR %"
            ]


            weekly_context_columns = [
                column
                for column
                in weekly_context_columns
                if column in context_df.columns
            ]


            st.dataframe(
                context_df[
                    weekly_context_columns
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


            monthly_context_columns = [
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
                "ATR %"
            ]


            monthly_context_columns = [
                column
                for column
                in monthly_context_columns
                if column in context_df.columns
            ]


            st.dataframe(
                context_df[
                    monthly_context_columns
                ],
                use_container_width=True,
                hide_index=True
            )


            # =================================================
            # MARKET CONTEXT DOWNLOAD
            # =================================================

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
                file_name="market_context.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_market_context_csv"
            )
