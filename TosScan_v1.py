import streamlit as st
from streamlit_extras.buy_me_a_coffee import button
import imaplib
import email
import re
from datetime import datetime, timedelta
import pandas as pd
from dateutil import parser
import yfinance as yf
import time
from bs4 import BeautifulSoup
import plotly.graph_objects as go

# Fetch credentials from Streamlit Secrets
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

# Constants
POLL_INTERVAL = 600  # 10 minutes in seconds
SENDER_EMAIL = "alerts@thinkorswim.com"

# Keywords for email subjects
KEYWORDS = [
    "orb_bull", "orb_bear", "volume_scan", "A+Bull_30m", "tmo_long", "tmo_Short",
    "Long_IT_volume", "Short_IT_volume", "bull_Daily_sqz", "bear_Daily_sqz"
]

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_spy_qqq_prices():
    """Fetch the latest closing prices for SPY and QQQ."""
    try:
        spy = yf.Ticker("SPY")
        qqq = yf.Ticker("QQQ")
        
        spy_price = round(spy.history(period="1d")['Close'].iloc[-1], 2)
        qqq_price = round(qqq.history(period="1d")['Close'].iloc[-1], 2)
        
        return spy_price, qqq_price
    except Exception as e:
        st.error(f"Error fetching market prices: {e}")
        return None, None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_stock_prices(df):
    if df.empty:
        return pd.DataFrame(columns=['Ticker', 'Latest Price'])
        
    prices = []
    for symbol in df['Ticker']:
        try:
            ticker = yf.Ticker(symbol)
            latest_price = ticker.history(period="1d")['Close'].iloc[-1]
            prices.append({'Ticker': symbol, 'Latest Price': round(latest_price, 2)})
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            st.warning(f"Failed to fetch price for {symbol}: {e}")
            prices.append({'Ticker': symbol, 'Latest Price': None})
    
    return pd.DataFrame(prices)

def connect_to_email():
    """Establish IMAP connection with error handling."""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        return mail
    except imaplib.IMAP4.error as e:
        st.error(f"IMAP connection error: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error connecting to email: {e}")
        return None

def extract_stock_symbols_from_email(email_address, password, sender_email, keyword):
    mail = connect_to_email()
    if not mail:
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

    try:
        mail.select('inbox')
        date_since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        search_criteria = f'(FROM "{sender_email}" SUBJECT "{keyword}" SINCE "{date_since}")'
        _, data = mail.search(None, search_criteria)

        stock_data = []
        processed_email_ids = set()  # Move inside function to avoid global state

        for num in data[0].split():
            if num in processed_email_ids:
                continue

            _, msg_data = mail.fetch(num, '(RFC822)')
            email_msg = email.message_from_bytes(msg_data[0][1])
            email_date = parser.parse(email_msg['Date']).date()
            
            if email_date.weekday() >= 5:  # Skip weekends
                continue

            body = ""
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    if part.get_content_type() in ["text/plain", "text/html"]:
                        payload = part.get_payload(decode=True).decode()
                        if part.get_content_type() == "text/html":
                            soup = BeautifulSoup(payload, "html.parser")
                            body = soup.get_text()
                        else:
                            body = payload
                        break
            else:
                payload = email_msg.get_payload(decode=True).decode()
                if email_msg.get_content_type() == "text/html":
                    soup = BeautifulSoup(payload, "html.parser")
                    body = soup.get_text()
                else:
                    body = payload

            symbols = re.findall(r'New symbols:\s*([A-Z,\s]+)\s*were added to\s*(' + re.escape(keyword) + ')', body)
            if symbols:
                for symbol_group in symbols:
                    extracted_symbols = [s.strip() for s in symbol_group[0].split(",") if s.strip()]
                    for symbol in extracted_symbols:
                        stock_data.append([symbol, email_date, symbol_group[1]])

            processed_email_ids.add(num)

        return pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal']).drop_duplicates(subset=['Ticker'], keep='last')

    except Exception as e:
        st.error(f"Error processing emails: {e}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass

# ... rest of the code remains the same ...

        df = pd.DataFrame(stock_data, columns=['Ticker', 'Date', 'Signal'])
        df = df.sort_values(by=['Date', 'Ticker']).drop_duplicates(subset=['Ticker'], keep='last')

        return df

    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=['Ticker', 'Date', 'Signal'])

