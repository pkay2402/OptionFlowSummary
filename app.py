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
from store_data import store_data, fetch_data

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 600  # 10 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords to search for in email subjects
KEYWORDS = ["volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short", "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"]  # Add more keywords as needed

# Track processed email IDs to avoid duplicates
processed_email_ids = set()

# Custom Tooltip descriptions for each keyword
TOOLTIPS = {
    "volume_scan": {
        "header": "Bullish Intraday high volume",
        "description": "This scan identifies high volume stocks that have very high volume and stock is up at least 2%."
    },
    # ... (rest of TOOLTIPS remain the same)
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

        date_since = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
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

            # Extract symbols using regex
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

def fetch_stock_prices(df):
    prices = []
    today = datetime.date.today()
    
    if today.weekday() >= 5:  # Saturday (5) or Sunday (6)
        today = today - datetime.timedelta(days=today.weekday() - 4)  # Set to Friday

    for index, row in df.iterrows():
        ticker = row['Ticker']
        alert_date = row['Date']
        try:
            stock = yf.Ticker(ticker)
            hist_alert = stock.history(start=alert_date, end=alert_date + datetime.timedelta(days=1))
            alert_price = round(hist_alert['Close'].iloc[0], 2) if not hist_alert.empty else None
            hist_today = stock.history(period="1d")
            today_price = round(hist_today['Close'].iloc[-1], 2) if not hist_today.empty else None
            
            if alert_price and today_price:
                rate_of_return = ((today_price - alert_price) / alert_price) * 100
            else:
                rate_of_return = None

            prices.append([ticker, alert_date, alert_price, today_price, rate_of_return, row['Signal']])
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            prices.append([ticker, alert_date, None, None, None, row['Signal']])
    
    price_df = pd.DataFrame(prices, columns=['Symbol', 'Alert Date', 'Alert Date Close', 'Today Close', 'Return Alert(%)', 'Signal'])
    price_df = price_df.sort_values(by='Alert Date', ascending=False)
    
    return price_df

def main():
    st.title("Thinkorswim Alerts Analyzer")
    st.write("This app polls your Thinkorswim alerts and analyzes stock data for different keywords.")

    button(username="tosalerts33", floating=False, width=221)

    spy_price, qqq_price = get_spy_qqq_prices()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("SPY Latest Close Price", f"${spy_price}")
    with col2:
        st.metric("QQQ Latest Close Price", f"${qqq_price}")

    with st.spinner("Polling alerts and analyzing data..."):
        for keyword in KEYWORDS:
            symbols_df = extract_stock_symbols_from_email(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
            if not symbols_df.empty:
                price_df = fetch_stock_prices(symbols_df)
                
                store_data(price_df, table_name=f"{keyword}_alerts")
                
                stored_df = fetch_data(table_name=f"{keyword}_alerts")
                
                st.markdown(f"### {TOOLTIPS[keyword]['header']}")
                st.dataframe(stored_df)

                csv = stored_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"Download {TOOLTIPS[keyword]['header']} Data as CSV",
                    data=csv,
                    file_name=f"{keyword}_alerts.csv",
                    mime="text/csv",
                )
            else:
                st.warning(f"No new stock found for {keyword}.")

    st.markdown("---")
    st.markdown("### **Disclaimer and Important Messages**")
    st.markdown("""
    **1. Not Financial Advice:**  
    This tool is for informational and educational purposes only. It is not intended to provide financial, investment, or trading advice. The data and analysis provided should not be construed as a recommendation to buy, sell, or hold any security or financial instrument.

    **2. No Guarantees:**  
    The creator of this tool makes no guarantees regarding the accuracy, completeness, or reliability of the information provided. Stock market investments are inherently risky, and past performance is not indicative of future results.

    **3. Your Responsibility:**  
    You are solely responsible for your financial decisions. The creator of this tool is not responsible for any profits or losses you may incur as a result of using this tool or acting on the information provided.

    **4. Consult a Professional:**  
    Before making any financial decisions, consult with a qualified financial advisor or professional who can provide personalized advice based on your individual circumstances.

    **5. Use at Your Own Risk:**  
    By using this tool, you acknowledge and agree that you are using it at your own risk. The creator disclaims all liability for any damages or losses arising from your use of this tool.
    """)

    time.sleep(POLL_INTERVAL)
    st.rerun()

if __name__ == "__main__":
    main()
