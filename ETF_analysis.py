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

def calculate_relative_strength(symbol_hist, spy_hist, lookback=20):
    common_dates = symbol_hist.index.intersection(spy_hist.index)
    if len(common_dates) < 2:
        return 0, "N/A"
    
    symbol_change = symbol_hist['Close'].loc[common_dates].pct_change(periods=lookback).iloc[-1]
    spy_change = spy_hist['Close'].loc[common_dates].pct_change(periods=lookback).iloc[-1]
    
    if spy_change != 0:
        rs = ((1 + symbol_change) / (1 + spy_change) - 1) * 100
        rs_status = "Strong" if rs > 0 else "Weak"
        return round(rs, 2), rs_status
    return 0, "N/A"

st.title("📊 Sector ETF Market Leadership Last 30 days")

# User input for ETFs
etf_list = "XLC, XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLRE, XLK, XLU, SMH, QQQ, IGV, XLV, IWM, DIA, XBI, ARKK"
symbols = [s.strip() for s in etf_list.split(",")]

# Fetch SPY data for benchmarking
spy_data = yf.Ticker("SPY").history(period="1mo", interval="1d")
all_data = []

for symbol in symbols:
    etf_data = yf.Ticker(symbol).history(period="1mo", interval="1d")
    if not etf_data.empty:
        rs_value, rs_status = calculate_relative_strength(etf_data, spy_data)
        all_data.append({"Symbol": symbol, "Relative Strength vs SPY": rs_value, "Status": rs_status})

df = pd.DataFrame(all_data)
strongest_etfs = df[df["Status"] == "Strong"].sort_values(by="Relative Strength vs SPY", ascending=False)
weakest_etfs = df[df["Status"] == "Weak"].sort_values(by="Relative Strength vs SPY", ascending=True)

st.subheader("📈 Leading ETFs (Market Favoring)")
st.dataframe(strongest_etfs, use_container_width=True)

st.subheader("📉 Weak ETFs (Market Avoiding)")
st.dataframe(weakest_etfs, use_container_width=True)
