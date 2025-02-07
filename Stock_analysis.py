import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_bollinger_bands(df, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    # Make sure to use copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Calculate middle band (20-day SMA)
    middle_band = df['Close'].rolling(window=window).mean()
    
    # Calculate standard deviation
    rolling_std = df['Close'].rolling(window=window).std()
    
    # Calculate upper and lower bands
    df['MA20'] = middle_band
    df['Upper_Band'] = middle_band + (rolling_std * num_std)
    df['Lower_Band'] = middle_band - (rolling_std * num_std)
    
    return df

def calculate_rsi(df, period=14):
    """Calculate RSI"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Streamlit UI
st.title("📈 Technical Analysis Dashboard")

# User input
symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA, SPY)", "AAPL").upper()

if symbol:
    # Fetch data
    try:
        df = yf.download(symbol, interval="30m", period="20d")
        
        if not df.empty:
            # Calculate indicators
            df = calculate_bollinger_bands(df)
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['RSI'] = calculate_rsi(df)
            df['SMA9'] = df['RSI'].rolling(window=9).mean()  # For RSI
            
            # Create figure
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                               vertical_spacing=0.06,
                               row_heights=[0.7, 0.3])

            # Main price chart
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name="Price",
                    increasing_line_color='#26A69A',
                    decreasing_line_color='#EF5350'
                ),
                row=1, col=1
            )

            # Add Bollinger Bands
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Upper_Band'],
                    line=dict(color='rgba(250, 128, 114, 0.3)'),
                    name="Upper BB",
                    fill=None
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Lower_Band'],
                    line=dict(color='rgba(250, 128, 114, 0.3)'),
                    name="Lower BB",
                    fill='tonexty'
                ),
                row=1, col=1
            )

            # Add MA50
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['MA50'],
                    line=dict(color='#2962FF', width=1),
                    name="MA 50"
                ),
                row=1, col=1
            )

            # RSI Plot
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['RSI'],
                    line=dict(color='#2962FF', width=1),
                    name="RSI"
                ),
                row=2, col=1
            )

            # Add RSI SMA
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['SMA9'],
                    line=dict(color='#FF6B6B', width=1),
                    name="RSI SMA(9)"
                ),
                row=2, col=1
            )

            # Add RSI levels
            for level in [30, 50, 70]:
                fig.add_shape(
                    type="line",
                    x0=df.index[0],
                    x1=df.index[-1],
                    y0=level,
                    y1=level,
                    line=dict(
                        color="gray",
                        width=1,
                        dash="dot"
                    ),
                    row=2,
                    col=1
                )

            # Update layout
            fig.update_layout(
                title=f"{symbol} Technical Analysis",
                template="plotly_white",
                height=800,
                xaxis_rangeslider_visible=False,
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )

            # Update y-axes
            fig.update_yaxes(title_text="Price", row=1, col=1)
            fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])

            # Update colors and grid
            fig.update_xaxes(gridcolor="lightgray", gridwidth=0.5)
            fig.update_yaxes(gridcolor="lightgray", gridwidth=0.5)

            # Show plot
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("No data available for this symbol.")
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
