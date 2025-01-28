import streamlit as st
from streamlit_extras.buy_me_a_coffee import button
import imaplib
import email
import re
import datetime
import pandas as pd
from dateutil import parser
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from functools import lru_cache

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 900  # 15 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"
KEYWORDS = ["volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short", "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"]
processed_email_ids = set()  # Track processed email IDs
TOOLTIPS = { ... }  # Same as original script

@lru_cache(maxsize=32)
def get_ticker_data(ticker):
    """Fetch data for a specific stock ticker using yfinance."""
    return yf.Ticker(ticker)

def batch_fetch_prices(tickers):
    """Batch fetch stock prices for multiple tickers."""
    data = {}
    try:
        tickers_data = yf.download(tickers, period="1d", group_by="ticker", progress=False)
        for ticker in tickers:
            if ticker in tickers_data.columns.get_level_values(1):
                data[ticker] = tickers_data["Close"][ticker].iloc[-1]
    except Exception as e:
        st.error(f"Error fetching batch data: {e}")
    return data

def fetch_emails():
    """Fetch emails from the server."""
    try:
        with imaplib.IMAP4_SSL('imap.gmail.com') as mail:
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            mail.select('inbox')
            since_date = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
            _, data = mail.search(None, f'(FROM "{SENDER_EMAIL}" SINCE "{since_date}")')

            email_data = []
            for num in data[0].split():
                if num in processed_email_ids:
                    continue  # Skip already processed emails
                _, msg_data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                email_data.append(msg)
                processed_email_ids.add(num)  # Mark email as processed
            return email_data
    except Exception as e:
        st.error(f"Error fetching emails: {e}")
        return []

def extract_stock_symbols(emails, keyword):
    """Extract stock symbols for a specific keyword from emails."""
    stock_data = []
    for msg in emails:
        try:
            email_date = parser.parse(msg['Date']).date()
            if email_date.weekday() >= 5:  # Skip weekends
                continue
            body = extract_email_body(msg)
            symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*(' + re.escape(keyword) + ')', body)
            for symbol_group in symbols:
                extracted_symbols = symbol_group[0].replace(" ", "").split(",")
                for symbol in extracted_symbols:
                    stock_data.append([symbol, email_date, keyword])
        except Exception as e:
            st.warning(f"Error processing email: {e}")
    df = pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal']).drop_duplicates()
    return df

def extract_email_body(msg):
    """Extract the text content from an email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                return part.get_payload(decode=True).decode()
    else:
        return msg.get_payload(decode=True).decode()

def fetch_stock_prices(df):
    """Fetch stock prices for the tickers in the DataFrame."""
    tickers = df['Ticker'].unique().tolist()
    today_prices = batch_fetch_prices(tickers)
    results = []
    for _, row in df.iterrows():
        alert_price = today_prices.get(row['Ticker'], None)
        today_price = today_prices.get(row['Ticker'], None)
        rate_of_return = ((today_price - alert_price) / alert_price) * 100 if alert_price and today_price else None
        results.append([row['Ticker'], row['Date'], alert_price, today_price, rate_of_return, row['Signal']])
    return pd.DataFrame(results, columns=['Ticker', 'Alert Date', 'Alert Price', 'Today Price', 'Return (%)', 'Signal'])

def main():
    st.title("📈 Thinkorswim Alerts Analyzer")
    button(username="tosalerts33", floating=False, width=221)
    
    emails = fetch_emails()

    for keyword in KEYWORDS:
        st.subheader(f"Analyzing {keyword}")
        df = extract_stock_symbols(emails, keyword)
        if not df.empty:
            price_df = fetch_stock_prices(df)
            st.dataframe(price_df)
        else:
            st.write(f"No data found for {keyword}.")

    # Add JavaScript-based auto-refresh
    st.markdown("---")
    st.write("Polling completed. Auto-refreshing in 15 minutes...")
    st.components.v1.html(
        """
        <script>
            setTimeout(function() {
                window.location.reload();
            }, 900000); // Refresh after 900,000 milliseconds (15 minutes)
        </script>
        """,
        height=0,
    )

if __name__ == "__main__":
    main()
