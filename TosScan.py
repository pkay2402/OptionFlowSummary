import streamlit as st
import imaplib
import email
import re
import datetime
import pandas as pd
from dateutil import parser
import yfinance as yf
import time
from bs4 import BeautifulSoup
from functools import lru_cache
import logging
from concurrent.futures import ThreadPoolExecutor
from streamlit_extras.buy_me_a_coffee import button

# Initialize session state at the very beginning
def init_session_state():
    if 'processed_email_ids' not in st.session_state:
        st.session_state['processed_email_ids'] = set()
    if 'last_refresh_time' not in st.session_state:
        st.session_state['last_refresh_time'] = time.time()

# Call initialization immediately
init_session_state()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 600  # 10 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Define keywords for Intraday_timeframe and daily scans
Intraday_timeframe_KEYWORDS = ["Long_VP", "Short_VP", "orb_bull", "orb_bear", "volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short"]
DAILY_KEYWORDS = ["Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"]

# Keyword definitions with added risk levels and descriptions
KEYWORD_DEFINITIONS = {
    "Long_VP": {
        "description": "Volume Profile based long signal.",
        "risk_level": "Medium",
        "timeframe": "2 weeks",
        "suggested_stop": "Below the volume node"
    },
    "Short_VP": {
        "description": "Volume Profile based short signal.",
        "risk_level": "Medium",
        "timeframe": "2 weeks",
        "suggested_stop": "Above the volume node"
    }
    "orb_bull": {
        "description": "10 mins 9 ema crossed above opening range high of 30mins",
        "risk_level": "high",
        "timeframe": "Intrday",
        "suggested_stop": "Below the ORB high"
    }
}

@lru_cache(maxsize=2)
def get_spy_qqq_prices():
    """Fetch the latest closing prices for SPY and QQQ with caching."""
    try:
        spy = yf.Ticker("SPY")
        qqq = yf.Ticker("QQQ")
        
        spy_price = round(spy.history(period="1d")['Close'].iloc[-1], 2)
        qqq_price = round(qqq.history(period="1d")['Close'].iloc[-1], 2)
        
        return spy_price, qqq_price
    except Exception as e:
        logger.error(f"Error fetching market prices: {e}")
        return None, None

def connect_to_email(retries=MAX_RETRIES):
    """Establish email connection with retry logic."""
    for attempt in range(retries):
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            return mail
        except Exception as e:
            if attempt == retries - 1:
                raise
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY)

def parse_email_body(msg):
    """Parse email body with better HTML handling."""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() in ["text/plain", "text/html"]:
                    body = part.get_payload(decode=True).decode()
                    if part.get_content_type() == "text/html":
                        soup = BeautifulSoup(body, "html.parser", from_encoding='utf-8')
                        return soup.get_text(separator=' ', strip=True)
                    return body
        else:
            body = msg.get_payload(decode=True).decode()
            if msg.get_content_type() == "text/html":
                soup = BeautifulSoup(body, "html.parser", from_encoding='utf-8')
                return soup.get_text(separator=' ', strip=True)
            return body
    except Exception as e:
        logger.error(f"Error parsing email body: {e}")
        return ""

