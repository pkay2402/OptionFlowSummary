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
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 900  # 15 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords to search for in email subjects
KEYWORDS = [
    "volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short", 
    "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"
]

# Track processed email IDs to avoid duplicates
processed_email_ids = set()

# Custom Tooltip descriptions for each keyword
TOOLTIPS = {
    "volume_scan": {
        "header": "Bullish Intraday high volume",
        "description": "This scan identifies high volume stocks that have very high volume and stock is up at least 2%."
    },
    "A+Bull_30m": {
        "header": "30mins A+Bull Alerts",
        "description": "This scan identifies bullish setups on a 30-minute chart. Typically I use it to play move 2 weeks out."
    },
    "tmo_Short": {
        "header": "Momentum Short Alerts",
        "description": "This scan identifies short-term overbought conditions for potential short opportunities."
    },
    "tmo_long": {
        "header": "Momentum Long Alerts",
        "description": "This scan identifies short-term oversold conditions for potential long opportunities."
    },
    "Long_IT_volume": {
        "header": "Long High Volume 9EMA Alerts",
        "description": "This scan looks for stocks with highest volume in last 30 days and breaking up above 9ema."
    },
    "Short_IT_volume": {
        "header": "Short High Volume 9EMA Alerts",
        "description": "This scan looks for stocks with highest volume in last 30 days and breaking down below 9ema."
    },
    "bull_Daily_sqz": {
        "header": "Bullish Daily Squeeze Alerts",
        "description": "This scan identifies stocks in a bullish squeeze on the daily chart."
    },
    "bear_Daily_sqz": {
        "header": "Bearish Daily Squeeze Alerts",
        "description": "This scan identifies stocks in a bearish squeeze on the daily chart."
    }
}

# Cache yfinance ticker data to avoid redundant API calls
@lru_cache(maxsize=32)
def get_ticker_data(ticker):
    return yf.Ticker(ticker)

def get_spy_qqq_prices():
    """Fetch the latest closing prices for SPY and QQQ."""
    spy = get_ticker_data("SPY")
    qqq = get_ticker_data("QQQ")
    
    spy_price = round(spy.history(period="1d")['Close'].iloc[-1], 2)
    qqq_price = round(qqq.history(period="1d")['Close'].iloc[-1], 2)
    
    return spy_price, qqq_price

def fetch_all_emails(email_address, password, sender_email):
    """Fetch all emails from the sender and return a list of email messages."""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, password)
        mail.select('inbox')

        date_since = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{sender_email}" SINCE "{date_since}")'
        _, data = mail.search(None, search_criteria)

        emails = []
        for num in data[0].split():
            if num in processed_email_ids:
                continue  # Skip already processed emails

            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            emails.append(msg)
            processed_email_ids.add(num)  # Mark email as processed

        mail.close()
        mail.logout()
        return emails

    except Exception as e:
        st.error(f"Error fetching emails: {e}")
        return []

def extract_stock_symbols_from_email(emails, keyword):
    """Extract stock symbols from emails for a given keyword."""
    stock_data = []
    for msg in emails:
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

    df = pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal'])
    df = df.sort_values(by=['Date', 'Ticker']).drop_duplicates(subset=['Ticker'], keep='last')
    return df

def fetch_stock_prices(df):
    """Fetch stock prices and calculate returns for a DataFrame of tickers."""
    prices = []
    today = datetime.date.today()
    
    if today.weekday() >= 5:  # Saturday (5) or Sunday (6)
        today = today - datetime.timedelta(days=today.weekday() - 4)  # Set to Friday

    def fetch_ticker_data(row):
        ticker = row['Ticker']
        alert_date = row['Date']
        try:
            stock = get_ticker_data(ticker)
            
            hist_alert = stock.history(start=alert_date, end=alert_date + datetime.timedelta(days=1))
            alert_price = round(hist_alert['Close'].iloc[0], 2) if not hist_alert.empty else None
            
            hist_today = stock.history(period="1d")
            if not hist_today.empty:
                today_price = round(hist_today['Close'].iloc[-1], 2)
            else:
                hist_recent = stock.history(period="1mo")
                today_price = round(hist_recent['Close'].iloc[-1], 2) if not hist_recent.empty else None
            
            if alert_price and today_price:
                rate_of_return = ((today_price - alert_price) / alert_price) * 100
            else:
                rate_of_return = None

            return [ticker, alert_date, alert_price, today_price, rate_of_return, row['Signal']]
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            return [ticker, alert_date, None, None, None, row['Signal']]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_ticker_data, row) for _, row in df.iterrows()]
        for future in as_completed(futures):
            prices.append(future.result())

    price_df = pd.DataFrame(prices, columns=[
        'Symbol', 'Alert Date', 'Alert Date Close', 'Today Close', 'Return Alert(%)', 'Signal'
    ])
    price_df = price_df.sort_values(by='Alert Date', ascending=False)
    return price_df

def main():
    st.title("Thinkorswim Alerts Analyzer")
    st.write("This app polls your Thinkorswim alerts and analyzes stock data for different keywords.")

    # Add Buy Me a Coffee button
    button(username="tosalerts33", floating=False, width=221)

    # Add tooltip CSS once
    st.markdown(
        """
        <style>
        .tooltip {
            position: relative;
            display: inline-block;
        }
        .tooltip .tooltiptext {
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
        }
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Fetch SPY and QQQ prices
    spy_price, qqq_price = get_spy_qqq_prices()

    # Display SPY and QQQ prices
    col1, col2 = st.columns(2)
    with col1:
        st.metric("SPY Latest Close Price", f"${spy_price}")
    with col2:
        st.metric("QQQ Latest Close Price", f"${qqq_price}")

    # Fetch all emails once
    emails = fetch_all_emails(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL)

    # Process each keyword
    with st.spinner("Polling alerts and analyzing data..."):
        cols_per_row = 2
        rows = (len(KEYWORDS) + cols_per_row - 1) // cols_per_row

        for row in range(rows):
            cols = st.columns(cols_per_row)
            for col in range(cols_per_row):
                idx = row * cols_per_row + col
                if idx < len(KEYWORDS):
                    keyword = KEYWORDS[idx]
                    with cols[col]:
                        tooltip_data = TOOLTIPS.get(keyword, {"header": keyword, "description": "No description available."})
                        st.markdown(
                            f"""
                            <div class="tooltip">
                                <h3>{tooltip_data["header"]} <span style="font-size: 0.8em;">ℹ️</span></h3>
                                <span class="tooltiptext">{tooltip_data["description"]}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        
                        symbols_df = extract_stock_symbols_from_email(emails, keyword)
                        if not symbols_df.empty:
                            price_df = fetch_stock_prices(symbols_df)
                            st.dataframe(price_df)

                            csv = price_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"Download {tooltip_data['header']} Data as CSV",
                                data=csv,
                                file_name=f"{keyword}_alerts.csv",
                                mime="text/csv",
                            )
                        else:
                            st.warning(f"No new stock found for {keyword}.")

    # Disclaimer and Important Messages
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

    # Automatically rerun the app every POLL_INTERVAL seconds
    time.sleep(POLL_INTERVAL)
    st.rerun()

if __name__ == "__main__":
    main()
