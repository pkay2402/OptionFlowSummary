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
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1332367135023956009/8HH_RiKnSP7R7l7mtFHOB8kJi7ATt0TKZRrh35D82zycKC7JrFVSMpgJUmHrnDQ4mQRw"

# Calculate EMA
def calculate_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

# Calculate Monthly Pivot Points
def calculate_monthly_pivot(data):
    """Calculates the monthly pivot based on High, Low, and Close prices for the current month."""
    data.columns = ['_'.join(filter(None, col)) for col in data.columns]
    ticker = [col.split('_')[1] for col in data.columns if '_' in col][0]
    high_col, low_col, close_col = f'High_{ticker}', f'Low_{ticker}', f'Close_{ticker}'

    if not all(col in data.columns for col in [high_col, low_col, close_col]):
        raise KeyError(f"Missing columns: {high_col}, {low_col}, {close_col}")

    data = data[[high_col, low_col, close_col]].rename(columns={
        high_col: 'High', low_col: 'Low', close_col: 'Close'
    })
    current_month, current_year = datetime.now().month, datetime.now().year
    data = data[(data.index.month == current_month) & (data.index.year == current_year)]

    if data.empty:
        raise ValueError("No data available for the current month.")

    pivot = (data['High'].max() + data['Low'].min() + data['Close'].iloc[-1]) / 3
    return pivot

def fetch_stock_data(symbol, interval, period="6mo"):
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            st.write(f"No data received for {symbol} ({interval})")
            return pd.DataFrame()
        return data[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        st.write(f"Error fetching data for {symbol} ({interval}): {e}")
        return pd.DataFrame()

def fetch_latest_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")['Close'].iloc[-1]
        return price
    except Exception as e:
        st.write(f"Error fetching latest price for {symbol}: {e}")
        return None

def calculate_signals(stock_data):
    if stock_data.empty or len(stock_data) < length + smooth_length * 2:
        return pd.Series(dtype=bool), pd.Series(dtype=bool)

    o, c = stock_data['Open'].values, stock_data['Close'].values
    data = np.array([sum(np.sign(c[i] - o[max(0, i - j)]) for j in range(length)) for i in range(len(c))]).flatten()
    data_series = pd.Series(data, index=stock_data.index)

    EMA5 = data_series.ewm(span=calc_length, adjust=False).mean()
    Main = EMA5.ewm(span=smooth_length, adjust=False).mean()
    Signal = Main.ewm(span=smooth_length, adjust=False).mean()

    buy_signals = (Main > Signal) & (Main.shift(1) <= Signal)
    sell_signals = (Main < Signal) & (Main.shift(1) >= Signal)

    return buy_signals, sell_signals

def analyze_stock(symbol, timeframes):
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

def calculate_indicators(data):
    data['EMA_21'] = calculate_ema(data['Close'], 21)
    data['EMA_50'] = calculate_ema(data['Close'], 50)
    data['EMA_200'] = calculate_ema(data['Close'], 200)
    monthly_pivot = calculate_monthly_pivot(data)
    return data, monthly_pivot

def save_signals(data):
    with open("last_signals.json", 'w') as f:
        json.dump(data, f)

def load_signals():
    try:
        with open("last_signals.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def send_to_discord(message, table=None):
    payload = {"content": message}
    if table:
        table_limit = 1900  # Discord character limit
        table = table[:table_limit] if len(table) > table_limit else table
        payload["content"] += f"\n\n```{table}```"

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        st.write(f"Message sent to Discord: {message}")
    except requests.exceptions.RequestException as e:
        st.write(f"Error sending to Discord: {e}")

def df_to_markdown(df):
    return df.to_markdown(index=False)

def is_market_open():
    tz = pytz.timezone('US/Eastern')
    now, market_open, market_close = datetime.now(tz), time(9, 30), time(16, 0)
    if now.weekday() >= 5:
        return False
    return market_open <= now.time() <= market_close

def main():
    st_autorefresh(interval=14400000, key="data_refresh")

    if not is_market_open():
        st.write("Market is currently closed. The app will resume during market hours.")
        return

    st.title("1D and 5D Signal Changes with Indicators")

    symbols = [
        "AAPL", "AMD", "AMZN", "AVGO", "COIN", "DIA", "GOOGL", "IWM", "META",
        "MSFT", "NVDA", "PANW", "QQQ", "SPY", "TSLA", "TSM", "UNH", "UVXY"
    ]
    timeframes = ["1d", "5d"]

    rows, trend_changes, current_signals = [], [], {}
    last_signals = load_signals()

    for symbol in symbols:
        stock_data = fetch_stock_data(symbol, "1d")
        if stock_data.empty:
            continue

        stock_data, monthly_pivot = calculate_indicators(stock_data)
        latest_price = fetch_latest_price(symbol)
        analysis = analyze_stock(symbol, timeframes)

        row = {
            "Symbol": symbol,
            "Price": latest_price,
            "1D Signal": analysis.get("1d", "Error"),
            "5D Signal": analysis.get("5d", "Error"),
            "EMA_21": stock_data['EMA_21'].iloc[-1] if not stock_data.empty else None,
            "EMA_50": stock_data['EMA_50'].iloc[-1] if not stock_data.empty else None,
            "EMA_200": stock_data['EMA_200'].iloc[-1] if not stock_data.empty else None,
            "Monthly Pivot": monthly_pivot
        }
        rows.append(row)
        current_signals[symbol] = analysis.get("1d", "Error")

        last_signal = last_signals.get(symbol, "Neutral")
        if current_signals[symbol] != last_signal:
            trend_changes.append(f"Signal change for {symbol}: {last_signal} -> {current_signals[symbol]}")

    df = pd.DataFrame(rows)
    st.dataframe(df)

    if st.button("Send Table to Discord"):
        table = df_to_markdown(df)
        send_to_discord("Manual Push of Signals and Indicators to Discord", table)

    save_signals(current_signals)

if __name__ == "__main__":
    main()
