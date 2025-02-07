import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_bollinger_bands(df, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    df = df.copy()
    middle_band = df['Close'].rolling(window=window).mean()
    rolling_std = df['Close'].rolling(window=window).std()
    
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

# Set page config
st.set_page_config(layout="wide")

# Streamlit UI
st.title("📈 Technical Analysis Dashboard")

# User input
symbol = st.text_input("Enter Stock Symbol (e.g., AAPL, TSLA, SPY)", "AAPL").upper()

if symbol:
    try:
        # Fetch data
        df = yf.download(symbol, interval="30m", period="20d")
        
        if not df.empty:
            # Calculate indicators
            df = calculate_bollinger_bands(df)
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['RSI'] = calculate_rsi(df)
            df['SMA9'] = df['RSI'].rolling(window=9).mean()
            
            # Create figure
            fig = make_subplots(
                rows=2, 
                cols=1, 
                shared_xaxes=True,
                vertical_spacing=0.08,
                row_heights=[0.7, 0.3],
                subplot_titles=(f'{symbol} Price', 'RSI (14)')
            )

            # Add price candlesticks
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name="Price",
                    increasing_line_color='#00C805',
                    decreasing_line_color='#FF3737',
                    increasing_fillcolor='#00C805',
                    decreasing_fillcolor='#FF3737'
                ),
                row=1, col=1
            )

            # Add Bollinger Bands
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Upper_Band'],
                    line=dict(color='rgba(152, 152, 152, 0.5)', width=1),
                    name="BB Upper",
                    showlegend=True
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Lower_Band'],
                    line=dict(color='rgba(152, 152, 152, 0.5)', width=1),
                    fill='tonexty',
                    fillcolor='rgba(152, 152, 152, 0.1)',
                    name="BB Lower",
                    showlegend=True
                ),
                row=1, col=1
            )

            # Add MA50
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['MA50'],
                    line=dict(color='#2962FF', width=1.5),
                    name="MA 50"
                ),
                row=1, col=1
            )

            # Add RSI
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['RSI'],
                    line=dict(color='#2962FF', width=1.5),
                    name="RSI"
                ),
                row=2, col=1
            )

            # Add RSI SMA
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['SMA9'],
                    line=dict(color='#FF6B6B', width=1.5),
                    name="RSI SMA(9)"
                ),
                row=2, col=1
            )

            # Add RSI levels
            rsi_levels = [
                dict(y=70, color="rgba(255, 55, 55, 0.3)", text="Overbought"),
                dict(y=50, color="rgba(152, 152, 152, 0.3)", text=""),
                dict(y=30, color="rgba(0, 200, 5, 0.3)", text="Oversold")
            ]

            for level in rsi_levels:
                fig.add_shape(
                    type="line",
                    x0=df.index[0],
                    x1=df.index[-1],
                    y0=level["y"],
                    y1=level["y"],
                    line=dict(color=level["color"], width=1, dash="dash"),
                    row=2,
                    col=1
                )

            # Update layout
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=800,
                margin=dict(l=50, r=50, t=50, b=50),
                xaxis_rangeslider_visible=False,
                showlegend=True,
                legend=dict(
                    bgcolor='rgba(255,255,255,0.1)',
                    bordercolor='rgba(255,255,255,0.1)',
                    borderwidth=1,
                    font=dict(size=10),
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )

            # Update axes
            fig.update_xaxes(
                gridcolor='rgba(128,128,128,0.1)',
                zeroline=False,
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.2)',
                row=1, col=1
            )
            
            fig.update_yaxes(
                gridcolor='rgba(128,128,128,0.1)',
                zeroline=False,
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.2)',
                row=1, col=1
            )
            
            fig.update_yaxes(
                gridcolor='rgba(128,128,128,0.1)',
                zeroline=False,
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.2)',
                range=[0, 100],
                row=2, col=1
            )

            # Show plot
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("No data available for this symbol.")
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
