import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

# Function to fetch stock data
def get_stock_data(symbol):
    data = yf.download(symbol, period="20d", interval="30m")
    return data

# Function to calculate pivot points
def calculate_pivots(data):
    prev_day = data.iloc[-49:-1]  # Extract previous day's data (49 candles of 30m = ~1 day)
    high, low, close = prev_day["High"].max(), prev_day["Low"].min(), prev_day["Close"].iloc[-1]
    
    PP = (high + low + close) / 3
    R1, S1 = (2 * PP) - low, (2 * PP) - high
    R2, S2 = PP + (high - low), PP - (high - low)
    
    return PP, R1, S1, R2, S2

# Function to calculate RSI
def calculate_rsi(data, period=14):
    delta = data["Close"].diff()
    gain, loss = delta.copy(), delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = abs(loss.rolling(window=period).mean())

    RS = avg_gain / avg_loss
    RSI = 100 - (100 / (1 + RS))
    
    return RSI

# Streamlit UI
st.title("Stock Pivot Point & RSI Analysis")

symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA, SPY):", "AAPL")

if symbol:
    data = get_stock_data(symbol)
    
    if not data.empty:
        PP, R1, S1, R2, S2 = calculate_pivots(data)
        data["RSI"] = calculate_rsi(data)

        # Plot Candlestick Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"],
            name="Price"
        ))

        # Add Moving Averages
        data["MA20"] = data["Close"].rolling(window=20).mean()
        data["MA50"] = data["Close"].rolling(window=50).mean()
        fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], mode="lines", name="MA 20", line=dict(color="red")))
        fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], mode="lines", name="MA 50", line=dict(color="blue")))

        # Add Pivot Points
        fig.add_hline(y=PP, line_dash="dot", line_color="black", annotation_text="Pivot", annotation_position="right")
        fig.add_hline(y=R1, line_dash="dot", line_color="green", annotation_text="R1", annotation_position="right")
        fig.add_hline(y=S1, line_dash="dot", line_color="red", annotation_text="S1", annotation_position="right")
        fig.add_hline(y=R2, line_dash="dot", line_color="green", annotation_text="R2", annotation_position="right")
        fig.add_hline(y=S2, line_dash="dot", line_color="red", annotation_text="S2", annotation_position="right")

        fig.update_layout(title=f"{symbol} - 30 Min Chart (20 Days)", xaxis_rangeslider_visible=False)

        # RSI Plot
        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Scatter(x=data.index, y=data["RSI"], mode="lines", name="RSI", line=dict(color="blue")))
        rsi_fig.add_hline(y=80, line_dash="dot", line_color="red", annotation_text="Overbought", annotation_position="right")
        rsi_fig.add_hline(y=50, line_dash="dot", line_color="black", annotation_text="Mid", annotation_position="right")
        rsi_fig.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Oversold", annotation_position="right")

        rsi_fig.update_layout(title=f"{symbol} - RSI Indicator")

        # Display charts
        st.plotly_chart(fig)
        st.plotly_chart(rsi_fig)

    else:
        st.error("No data found! Check the stock symbol.")