def extract_stock_symbols_from_email(email_address, password, sender_email, keyword, days_lookback):
    """Extract stock symbols with improved error handling and performance."""
    try:
        mail = connect_to_email()
        mail.select('inbox')

        date_since = (datetime.date.today() - datetime.timedelta(days=days_lookback)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{sender_email}" SUBJECT "{keyword}" SINCE "{date_since}")'
        _, data = mail.search(None, search_criteria)

        stock_data = []
        
        # Process each email
        for num in data[0].split():
            if num in st.session_state['processed_email_ids']:
                continue

            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            email_date = parser.parse(msg['Date']).date()
            
            if email_date.weekday() >= 5:  # Skip weekends
                continue

            body = parse_email_body(msg)
            symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*(' + re.escape(keyword) + ')', body)
            
            if symbols:
                for symbol_group in symbols:
                    extracted_symbols = symbol_group[0].replace(" ", "").split(",")
                    signal_type = symbol_group[1]
                    for symbol in extracted_symbols:
                        if symbol.isalpha():  # Basic symbol validation
                            stock_data.append([symbol, email_date, signal_type])
            
            st.session_state['processed_email_ids'].add(num)

        mail.close()
        mail.logout()

        if stock_data:
            df = pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal'])
            df = df.sort_values(by=['Date', 'Ticker']).drop_duplicates(subset=['Ticker'], keep='last')
            return df

        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

    except Exception as e:
        logger.error(f"Error in extract_stock_symbols_from_email: {e}")
        st.error(f"Error processing emails: {str(e)}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

def main():
    st.set_page_config(
        page_title="Thinkorswim Alerts Analyzer",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 Thinkorswim Alerts Analyzer")
    
    # Add sidebar for settings
    with st.sidebar:
        st.header("Settings")
        days_lookback = st.slider(
            "Days to Look Back",
            min_value=1,
            max_value=3,
            value=1,
            help="Choose how many days of historical alerts to analyze"
        )
        
        # Add auto-refresh option
        auto_refresh = st.checkbox("Enable Auto-refresh", value=False)
        if auto_refresh:
            refresh_interval = st.slider("Refresh Interval (minutes)", 1, 30, 10)
        
        # Buy Me a Coffee Button in sidebar
        st.markdown("---")
        button(username="tosalerts33", floating=False, width=221)

    # Market data
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        spy_price, qqq_price = get_spy_qqq_prices()
        if spy_price and qqq_price:
            st.metric("SPY Latest", f"${spy_price}")
    with col2:
        if spy_price and qqq_price:
            st.metric("QQQ Latest", f"${qqq_price}")
    with col3:
        if st.button("🔄 Refresh Data"):
            st.session_state['processed_email_ids'].clear()
            st.rerun()

    # Auto-refresh logic
    if auto_refresh and st.session_state['last_refresh_time']:
        time_since_refresh = time.time() - st.session_state['last_refresh_time']
        if time_since_refresh >= refresh_interval * 60:
            st.session_state['processed_email_ids'].clear()
            st.session_state['last_refresh_time'] = time.time()
            st.rerun()

    # Scan type selection
    section = st.radio("Select Scan Type", ["Intraday_timeframe", "Daily"], index=0, horizontal=True)
    selected_keywords = Intraday_timeframe_KEYWORDS if section == "Intraday_timeframe" else DAILY_KEYWORDS
    
    st.subheader(f"{section} Scans")
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Individual Scans", "Combined View"])
    
    with tab1:
        for keyword in selected_keywords:
            with st.expander(f"📊 {keyword}", expanded=False):
                info = KEYWORD_DEFINITIONS.get(keyword, {})
                if info:
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.info(f"Risk Level: {info.get('risk_level', 'N/A')}")
                    with col2:
                        st.info(f"Timeframe: {info.get('timeframe', 'N/A')}")
                    with col3:
                        st.info(f"Suggested Stop: {info.get('suggested_stop', 'N/A')}")
                
                symbols_df = extract_stock_symbols_from_email(
                    EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword, days_lookback
                )
                
                if not symbols_df.empty:
                    st.dataframe(symbols_df, use_container_width=True)
                    csv = symbols_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"📥 Download {keyword} Data",
                        data=csv,
                        file_name=f"{keyword}_alerts_{datetime.date.today()}.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning(f"No signals found for {keyword} in the last {days_lookback} day(s).")
    
    with tab2:
        # Combine all signals into one view
        all_signals = []
        for keyword in selected_keywords:
            df = extract_stock_symbols_from_email(
                EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword, days_lookback
            )
            if not df.empty:
                all_signals.append(df)
        
        if all_signals:
            combined_df = pd.concat(all_signals, ignore_index=True)
            combined_df = combined_df.sort_values(['Date', 'Ticker'], ascending=[False, True])
            
            st.dataframe(combined_df, use_container_width=True)
            
            csv = combined_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Combined Data",
                data=csv,
                file_name=f"combined_alerts_{datetime.date.today()}.csv",
                mime="text/csv",
            )
        else:
            st.warning(f"No signals found in the last {days_lookback} day(s).")

    # Update last refresh time
    st.session_state['last_refresh_time'] = time.time()
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center'>
            <p><strong>Disclaimer:</strong> This tool is for informational purposes only and does not constitute financial advice. 
            Trade at your own risk.</p>
            <p>Last updated: {}</p>
        </div>
        """.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
