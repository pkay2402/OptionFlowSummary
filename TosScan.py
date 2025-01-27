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

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 900  # 15 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords to search for in email subjects
KEYWORDS = ["A+Bull_30m","tmo_Short", "tmo_long", "Long_IT_volume","Short_IT_volume","bull_Daily_sqz","bear_Daily_sqz"]  # Add more keywords as needed

# Track processed email IDs to avoid duplicates
processed_email_ids = set()

# Tooltip descriptions for each keyword
TOOLTIPS = {
    "30mins_A+bull_alerts": "This scan identifies bullish setups on a 30-minute chart. Typically I use it to play move 2 weeks out",
    "tmo_Short": "This scan identifies short-term overbought conditions for potential short opportunities.",
    "tmo_long": "This scan identifies short-term oversold conditions for potential long opportunities.",
    "LONG_HIGHVOLUME_9EMA": "This scan looks for stocks with highest volume in last 30 days and breaking up above 9ema.",
    "SHORT_HIGHVOLUME_9EMA": "This scan looks for stocks with highest volume in last 30 days and breaking down below 9ema",
    "bull_Daily_sqz": "This scan identifies stocks in a bullish squeeze on the daily chart.",
    "bear_Daily_sqz": "This scan identifies stocks in a bearish squeeze on the daily chart.",
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
    st.write("This app polls your Thinkorswim alerts and analyzes stock data for different keywords.")

    # Add Buy Me a Coffee button using streamlit-extras
    button(username="tosalerts33", floating=False, width=221)

    # Fetch SPY and QQQ prices
    spy_price, qqq_price = get_spy_qqq_prices()

    # Display SPY and QQQ prices with a refresh button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("SPY Latest Close Price", f"${spy_price}")
    with col2:
        st.metric("QQQ Latest Close Price", f"${qqq_price}")
    with col3:
        if st.button("Refresh Prices"):
            st.rerun()  # Refresh the app to update prices

    if st.button("Poll ThinkorSwim Alerts and Analyze"):
        with st.spinner("Polling alerts and analyzing data..."):
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
                            # Add a tooltip for the keyword
                            st.markdown(
                                f"""
                                <style>
                                .tooltip {{
                                    position: relative;
                                    display: inline-block;
                                }}
                                .tooltip .tooltiptext {{
                                    visibility: hidden;
                                    width: 200px;
                                    background-color: #555;
                                    color: #fff;
                                    text-align: center;
                                    border-radius: 6px;
                                    padding: 5px;
                                    position: absolute;
                                    z-index: 1;
                                    bottom: 125%;
                                    left: 50%;
                                    margin-left: -100px;
                                    opacity: 0;
                                    transition: opacity 0.3s;
                                }}
                                .tooltip:hover .tooltiptext {{
                                    visibility: visible;
                                    opacity: 1;
                                }}
                                </style>
                                <div class="tooltip">
                                    <h3>{keyword.upper()} Alerts <span style="font-size: 0.8em;">ℹ️</span></h3>
                                    <span class="tooltiptext">{TOOLTIPS.get(keyword, "No description available.")}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            
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
