import streamlit as st
from streamlit_extras.buy_me_a_coffee import button
import imaplib
import email
import re
import datetime
import pandas as pd
from dateutil import parser
import yfinance as yf
import time
from bs4 import BeautifulSoup

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 600  # 10 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Define keywords for intraday and daily scans
INTRADAY_KEYWORDS = ["Long_VP", "Short_VP", "orb_bull", "orb_bear", "volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short"]
DAILY_KEYWORDS = ["Long_IT_volume", "Short_IT_volume","bull_Daily_sqz", "bear_Daily_sqz"]

# Track processed email IDs
processed_email_ids = set()

def get_spy_qqq_prices():
    """Fetch the latest closing prices for SPY and QQQ."""
    spy = yf.Ticker("SPY")
    qqq = yf.Ticker("QQQ")
    
    spy_price = round(spy.history(period="1d")['Close'].iloc[-1], 2)
    qqq_price = round(qqq.history(period="1d")['Close'].iloc[-1], 2)
    
    return spy_price, qqq_price

def extract_stock_symbols_from_email(email_address, password, sender_email, keyword):
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, password)
        mail.select('inbox')

        date_since = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{sender_email}" SUBJECT "{keyword}" SINCE "{date_since}")'
        _, data = mail.search(None, search_criteria)

        stock_data = []
        for num in data[0].split():
            if num in processed_email_ids:
                continue  # Skip already processed emails

            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            email_date = parser.parse(msg['Date']).date()
            
            if email_date.weekday() >= 5:  # Skip weekends
                continue

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                    elif part.get_content_type() == "text/html":
                        html_body = part.get_payload(decode=True).decode()
                        soup = BeautifulSoup(html_body, "html.parser")
                        body = soup.get_text()
            else:
                if msg.get_content_type() == "text/html":
                    html_body = msg.get_payload(decode=True).decode()
                    soup = BeautifulSoup(html_body, "html.parser")
                    body = soup.get_text()
                else:
                    body = msg.get_payload(decode=True).decode()

            symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*(' + re.escape(keyword) + ')', body)
            if symbols:
                for symbol_group in symbols:
                    extracted_symbols = symbol_group[0].replace(" ", "").split(",")
                    signal_type = symbol_group[1]
                    for symbol in extracted_symbols:
                        stock_data.append([symbol, email_date, signal_type])

            processed_email_ids.add(num)  # Mark email as processed

        mail.close()
        mail.logout()

        df = pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal'])
        df = df.sort_values(by=['Date', 'Ticker']).drop_duplicates(subset=['Ticker'], keep='last')

        return df

    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

def main():
    st.title("Thinkorswim Alerts Analyzer")
    st.write("This app polls your Thinkorswim alerts and analyzes stock data for different keywords.")

    # Buy Me a Coffee Button
    button(username="tosalerts33", floating=False, width=221)

    # Fetch SPY and QQQ Prices
    spy_price, qqq_price = get_spy_qqq_prices()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("SPY Latest Close Price", f"${spy_price}")
    with col2:
        st.metric("QQQ Latest Close Price", f"${qqq_price}")

    # Radio button for Intraday vs. Daily
    section = st.radio("Select Scan Type", ["Intraday", "Daily"], index=0)
    selected_keywords = INTRADAY_KEYWORDS if section == "Intraday" else DAILY_KEYWORDS
    
    st.subheader(f"{section} Scans")
    
    for keyword in selected_keywords:
        with st.expander(f"Show {keyword} Data"):
            symbols_df = extract_stock_symbols_from_email(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
            if not symbols_df.empty:
                st.dataframe(symbols_df)
                csv = symbols_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"Download {keyword} Data as CSV",
                    data=csv,
                    file_name=f"{keyword}_alerts.csv",
                    mime="text/csv",
                )
            else:
                st.warning(f"No new stock found for {keyword}.")

if __name__ == "__main__":
    main()
