import streamlit as st
import yfinance as yf
import pandas as pd
import traceback

st.set_page_config(page_title="STRAT Scanner - DEBUG MODE", layout="wide")

st.title("🔍 STRAT Scanner - Diagnostic Version")
st.warning("This version has extensive debugging to find the 3-month issue")

# =====================================================
# DIAGNOSTIC FUNCTIONS
# =====================================================

def diagnose_yfinance():
    """Check yfinance version and basic functionality"""
    try:
        import yfinance
        version = yfinance.__version__
        st.success(f"yfinance version: {version}")
        return True
    except Exception as e:
        st.error(f"yfinance import error: {e}")
        return False

def test_single_ticker(ticker, interval, period):
    """Test downloading a single ticker and return detailed diagnostics"""
    result = {
        "success": False,
        "candles": 0,
        "columns": None,
        "error": None,
        "sample_data": None
    }
    
    try:
        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True
        )
        
        result["success"] = True
        result["candles"] = len(data)
        result["columns"] = str(data.columns.tolist())
        result["is_multiindex"] = isinstance(data.columns, pd.MultiIndex)
        
        if len(data) > 0:
            result["sample_data"] = data.tail(1).to_dict()
            
    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    
    return result

# =====================================================
# SIDEBAR DIAGNOSTICS
# =====================================================

st.sidebar.header("Diagnostics")

if st.sidebar.button("Test yfinance Installation"):
    diagnose_yfinance()

st.sidebar.markdown("---")

# Test single ticker
test_ticker = st.sidebar.text_input("Test Ticker", "AAPL")
test_interval = st.sidebar.selectbox("Test Interval", ["1d", "1wk", "1mo", "3mo"])
test_period = st.sidebar.selectbox("Test Period", ["1y", "5y", "10y", "max"])

if st.sidebar.button("Run Single Test"):
    with st.spinner(f"Testing {test_ticker}..."):
        result = test_single_ticker(test_ticker, test_interval, test_period)
        
        st.sidebar.subheader("Results")
        if result["success"]:
            st.sidebar.success(f"✓ Success - {result['candles']} candles")
            st.sidebar.write(f"Columns: {result['columns']}")
            st.sidebar.write(f"MultiIndex: {result['is_multiindex']}")
        else:
            st.sidebar.error(f"✗ Failed: {result['error']}")
            if "traceback" in result:
                with st.sidebar.expander("Traceback"):
                    st.code(result["traceback"])

# =====================================================
# MAIN SCANNER (ULTRA-SIMPLE VERSION)
# =====================================================

st.header("Ultra-Simple STRAT Scanner")

# Just use a few tickers for testing
test_tickers = st.multiselect(
    "Select Tickers to Test",
    ["AAPL", "MSFT", "SPY", "QQQ", "TSLA", "AMZN", "GOOGL"],
    default=["AAPL", "SPY"]
)

timeframe = st.selectbox("Timeframe", ["Daily", "Weekly", "Monthly", "3-Month"])

interval_map = {
    "Daily": ("1d", "1y"),
    "Weekly": ("1wk", "2y"), 
    "Monthly": ("1mo", "5y"),
    "3-Month": ("3mo", "max")  # MUST use max for 3mo
}

run_scan = st.button("Run Simple Scan", type="primary")

