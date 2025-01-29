import os
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, time
import pytz

# Parameters (match these with your main script)
SYMBOLS = ["SPY", "QQQ", "NVDA", "TSLA"]
INTERVAL = "30m"
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')  # Use environment variable
LENGTH = 14
CALC_LENGTH = 5
SMOOTH_LENGTH = 3

def is_market_open():
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    market_open = time(9, 30)
    market_close = time(16, 0)
    return now.weekday() < 5 and market_open <= now.time() <= market_close

def fetch_stock_data(symbol, interval, period="1d"):
    try:
        data = yf.download(symbol, period=period, interval=interval)
        return data[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def calculate_signals(stock_data):
    if stock_data.empty or len(stock_data) < LENGTH + SMOOTH_LENGTH * 2:
        return pd.Series(dtype=bool), pd.Series(dtype=bool)

    o, c = stock_data['Open'].values, stock_data['Close'].values
    data = np.array([sum(np.sign(c[i] - o[max(0, i - j)]) for j in range(LENGTH)) for i in range(len(c))]).flatten()
    data_series = pd.Series(data, index=stock_data.index)

    EMA5 = data_series.ewm(span=CALC_LENGTH, adjust=False).mean()
    Main = EMA5.ewm(span=SMOOTH_LENGTH, adjust=False).mean()
    Signal = Main.ewm(span=SMOOTH_LENGTH, adjust=False).mean()

    buy_signals = (Main > Signal) & (Main.shift(1) <= Signal)
    sell_signals = (Main < Signal) & (Main.shift(1) >= Signal)

    return buy_signals, sell_signals

def send_to_discord(message):
    payload = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"Message sent to Discord: {message}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Discord: {e}")

def main():
    if not is_market_open():
        print("Market is closed.")
        return

    for symbol in SYMBOLS:
        stock_data = fetch_stock_data(symbol, INTERVAL, period="1d")
        if not stock_data.empty:
            buy_signals, sell_signals = calculate_signals(stock_data)
            if not buy_signals.empty and buy_signals.iloc[-1]:
                send_to_discord(f"Buy signal detected for {symbol}")
            if not sell_signals.empty and sell_signals.iloc[-1]:
                send_to_discord(f"Sell signal detected for {symbol}")

if __name__ == "__main__":
    main()
