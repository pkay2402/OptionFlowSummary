import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from math import ceil

# Set page configuration for responsiveness
st.set_page_config(layout="wide")

# Initialize session state for chart display
if 'chart_symbol' not in st.session_state:
    st.session_state['chart_symbol'] = None

def fetch_stock_data(symbol, period="1d", interval="15m"):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, interval=interval)
        if hist.empty:
            raise ValueError(f"No data available for {symbol}")
        
        # Calculate VWAP
        hist['Cumulative_Volume'] = hist['Volume'].cumsum()
        hist['Cumulative_PV'] = (hist['Close'] * hist['Volume']).cumsum()
        hist['VWAP'] = hist['Cumulative_PV'] / hist['Cumulative_Volume']
        
        today_data = hist.iloc[-1]
        open_price = round(today_data["Open"], 2)
        high_price = round(hist["High"].iloc[-1], 2)
        low_price = round(hist["Low"].iloc[-1], 2)
        current_price = round(today_data["Close"], 2)
        vwap = round(hist['VWAP'].iloc[-1], 2)

        # Daily Pivot Calculation
        daily_pivot = round((high_price + low_price + current_price) / 3, 2)

        # EMAs
        ema_9 = round(hist["Close"].ewm(span=9, adjust=False).mean().iloc[-1], 2)
        ema_21 = round(hist["Close"].ewm(span=21, adjust=False).mean().iloc[-1], 2)
        ema_50 = round(hist["Close"].ewm(span=50, adjust=False).mean().iloc[-1], 2)

        # KeyMAs Logic
        if current_price > ema_9 and current_price > ema_21 and current_price > ema_50:
            key_mas = "Bullish"
        elif current_price < ema_9 and current_price < ema_21 and current_price < ema_50:
            key_mas = "Bearish"
        else:
            key_mas = "Mixed"

        # Determine Price_Vwap
        if current_price > vwap and current_price > open_price:
            direction = "Bullish"
        elif current_price < vwap and current_price < open_price:
            direction = "Bearish"
        else:
            direction = "Neutral"

        return pd.DataFrame({
            "Symbol": [symbol],
            "Current Price": [current_price],
            "VWAP": [vwap],
            "Daily Pivot": [daily_pivot],
            "Price_Vwap": [direction],
            "KeyMAs": [key_mas]
        }), hist.round(2)
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame(), pd.DataFrame()

def plot_candlestick(data, symbol):
    fig = go.Figure()
    
    # Add candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name=symbol
    ))
    
    # Add VWAP
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['VWAP'],
        name='VWAP',
        line=dict(color='purple', width=2)
    ))

    fig.update_layout(
        title=f'{symbol} Candlestick Chart with VWAP',
        yaxis_title='Price',
        template='plotly_white',
        height=600,
        xaxis_rangeslider_visible=False
    )
    
    # Format y-axis to show 2 decimal places
    fig.update_layout(yaxis_tickformat='.2f')
    
    return fig

# Streamlit UI
st.title("📊 Live Market Dashboard")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    stock_list = st.text_area("Enter Stock Symbols (comma separated)", "SPY, QQQ, UVXY, AAPL, GOOGL, META, NVDA, TSLA, AMZN, COIN").upper()
    symbols = [s.strip() for s in stock_list.split(",")]
    
    time_frames = {
        "1 Day": "1d",
        "5 Days": "5d",
        "1 Month": "1mo",
        "3 Months": "3mo",
        "6 Months": "6mo",
        "1 Year": "1y",
        "2 Years": "2y",
        "5 Years": "5y"
    }
    selected_timeframe = st.selectbox("Choose Time Frame", list(time_frames.keys()), index=0)
    period = time_frames[selected_timeframe]

    intervals = ["1m", "5m", "15m", "30m", "1h", "1d"]
    selected_interval = st.selectbox("Choose Interval", intervals, index=2)

    auto_refresh = st.checkbox("Auto Refresh every 5 mins")

# Main content area
st.subheader(f"📈 Stock Data for {selected_timeframe} ({selected_interval} interval)")

# Create columns for the layout
col1, col2 = st.columns([2, 1])

with col1:
    # Display table
    all_data = pd.DataFrame()
    stock_histories = {}
    
    # Calculate number of columns needed for buttons (3 buttons per row)
    num_symbols = len(symbols)
    num_cols = 3
    num_rows = ceil(num_symbols / num_cols)
    
    # Create button grid
    for i in range(num_rows):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            idx = i * num_cols + j
            if idx < num_symbols:
                symbol = symbols[idx]
                data, history = fetch_stock_data(symbol, period=period, interval=selected_interval)
                if not data.empty:
                    all_data = pd.concat([all_data, data], ignore_index=True)
                    stock_histories[symbol] = history
                    if cols[j].button(f'📈 {symbol}', key=f'btn_{symbol}'):
                        st.session_state['chart_symbol'] = symbol

    # Style and display the DataFrame with color coding for both columns
    def color_columns(val):
        if val in ["Bullish", "Bullish"]:
            return 'background-color: #90EE90; color: black'  # Light green
        elif val in ["Bearish", "Bearish"]:
            return 'background-color: #FF7F7F; color: black'  # Light red
        elif val in ["Neutral", "Mixed"]:
            return 'background-color: #D3D3D3; color: black'  # Light gray
        return ''

    styled_df = all_data.style.format({
        'Current Price': '{:.2f}',
        'VWAP': '{:.2f}',
        'Daily Pivot': '{:.2f}'
    }).applymap(color_columns, subset=['Price_Vwap', 'KeyMAs'])
    
    st.dataframe(styled_df, use_container_width=True)

with col2:
    # Display chart based on session state
    if st.session_state['chart_symbol'] and st.session_state['chart_symbol'] in stock_histories:
        symbol = st.session_state['chart_symbol']
        st.plotly_chart(plot_candlestick(stock_histories[symbol], symbol), use_container_width=True)

# Manual Refresh Button
if st.button("🔄 Refresh Data"):
    st.rerun()

# Auto-refresh logic
if auto_refresh:
    st.info("Auto-refresh active. Data will update every 5 minutes.")
    import time
    time.sleep(300)
    st.rerun()

# Styling
st.markdown("""
<style>
.stApp {
    max-width: 100%;
}
div[data-testid="stHorizontalBlock"] {
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)