if run_scan:
    interval, period = interval_map[timeframe]
    
    st.write(f"**Settings:** Interval={interval}, Period={period}")
    
    results = []
    
    for ticker in test_tickers:
        with st.expander(f"Processing {ticker}", expanded=True):
            try:
                # Step 1: Download
                st.write("1. Downloading...")
                data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
                st.write(f"   ✓ Downloaded {len(data)} rows")
                
                if len(data) == 0:
                    st.error("   ✗ No data returned!")
                    continue
                
                # Step 2: Check structure
                st.write("2. Checking structure...")
                st.write(f"   Columns: {data.columns.tolist()}")
                st.write(f"   MultiIndex: {isinstance(data.columns, pd.MultiIndex)}")
                
                # Step 3: Get last candles
                st.write("3. Getting candles...")
                
                if len(data) < 2:
                    st.error(f"   ✗ Need at least 2 candles, got {len(data)}")
                    continue
                
                # For 3mo, we work with 2 candles
                if timeframe == "3-Month":
                    curr = data.iloc[-1]
                    prev = data.iloc[-2]
                    
                    # Show raw values
                    st.write("   Current candle:", curr.to_dict())
                    st.write("   Previous candle:", prev.to_dict())
                    
                    # Simple STRAT logic (no MultiIndex handling first)
                    try:
                        curr_close = float(curr["Close"])
                        curr_open = float(curr["Open"])
                        curr_high = float(curr["High"])
                        curr_low = float(curr["Low"])
                        prev_high = float(prev["High"])
                        prev_low = float(prev["Low"])
                        
                        st.write(f"   ✓ Extracted values: Close={curr_close}, Open={curr_open}")
                        
                        # Determine pattern
                        if curr_high < prev_high and curr_low > prev_low:
                            pattern = "1 (Inside)"
                        elif curr_high > prev_high and curr_low < prev_low:
                            pattern = "3 (Outside)"
                        elif curr_high > prev_high:
                            color = "Green" if curr_close >= curr_open else "Red"
                            pattern = f"2U {color}"
                        elif curr_low < prev_low:
                            color = "Green" if curr_close >= curr_open else "Red"
                            pattern = f"2D {color}"
                        else:
                            pattern = "Undefined"
                        
                        st.success(f"   ✓ Pattern: {pattern}")
                        
                        results.append({
                            "Ticker": ticker,
                            "Pattern": pattern,
                            "Close": round(curr_close, 2),
                            "Direction": "Up" if curr_close > curr_open else "Down"
                        })
                        
                    except Exception as e:
                        st.error(f"   ✗ Value extraction failed: {e}")
                        # Try MultiIndex approach
                        if isinstance(data.columns, pd.MultiIndex):
                            st.write("   Trying MultiIndex extraction...")
                            try:
                                curr_close = float(curr[("Close", ticker)])
                                curr_open = float(curr[("Open", ticker)])
                                st.write(f"   ✓ MultiIndex worked! Close={curr_close}")
                            except Exception as e2:
                                st.error(f"   ✗ MultiIndex also failed: {e2}")
                
                else:
                    # Regular 3-candle logic for other timeframes
                    if len(data) < 3:
                        st.error(f"   ✗ Need 3 candles for {timeframe}, got {len(data)}")
                        continue
                    
                    # ... (similar logic for other timeframes)
                    st.write("   (Using 3-candle logic)")
                    
            except Exception as e:
                st.error(f"✗ Major error: {e}")
                st.code(traceback.format_exc())
    
    # Show results
    if results:
        st.success(f"Found {len(results)} results")
        st.dataframe(pd.DataFrame(results))
    else:
        st.error("No results - check expanders above for errors")

# =====================================================
# TROUBLESHOOTING GUIDE
# =====================================================

st.markdown("---")
st.header("Common 3-Month Issues & Solutions")

issues = {
    "No data returned (0 candles)": """
    - Try changing period to "max" instead of "5y"
    - Some tickers don't have 20+ years of history
    - Test with SPY or AAPL first (they have long history)
    """,
    
    "KeyError on column access": """
    - yfinance now returns MultiIndex columns: ('Close', 'AAPL') instead of 'Close'
    - The code tries both flat and MultiIndex, but may fail on some versions
    - Update yfinance: pip install yfinance --upgrade
    """,
    
    "ValueError or type errors": """
    - Data might contain NaN values
    - Check if market was open during the period
    - Try auto_adjust=True/False
    """,
    
    "Patterns all show 'Undefined'": """
    - With 3mo candles, price action is compressed
    - Inside/Outside bars are rare on quarterly timeframe
    - This might be correct behavior - try with "max" period to get more history
    """
}

for issue, solution in issues.items():
    with st.expander(issue):
        st.markdown(solution)

st.markdown("---")
st.info("💡 **Tip**: Start with Daily timeframe to verify the scanner works, then try 3-Month")
