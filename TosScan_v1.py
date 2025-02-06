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
POLL_INTERVAL = 600  # 10 minutes
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords for email subjects
KEYWORDS = [
    "orb_bull", "orb_bear", "volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short",
    "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"
]

# Track processed email IDs
processed_email_ids = set()

# Tooltip descriptions
TOOLTIPS = {
    "orb_bull": {"header": "Bullish 30m ORB", "description": "Identifies stocks crossing above the 30m opening range."},
    "orb_bear": {"header": "Bearish 30m ORB", "description": "Identifies stocks crossing below the 30m opening range."},
    "volume_scan": {"header": "High Volume Scan", "description": "Detects stocks up 2%+ with high volume."},
    "A+Bull_30m": {"header": "30m A+ Bull Alerts", "description": "Bullish setups on a 30-minute chart."},
    "tmo_Short": {"header": "Momentum Short", "description": "Short-term overbought stocks for short opportunities."},
    "tmo_long": {"header": "Momentum Long", "description": "Short-term oversold stocks for long opportunities."},
    "Long_IT_volume": {"header": "Long High Volume 9EMA", "description": "Stocks with highest volume in 30 days breaking above 9EMA."},
    "Short_IT_volume": {"header": "Short High Volume 9EMA", "description": "Stocks with highest volume in 30 days breaking below 9EMA."},
    "bull_Daily_sqz": {"header": "Bullish Daily Squeeze", "description": "Identifies stocks in a bullish squeeze on the daily chart."},
    "bear_Daily_sqz": {"header": "Bearish Daily Squeeze", "description": "Identifies stocks in a bearish squeeze on the daily chart."}
}

@st.cache_data
def get_spy_qqq_prices():
    """Fetch the latest closing prices for SPY and QQQ."""
    tickers = yf.download(["SPY", "QQQ"], period="1d")['Close']
    return round(tickers["SPY"].iloc[-1], 2), round(tickers["QQQ"].iloc[-1], 2)

def extract_stock_symbols_from_email(email_address, password, sender_email, keyword):
    """Fetch stock symbols from Thinkorswim alert emails."""
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

            _, fetched_data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(fetched_data[0][1])
            email_date = parser.parse(msg['Date']).date()

            if email_date.weekday() >= 5:  # Skip weekends
                continue

            body = ""
            for part in msg.walk():
                if part.get_content_type() in ["text/plain", "text/html"]:
                    body = part.get_payload(decode=True).decode()
                    if part.get_content_type() == "text/html":
                        body = BeautifulSoup(body, "html.parser").get_text()

            # Extract symbols
            symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*' + re.escape(keyword), body)
            if symbols:
                for symbol_group in symbols:
                    extracted_symbols = [sym.strip() for sym in symbol_group.split(",") if sym.strip()]
                    stock_data.extend([[symbol, email_date, keyword] for symbol in extracted_symbols])

            processed_email_ids.add(num)  # Mark email as processed

        mail.close()
        mail.logout()

        return pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal']).drop_duplicates(subset=['Ticker'])

    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

    return pd.DataFrame(prices, columns=['Symbol', 'Alert Date', 'Signal'])


def main():
    st.title("Thinkorswim Alerts Analyzer")
    st.write("This app polls your Thinkorswim alerts and analyzes stock data for different keywords.")

    button(username="tosalerts33", floating=False, width=221)

    # Fetch SPY and QQQ prices
    spy_price, qqq_price = get_spy_qqq_prices()
    col1, col2 = st.columns(2)
    col1.metric("SPY Latest Close", f"${spy_price}")
    col2.metric("QQQ Latest Close", f"${qqq_price}")

    with st.spinner("Polling alerts and analyzing data..."):
        for keyword in KEYWORDS:
            tooltip = TOOLTIPS.get(keyword, {"header": keyword, "description": "No description available."})
            st.markdown(f"### {tooltip['header']} ℹ️")
            st.caption(tooltip["description"])

            symbols_df = extract_stock_symbols_from_email(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
            if not symbols_df.empty:
                price_df = fetch_stock_prices(symbols_df)
                st.dataframe(price_df)

                # Download button for CSV
                csv = price_df.to_csv(index=False).encode('utf-8')
                st.download_button(f"Download {tooltip['header']} Data", csv, f"{keyword}_alerts.csv", "text/csv")
            else:
                st.warning(f"No new stock found for {keyword}.")

    st.markdown("---")
    st.markdown("### Disclaimer")
    st.markdown("This tool is for informational purposes only and is not financial advice. Use at your own risk.")

    time.sleep(POLL_INTERVAL)
    st.rerun()

if __name__ == "__main__":
    main()
