import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import json
import time
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, time
import pytz

# Parameters
length = 14
calc_length = 5
smooth_length = 3

# Webhook URL for Discord
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1332242383458406401/6KXAsHFsvTKgDZyDimQ_ncrBx9vePgsOYxSRjga0mK-Zg2m404r65zzqdyL1bKCQRwVO"

def fetch_stock_data(symbol, interval, period="6mo"):
    """Fetches stock data using yfinance directly."""
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            st.write(f"No data received for {symbol} ({interval})")
            return pd.DataFrame()
        return data[['Open', 'Close']].rename(columns={'Open': 'open', 'Close': 'close'})
    except Exception as e:
        st.write(f"Error fetching data for {symbol} ({interval}): {e}")
        return pd.DataFrame()

def fetch_latest_price(symbol):
    """Fetches the latest price of the stock."""
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")['Close'].iloc[-1]
        return price
    except Exception as e:
        st.write(f"Error fetching latest price for {symbol}: {e}")
        return None

def calculate_signals(stock_data):
    """Calculates buy/sell signals."""
    if stock_data.empty or len(stock_data) < length + smooth_length * 2:
        return pd.Series(dtype=bool), pd.Series(dtype=bool)

    o = stock_data['open'].values
    c = stock_data['close'].values

    data = np.array([sum(np.sign(c[i] - o[max(0, i - j)]) for j in range(length)) for i in range(len(c))]).flatten()
    data_series = pd.Series(data, index=stock_data.index)

    EMA5 = data_series.ewm(span=calc_length, adjust=False).mean()
    Main = EMA5.ewm(span=smooth_length, adjust=False).mean()
    Signal = Main.ewm(span=smooth_length, adjust=False).mean()

    buy_signals = (Main > Signal) & (Main.shift(1) <= Signal)
    sell_signals = (Main < Signal) & (Main.shift(1) >= Signal)

    return buy_signals, sell_signals

def analyze_stock(symbol, timeframes):
    """Analyzes a stock across the specified timeframes."""
    results = {}
    for timeframe in timeframes:
        stock_data = fetch_stock_data(symbol, timeframe)
        if stock_data.empty:
            results[timeframe] = "No Data"
        else:
            buy_signals, sell_signals = calculate_signals(stock_data)
            if not buy_signals.empty and buy_signals.iloc[-1]:
                results[timeframe] = "Buy"
            elif not sell_signals.empty and sell_signals.iloc[-1]:
                results[timeframe] = "Sell"
            else:
                results[timeframe] = "Neutral"
    return results

# File to store last signals
last_signals_file = "last_signals.json"

def save_signals(data):
    """Save the current signals to a JSON file."""
    with open(last_signals_file, 'w') as f:
        json.dump(data, f)

def load_signals():
    """Load the previously saved signals from JSON file."""
    try:
        with open(last_signals_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def send_to_discord(message, table=None):
    """Send message and table to a Discord webhook."""
    payload = {
        "content": message
    }

    if table is not None:
        # Send table as a code block (markdown format) to Discord
        payload["content"] += "\n\n```" + table + "```"
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()  # Check if request was successful
        st.write(f"Message sent to Discord: {message}")  # Confirm in Streamlit
    except requests.exceptions.RequestException as e:
        st.write(f"Error sending to Discord: {e}")  # Display the error in Streamlit

def df_to_markdown(df):
    """Convert a DataFrame to a markdown table format."""
    return df.to_markdown(index=False)

def is_market_open():
    """Check if the current time is within market hours (Monday to Friday, 9:30 AM to 4:00 PM EST)."""
    tz = pytz.timezone('US/Eastern')  # Set timezone to Eastern Time
    now = datetime.now(tz)
    market_open = time(9, 30)  # Market opens at 9:30 AM
    market_close = time(16, 0)  # Market closes at 4:00 PM

    if now.weekday() >= 5:  # Check if it's Saturday (5) or Sunday (6)
        return False

    if market_open <= now.time() <= market_close:  # Check if current time is within market hours
        return True

    return False

def main():
    # Check if the market is open
    if not is_market_open():
        st.write("Market is currently closed. The app will resume during market hours.")
        return

    # Refresh the app every 15 minutes (900000 milliseconds)
    st_autorefresh(interval=900000, key="data_refresh")

    st.title("60-Minute Signal Changes for Trading")

    symbols = [
        "AAPL", "MSFT", "AMZN", "GOOGL", "QQQ", "NVDA", "TSLA", "META","SPY","UVXY","DIA","IWM","COIN"
        # Add more symbols if needed
    ]
    timeframes = ["60m"]  # Only focus on 60-minute timeframe

    rows = []
    trend_changes = []  # List to store stocks with trend changes
    current_signals = {}  # Dictionary to store the current signals

    for symbol in symbols:
        latest_price = fetch_latest_price(symbol)
        analysis = analyze_stock(symbol, timeframes)
        row = {"Symbol": symbol, "Price": latest_price, "60m_Signal": analysis.get("60m", "Error")}
        rows.append(row)

        # Store current signal for the symbol
        current_signals[symbol] = analysis.get("60m", "Error")

        # Load last signals
        last_signals = load_signals()

        # Check if trend changed
        current_signal = current_signals[symbol]
        last_signal = last_signals.get(symbol, "Neutral")

        if current_signal != last_signal:
            trend_changes.append(f"Signal change for {symbol}: {last_signal} -> {current_signal}")
        
    # Send the message to Discord every time
    message = "\n".join(trend_changes) if trend_changes else "No trend changes"
    table = df_to_markdown(pd.DataFrame(rows))  # Convert the DataFrame to markdown format
    send_to_discord(message, table)

    # Highlight stocks where the trend changed
    df = pd.DataFrame(rows)
    st.write("Current 60-Minute Signals for Trading")
    st.dataframe(df)

    # Update the last signals file
    save_signals(current_signals)

if __name__ == "__main__":
    main()