def plot_intraday_chart(symbol, interval='5m'):
    try:
        # Fetch intraday data
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d', interval=interval)

        if data.empty:
            st.error(f"No data available for {symbol}")
            return

        # Calculate 9 EMA
        data['9EMA'] = data['Close'].ewm(span=9, adjust=False).mean()

        # Get market open time (assuming EST/EDT)
        try:
            start_time = data.index[0].replace(hour=9, minute=30)
            end_time = start_time + timedelta(minutes=30)
            
            first_30_mins = data[(data.index >= start_time) & (data.index <= end_time)]
            
            high_30m = first_30_mins['High'].max() if not first_30_mins.empty else None
            low_30m = first_30_mins['Low'].min() if not first_30_mins.empty else None
        except IndexError:
            st.warning("Not enough data for first 30 minutes calculation")
            high_30m = None
            low_30m = None

        # Create Plotly figure
        fig = go.Figure()

        # Candlestick chart
        fig.add_trace(go.Candlestick(x=data.index,
                                   open=data['Open'],
                                   high=data['High'],
                                   low=data['Low'],
                                   close=data['Close'],
                                   name='Market Data'))

        # Plot 9 EMA
        fig.add_trace(go.Scatter(x=data.index, 
                               y=data['9EMA'], 
                               mode='lines', 
                               name='9 EMA', 
                               line=dict(color='blue', width=2)))

        # Plot first 30 minutes high and low if available
        if high_30m:
            fig.add_hline(y=high_30m, 
                         line_width=1, 
                         line_dash="dash", 
                         line_color="green", 
                         annotation_text="30m High")
        if low_30m:
            fig.add_hline(y=low_30m, 
                         line_width=1, 
                         line_dash="dash", 
                         line_color="red", 
                         annotation_text="30m Low")

        # Update layout with better styling
        fig.update_layout(
            title=f'{symbol} - {interval} Intraday Chart',
            xaxis_title='Time',
            yaxis_title='Price',
            xaxis_rangeslider_visible=False,
            template='plotly_white',  # Clean template
            height=600,  # Fixed height
            margin=dict(t=30, b=30, l=30, r=30)
        )

        # Show the chart
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred while plotting {symbol}: {str(e)}")

def main():
    st.title("Thinkorswim Alerts Analyzer")
    st.write("This app polls your Thinkorswim alerts and analyzes stock data for different keywords.")

    # Add Buy Me a Coffee button using streamlit-extras
    button(username="tosalerts33", floating=False, width=221)

    # Fetch SPY and QQQ prices
    spy_price, qqq_price = get_spy_qqq_prices()

    # Display SPY and QQQ prices
    col1, col2 = st.columns(2)
    with col1:
        if st.button("SPY"):
            plot_intraday_chart("SPY")
        st.metric("SPY Latest Close Price", f"${spy_price}")
    with col2:
        if st.button("QQQ"):
            plot_intraday_chart("QQQ")
        st.metric("QQQ Latest Close Price", f"${qqq_price}")

    # Automatically poll emails and update data
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
                        tooltip_data = TOOLTIPS.get(keyword, {"header": keyword, "description": "No description available."})
                        st.markdown(
                            f"""
                            **{tooltip_data["header"]}** ℹ️  
                            {tooltip_data["description"]}
                            """,
                            unsafe_allow_html=True,
                        )
                        
                        # Extract and process data for the current keyword
                        symbols_df = extract_stock_symbols_from_email(EMAIL_ADDRESS, EMAIL_PASSWORD, SENDER_EMAIL, keyword)
                        if not symbols_df.empty:
                            # Fetch prices for each symbol
                            price_df = fetch_stock_prices(symbols_df)
                            # Merge the fetched prices with the original dataframe
                            merged_df = symbols_df.merge(price_df, on='Ticker', how='left')
                            
                            # Create a collapsible component for each table
                            with st.expander(f"Show {tooltip_data['header']} Data"):
                                st.dataframe(merged_df)
                                # Display the dataframe with clickable links for chart viewing
                                for index, row in merged_df.iterrows():
                                    if st.button(row['Ticker'], key=f"{row['Ticker']}_{keyword}"):
                                        plot_intraday_chart(row['Ticker'])
                                # Add a download button for CSV inside the expander
                                csv = merged_df.to_csv(index=False).encode('utf-8')
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
