import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Function to calculate pivot points
def calculate_pivots(df):
    high = df['High'].iloc[-1]
    low = df['Low'].iloc[-1]
    close = df['Close'].iloc[-1]
    
    PP = (high + low + close) / 3
    R1 = (2 * PP) - low
    S1 = (2 * PP) - high
    R2 = PP + (high - low)
    S2 = PP - (high - low)
    
    return PP, R1, S1, R2, S2

# Function to calculate RSI
def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Streamlit UI
st.title("📈 Stock Analysis - 30min Chart (20 Days)")

# User input for stock symbol
symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA, SPY)", "AAPL").upper()

# Fetch data
if symbol:
    df = yf.download(symbol, interval="30m", period="20d")

    if not df.empty:
        df['20_MA'] = df['Close'].rolling(window=20).mean()
        df['50_MA'] = df['Close'].rolling(window=50).mean()
        df['RSI'] = calculate_rsi(df)

        # Calculate pivot points
        PP, R1, S1, R2, S2 = calculate_pivots(df)

        # Create subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                            row_heights=[0.7, 0.3])

        # Candlestick chart
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                     low=df['Low'], close=df['Close'], name="Price",
                                     increasing_line_color='green', decreasing_line_color='red'), row=1, col=1)

        # Moving averages
        fig.add_trace(go.Scatter(x=df.index, y=df['20_MA'], mode="lines", name="MA 20", line=dict(color="red")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['50_MA'], mode="lines", name="MA 50", line=dict(color="blue")), row=1, col=1)

        # Pivot points
        pivot_levels = {"Pivot": PP, "R1": R1, "R2": R2, "S1": S1, "S2": S2}
        colors = {"Pivot": "black", "R1": "green", "R2": "green", "S1": "red", "S2": "red"}

        for level, value in pivot_levels.items():
        fig.add_shape(
        type="line",
        x0=df.index[0], x1=df.index[-1], y0=value, y1=value,
        line=dict(color=colors[level], dash="dot"),
        xref="x", yref="y"
        )
        fig.add_annotation(
        x=df.index[-1], y=value, text=level, showarrow=False,
        font=dict(color=colors[level]), align="right",
        xanchor="left", yanchor="middle"
        )


        # RSI Plot
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode="lines", name="RSI", line=dict(color="blue")), row=2, col=1)
        fig.add_hline(y=80, line_dash="dot", line_color="red", annotation_text="Overbought", annotation_position="right", row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="Mid", annotation_position="right", row=2, col=1)
        fig.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Oversold", annotation_position="right", row=2, col=1)

        fig.update_layout(title=f"{symbol} - 30 Min Chart (20 Days)", template="plotly_dark", height=800)

        # Show plot
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("No data available. Please check the symbol and try again.")
