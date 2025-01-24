import pandas as pd
import numpy as np
import yfinance as yf

# Parameters
length = 14
calc_length = 5
smooth_length = 3

def fetch_stock_data(symbol, interval, period="6mo"):
    """Fetches stock data using yfinance directly."""
    try:
        data = yf.download(symbol, period=period, interval=interval)
        if data.empty:
            print(f"No data received for {symbol} ({interval})")
            return pd.DataFrame()
        return data[['Open', 'Close']].rename(columns={'Open': 'open', 'Close': 'close'})
    except Exception as e:
        print(f"Error fetching data for {symbol} ({interval}): {e}")
        return pd.DataFrame()

def fetch_latest_price(symbol):
    """Fetches the latest price of the stock."""
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")['Close'].iloc[-1]
        return price
    except Exception as e:
        print(f"Error fetching latest price for {symbol}: {e}")
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
    """Analyzes a stock across multiple timeframes."""
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

def sort_stocks_by_signals(df, timeframes):
    """Sort the DataFrame to prioritize Buy and Sell signals as per the desired order."""
    def signal_sort_key(row):
        # Define a priority for the signals
        signal_priority = {
            'Buy': 3,
            'Neutral': 2,
            'Sell': 1,
            'No Data': 0
        }

        # Create a sort key that prioritizes by the order of timeframes (Weekly > Daily > 1 Hour)
        sort_order = (
            signal_priority.get(row["1wk_Signal"], 0),
            signal_priority.get(row["1d_Signal"], 0),
            signal_priority.get(row["60m_Signal"], 0)
        )
        return sort_order

    # Apply the custom sort key and return the sorted DataFrame
    return df.sort_values(by=["1wk_Signal", "1d_Signal", "60m_Signal"], ascending=[False, False, False])

def main():
    symbols = [
        "AAPL", "MSFT", "AMZN", "GOOGL", "QQQ", "NVDA", "TSLA", "META",
        "UNH", "JNJ", "V", "PG", "XOM", "JPM", "MA", "CVX", "HD",
        "LLY", "MRK", "PFE", "KO", "PEP", "AVGO", "COST", "CSCO",
        "ADBE", "PLTR", "NFLX", "TXN", "AMAT", "INTC", "QCOM",
        "HON", "ORCL", "INTU", "MCD", "DIS", "CRM", "ABBV", "ACN",
        "LIN", "DHR", "NEE", "UPS", "TMO", "LOW", "UNP", "IBM",
        "RTX", "BA", "CAT", "MS", "GS", "BLK", "AMD",  "CEG", "VST",
        "HCC", "JNJ", "MPC", "PM", "MO", "TDW", "VAL", "NE", "SLDP", "SHOP", "HSY",
        "RGTI", "LUNR", "FERG", "COIN", "HOOD", "TEM", "MU", "MARA"
    ]
    timeframes = ["60m", "1d", "1wk"]

    rows = []
    for symbol in symbols:
        latest_price = fetch_latest_price(symbol)
        analysis = analyze_stock(symbol, timeframes)
        row = {"Symbol": symbol, "Price": latest_price}
        for timeframe in timeframes:
            row[f"{timeframe}_Signal"] = analysis.get(timeframe, "Error")
        rows.append(row)

    df = pd.DataFrame(rows)

    # Sort the DataFrame based on the custom sorting order
    sorted_df = sort_stocks_by_signals(df, timeframes)

    print("Sorted Stock Analysis Summary")
    print(sorted_df.to_string(index=False))

if __name__ == "__main__":
    main()
