import streamlit as st
import imaplib
import email
import re
import datetime
import pandas as pd
from dateutil import parser
import yfinance as yf
import time

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 900  # 15 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords to search for in email subjects
KEYWORDS = ["tmo_Short", "tmo_long", "Long_IT_volume","Short_IT_volume","bull_Daily_sqz","bear_Daily_sqz","A+Bull_30m"]  # Add more keywords as needed

# Track processed email IDs to avoid duplicates
processed_email_ids = set()

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
                        symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*(' + re.escape(keyword) + ')', body)
                        if symbols:
                            for symbol_group in symbols:
                                extracted_symbols = symbol_group[0].replace(" ", "").split(",")
                                signal_type = symbol_group[1]
                                for symbol in extracted_symbols:
                                    stock_data.append([symbol, email_date, signal_type])
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

def fetch_stock_prices(df):
    prices = []
    today = datetime.date.today()
    
    # Adjust today's date if it's a weekend
    if today.weekday() >= 5:  # Saturday (5) or Sunday (6)
        today = today - datetime.timedelta(days=today.weekday() - 4)  # Set to Friday

    for index, row in df.iterrows():
        ticker = row['Ticker']
        alert_date = row['Date']
        try:
            stock = yf.Ticker(ticker)
            hist_alert = stock.history(start=alert_date, end=alert_date + datetime.timedelta(days=1))
            hist_today = stock.history(start=today, end=today + datetime.timedelta(days=1))
            
            alert_price = round(hist_alert['Close'].iloc[0], 2) if not hist_alert.empty else None
            today_price = round(hist_today['Close'].iloc[0], 2) if not hist_today.empty else None
            
            # Calculate the rate of return (if both prices are available)
            if alert_price and today_price:
                rate_of_return = ((today_price - alert_price) / alert_price) * 100
            else:
                rate_of_return = None

            prices.append([ticker, alert_date, alert_price, today_price, rate_of_return, row['Signal']])
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            prices.append([ticker, alert_date, None, None, None, row['Signal']])
    
    price_df = pd.DataFrame(prices, columns=['Ticker', 'Alert Date', 'Alert Close Price', "Latest Close Price", 'Rate of Return (%)', 'Signal'])
    
    # Sort by Alert Date (latest first)
    price_df = price_df.sort_values(by='Alert Date', ascending=False)
    
    return price_df

def main():
    st.title("Thinkorswim Alerts Analyzer")
    st.write("This app polls your email for Thinkorswim alerts and analyzes stock data for different keywords.")

    if st.button("Poll Emails and Analyze"):
        with st.spinner("Polling emails and analyzing data..."):
            # Define the number of columns per row
            cols_per_row = 2
            rows = (len(KEYWORDS) + cols_per_row - 1) // cols_per_row  # Calculate the number of rows

            for row in range(rows):
                cols = st.columns(cols_per_row)  # Create columns for the current row
                for col in range(cols_per_row):
                    idx = row * cols_per_row + col
                    if idx < len(KEYWORDS):  # Check if there's a keyword for this column
                        keyword = KEYWORDS[idx]
                        with cols[col]:  # Use the corresponding column
                            st.header(f"{keyword.upper()} Alerts")
                            
                            # Extract and process data for the current keyword
                            symbols_df = extract_stock_symbols_from_email(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
                            if not symbols_df.empty:
                                price_df = fetch_stock_prices(symbols_df)
                                
                                # Display the DataFrame in the app
                                st.dataframe(price_df)

                                # Add a download button for CSV
                                csv = price_df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label=f"Download {keyword.upper()} Data as CSV",
                                    data=csv,
                                    file_name=f"{keyword}_alerts.csv",
                                    mime="text/csv",
                                )
                            else:
                                st.warning(f"No new emails found for {keyword}.")

if __name__ == "__main__":
    main()
