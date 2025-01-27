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

# Keywords to search for in email subjects
KEYWORDS = ["volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short", "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"]

# Track processed email IDs to avoid duplicates
processed_email_ids = set()

# Tooltips for keywords
TOOLTIPS = {
    "volume_scan": {"header": "Bullish Intraday high volume", "description": "Identifies high volume stocks up at least 2%."},
    "A+Bull_30m": {"header": "30mins A+Bull Alerts", "description": "Bullish setups on a 30-minute chart."},
    # Add other descriptions as needed...
}

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

        date_since = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{sender_email}" SUBJECT "{keyword}" SINCE "{date_since}")'
        _, data = mail.search(None, search_criteria)

        stock_data = []
        for num in data[0].split():
            if num in processed_email_ids:
                continue

            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            email_date = parser.parse(msg['Date']).date()

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        body = BeautifulSoup(part.get_payload(decode=True).decode(), "html.parser").get_text()
            else:
                body = msg.get_payload(decode=True).decode()

            symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*(' + re.escape(keyword) + ')', body)
            if symbols:
                for symbol_group in symbols:
                    extracted_symbols = symbol_group[0].replace(" ", "").split(",")
                    signal_type = symbol_group[1]
                    for symbol in extracted_symbols:
                        stock_data.append([symbol, email_date, signal_type])

            processed_email_ids.add(num)

        mail.close()
        mail.logout()

        return pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal']).drop_duplicates()
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

def fetch_stock_prices(df):
    prices = []
    for index, row in df.iterrows():
        ticker = row['Ticker']
        alert_date = row['Date']
        try:
            stock = yf.Ticker(ticker)
            alert_price = stock.history(start=alert_date, end=alert_date + datetime.timedelta(days=1))['Close'].iloc[0]
            today_price = stock.history(period="1d")['Close'].iloc[-1]
            rate_of_return = ((today_price - alert_price) / alert_price) * 100
            prices.append([ticker, alert_date, alert_price, today_price, rate_of_return, row['Signal']])
        except:
            prices.append([ticker, alert_date, None, None, None, row['Signal']])

    return pd.DataFrame(prices, columns=['Stock Symbol', 'Alert Date', 'Alert Price', 'Latest Price', 'Return (%)', 'Signal']).sort_values(by='Alert Date', ascending=False)

def main():
    st.title("Thinkorswim Alerts Analyzer")
    button(username="tosalerts33", floating=False, width=221)

    spy_price, qqq_price = get_spy_qqq_prices()
    col1, col2 = st.columns(2)
    col1.metric("SPY Latest Close Price", f"${spy_price}")
    col2.metric("QQQ Latest Close Price", f"${qqq_price}")

    for keyword in KEYWORDS:
        st.subheader(TOOLTIPS.get(keyword, {}).get("header", keyword))
        symbols_df = extract_stock_symbols_from_email(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
        if not symbols_df.empty:
            price_df = fetch_stock_prices(symbols_df)
            st.dataframe(price_df)
        else:
            st.write(f"No data for {keyword}.")

    # Disclaimer
    st.markdown("""
    ---
    ### Disclaimer
    **1. Not Financial Advice:**  
    This tool is for informational and educational purposes only. It is not intended to provide financial, investment, or trading advice.  

    **2. No Guarantees:**  
    The creator of this tool makes no guarantees regarding the accuracy, completeness, or reliability of the information provided.  

    **3. Your Responsibility:**  
    You are solely responsible for your financial decisions.  

    **4. Consult a Professional:**  
    Before making any financial decisions, consult with a qualified financial advisor.  

    **5. Use at Your Own Risk:**  
    By using this tool, you acknowledge and agree that you are using it at your own risk.
    """)

if __name__ == "__main__":
    main()
