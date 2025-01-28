import streamlit as st
from streamlit_extras.buy_me_a_coffee import button
import imaplib
import email
import re
import datetime
import pandas as pd
from dateutil import parser
import yfinance as yf
import asyncio
from bs4 import BeautifulSoup

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 600  # 10 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords
KEYWORDS = ["volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short", "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"]

# Tooltips
TOOLTIPS = {
    "volume_scan": {"header": "Bullish Intraday high volume", "description": "This scan identifies high volume stocks that have very high volume and stock is up at least 2%."},
    "A+Bull_30m": {"header": "30mins A+Bull Alerts", "description": "This scan identifies bullish setups on a 30-minute chart. Typically I use it to play move 2 weeks out."},
    "tmo_Short": {"header": "Momentum Short Alerts", "description": "This scan identifies short-term overbought conditions for potential short opportunities."},
    "tmo_long": {"header": "Momentum Long Alerts", "description": "This scan identifies short-term oversold conditions for potential long opportunities."},
    "Long_IT_volume": {"header": "Long High Volume 9EMA Alerts", "description": "This scan looks for stocks with highest volume in last 30 days and breaking up above 9ema."},
    "Short_IT_volume": {"header": "Short High Volume 9EMA Alerts", "description": "This scan looks for stocks with highest volume in last 30 days and breaking down below 9ema."},
    "bull_Daily_sqz": {"header": "Bullish Daily Squeeze Alerts", "description": "This scan identifies stocks in a bullish squeeze on the daily chart."},
    "bear_Daily_sqz": {"header": "Bearish Daily Squeeze Alerts", "description": "This scan identifies stocks in a bearish squeeze on the daily chart."},
}

processed_email_uids = set()  # Global set for processed email UIDs

def get_spy_qqq_prices():
    spy = yf.Ticker("SPY")
    qqq = yf.Ticker("QQQ")
    try:
        spy_price = round(spy.history(period="1d")['Close'].iloc[-1], 2)
        qqq_price = round(qqq.history(period="1d")['Close'].iloc[-1], 2)
        return spy_price, qqq_price
    except Exception as e:
        st.error(f"Error fetching SPY/QQQ prices: {e}")
        return None, None


async def fetch_emails_and_extract(email_address, password, sender_email, keyword):
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_address, password)
        mail.select('inbox')

        date_since = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{sender_email}" SUBJECT "{keyword}" SINCE "{date_since}")'
        _, data = mail.search(None, search_criteria)

        stock_data = []
        for uid in data[0].split():
            if uid in processed_email_uids:
                continue

            _, data = mail.fetch(uid, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            email_date = parser.parse(msg['Date']).date()

            if email_date.weekday() >= 5:  # Skip weekends
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
                    elif content_type == "text/html" and not body:
                        html_body = part.get_payload(decode=True).decode()
                        soup = BeautifulSoup(html_body, "html.parser")
                        body = soup.get_text()
            elif msg.get_content_type() == "text/html":
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

            processed_email_uids.add(uid)

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

    if today.weekday() >= 5:
        today = today - datetime.timedelta(days=today.weekday() - 4)

    for _, row in df.iterrows():
        ticker = row['Ticker']
        alert_date = row['Date']
        try:
            stock = yf.Ticker(ticker)

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

            prices.append([ticker, alert_date, alert_price, today_price, rate_of_return, row['Signal']])
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            prices.append([ticker, alert_date, None, None, None, row['Signal']])

    price_df = pd.DataFrame(prices, columns=['Symbol', 'Alert Date', 'Alert Date Close', 'Today Close', 'Return Alert(%)', 'Signal'])
    price_df = price_df.sort_values(by='Alert Date', ascending=False)
    return price_df


def main():
    st.title("Thinkorswim Alerts Analyzer")
    button(username="tosalerts33", floating=False, width=221)

    spy_price, qqq_price = get_spy_qqq_prices()
    if spy_price is not None and qqq_price is not None:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("SPY Latest Close Price", f"<span class="math-inline">\{spy\_price\}"\)
with col2\:
st\.metric\("QQQ Latest Close Price", f"</span>{qqq_price}")

    async def process_all_keywords():
        results = {}
        for keyword in KEYWORDS:
            results[keyword] = await fetch_emails_and_extract(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
        return results

    async def display_data(results):
        for keyword,
