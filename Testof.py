import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import os
import numpy as np
import yfinance as yf

# Custom RSI calculation using Pandas
def calculate_rsi(series, period=14):
    """Calculate RSI without TA-Lib."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Function to load and process the CSV file
def score_flow(flow_row):
    """
    Score each options flow based on multiple factors, optimized for profitability.
    Higher score = stronger signal with better risk/reward.
    """
    score = 0
    
    # Premium scaled by risk/reward
    premium = flow_row['Premium Price']
    move_pct = abs((flow_row['Strike Price'] - flow_row['Reference Price']) / flow_row['Reference Price'] * 100)
    rr_ratio = move_pct / (premium / flow_row['Size']) if flow_row['Size'] > 0 else 1  # Simplified risk/reward
    score += min(premium / 50000, 5) * min(rr_ratio / 10, 2)  # Cap at 5, adjusted by R:R (max 2x boost)
    
    # Aggressiveness
    side_code = flow_row.get('Side Code', 'N/A')
    score += {'AA': 5, 'BB': 4, 'A': 2, 'B': 1}.get(side_code, 0)
    
    # Flags
    score += 2 if flow_row['Is Unusual'] == 'Yes' else 0
    score += 3 if flow_row['Is Golden Sweep'] == 'Yes' else 0
    score += 1 if flow_row['Is Opening Position'] == 'Yes' else 0
    
    # OTM Move
    if 5 <= move_pct <= 15:
        score += 3
    elif 15 < move_pct <= 30:
        score += 2
    elif move_pct <= 50:
        score += 1
    
    # Expiration Timing
    days = flow_row['Days Until Expiration']
    if days <= 7:
        score += 2
    elif days <= 30:
        score += 1.5
    elif days <= 60:
        score += 0.5
    
    # Liquidity Penalty
    if flow_row['Size'] < 100:
        score -= 2
    
    # Technical Boost (if RSI available)
    if 'RSI' in flow_row.index and pd.notna(flow_row['RSI']):
        if flow_row['Contract Type'] == 'CALL' and flow_row['RSI'] > 60:
            score += 1
        elif flow_row['Contract Type'] == 'PUT' and flow_row['RSI'] < 40:
            score += 1
    
    return max(score, 0)  # No negative scores

def add_technical_context(df):
    """Add RSI and 5-day change for each ticker using yfinance and Pandas RSI."""
    for ticker in df['Ticker'].unique():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="20d")  # Extend to 20d for 14-period RSI
            if not hist.empty and len(hist) >= 14:  # Need at least 14 days for RSI
                rsi = calculate_rsi(hist['Close'])[-1]  # Get the latest RSI value
                change_5d = (hist['Close'][-1] - hist['Close'][-5]) / hist['Close'][-5] * 100  # Last 5 days
                df.loc[df['Ticker'] == ticker, 'RSI'] = rsi
                df.loc[df['Ticker'] == ticker, '5d_Change'] = change_5d
        except Exception as e:
            st.warning(f"Failed to fetch data for {ticker}: {e}")
    return df

def check_x_sentiment(ticker):
    """Placeholder for X sentiment analysis. Replace with real API."""
    return 50  # Neutral default (0-100 scale)

def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        
        # Map columns by position if needed
        if not all(col in df.columns for col in ['Ticker', 'Expiration Date', 'Contract Type']):
            positional_mapping = {
                'Trade ID': 0, 'Trade Time': 1, 'Ticker': 2, 'Expiration Date': 3,
                'Days Until Expiration': 4, 'Strike Price': 5, 'Contract Type': 6,
                'Reference Price': 7, 'Size': 8, 'Option Price': 9, 'Ask Price': 10,
                'Bid Price': 11, 'Premium Price': 12, 'Trade Type': 13,
                'Consolidation Type': 14, 'Is Unusual': 15, 'Is Golden Sweep': 16,
                'Is Opening Position': 17, 'Money Type': 18
            }
            new_columns = df.columns.tolist()
            renamed_df = df.copy()
            renamed_df.columns = [positional_mapping.get(i, col) for i, col in enumerate(new_columns)]
            df = renamed_df

        # Convert and clean data
        df['Expiration Date'] = pd.to_datetime(df['Expiration Date'])
        numeric_columns = ['Days Until Expiration', 'Strike Price', 'Reference Price', 
                          'Size', 'Option Price', 'Premium Price']
        for col in numeric_columns:
            if col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        for col in ['Trade Type', 'Ticker', 'Contract Type', 'Is Unusual', 'Is Golden Sweep', 'Is Opening Position', 'Money Type']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                if col == 'Ticker':
                    df[col] = df[col].str.upper()
        
        # Filter for OTM and opening positions
        df = df[(df['Money Type'] == 'OUT_THE_MONEY') & (df['Is Opening Position'] == 'Yes')]
        
        # Add technical context
        df = add_technical_context(df)
        
        # Add X sentiment (placeholder)
        df['X_Sentiment'] = df['Ticker'].apply(check_x_sentiment)
        
        # Calculate flow scores
        df['Flow Score'] = df.apply(score_flow, axis=1)
        
        return df
    except Exception as e:
        st.error(f"Failed to load CSV: {e}")
        return None

def identify_unusual_volume_patterns(df):
    """Identify unusual volume patterns in specific tickers."""
    ticker_groups = df.groupby('Ticker')
    unusual_activity = []
    exclude_tickers = ['SPY', 'QQQ', 'SPX', 'IWM']
    
    for ticker, group in ticker_groups:
        if ticker in exclude_tickers:
            continue
        total_premium = group['Premium Price'].sum()
        flow_count = len(group)
        if flow_count < 3 or total_premium < 300000:
            continue
        call_premium = group[group['Contract Type'] == 'CALL']['Premium Price'].sum()
        put_premium = group[group['Contract Type'] == 'PUT']['Premium Price'].sum()
        if min(call_premium, put_premium) > 0:
            ratio = max(call_premium, put_premium) / min(call_premium, put_premium)
            direction = "CALL" if call_premium > put_premium else "PUT"
            if ratio >= 3:
                unusual_activity.append({
                    'Ticker': ticker, 'Direction': direction, 'Ratio': ratio,
                    'Total Premium': total_premium, 'Flow Count': flow_count
                })
    
    return pd.DataFrame(unusual_activity).sort_values('Total Premium', ascending=False)

def detect_repeat_flows(df):
    """Detect repeat flows in the same ticker/direction."""
    grouped = df.groupby(['Ticker', 'Contract Type'])
    repeat_flows = []
    
    for (ticker, contract_type), group in grouped:
        if len(group) >= 3:
            total_premium = group['Premium Price'].sum()
            avg_score = group['Flow Score'].mean()
            repeat_flows.append({
                'Ticker': ticker, 'Direction': contract_type, 'Flow Count': len(group),
                'Total Premium': total_premium, 'Avg Score': avg_score
            })
    
    return pd.DataFrame(repeat_flows).sort_values('Avg Score', ascending=False)

def get_best_plays(df, min_score=12, max_days=30):
    """Filter for the best actionable plays."""
    best_plays = df[
        (df['Flow Score'] >= min_score) &
        (df['Days Until Expiration'] <= max_days) &
        (df['Size'] >= 100) &
        (((df['RSI'] > 60) & (df['Contract Type'] == 'CALL')) | 
         ((df['RSI'] < 40) & (df['Contract Type'] == 'PUT')))
    ].sort_values('Flow Score', ascending=False).head(10)
    return best_plays

def generate_newsletter(df, top_n_aggressive_flows, premium_price, side_codes, tickers, sort_by, include_scoring=True):
    if df is None or df.empty:
        return "No data available for newsletter generation."
    
    current_date = pd.to_datetime("today")
    current_date_str = current_date.strftime("%b %d, %Y")
    exclude_tickers = ['SPX', 'SPY', 'IWM', 'QQQ']
    
    newsletter = f"📈 OUT-THE-MONEY OPTIONS FLOW SUMMARY - {current_date_str} 📈\n\n"
    
    # Market Update
    newsletter += "=== MARKET UPDATE (OTM FLOWS) ===\n"
    market_df = df[df['Ticker'].isin(['SPY', 'QQQ'])].copy()
    if market_df.empty:
        newsletter += "No OTM market index flows detected.\n\n"
    else:
        max_expiry = current_date + pd.Timedelta(days=7)
        market_df = market_df[(market_df['Expiration Date'] <= max_expiry) & 
                              (market_df['Expiration Date'] > current_date)]
        if market_df.empty:
            newsletter += "No near-term OTM flows for SPY/QQQ.\n"
        else:
            call_premium = market_df[market_df['Contract Type'] == 'CALL']['Premium Price'].sum()
            put_premium = market_df[market_df['Contract Type'] == 'PUT']['Premium Price'].sum()
            total_volume = market_df['Size'].sum()
            pc_ratio = put_premium / call_premium if call_premium > 0 else float('inf')
            sentiment = "BULLISH 🟢" if pc_ratio < 0.7 else "BEARISH 🔴" if pc_ratio > 1.5 else "NEUTRAL ⚪"
            newsletter += f"Market Sentiment: {sentiment}\nTotal Premium: ${call_premium + put_premium:,.2f}\n"
            newsletter += f"Total Contracts: {total_volume:,}\nPut/Call Ratio: {pc_ratio:.2f}\n\n"
    
    # High Conviction Plays
    newsletter += "=== 🔥 HIGH CONVICTION PLAYS 🔥 ===\n"
    high_conviction = get_best_plays(df)
    if high_conviction.empty:
        newsletter += "No high conviction plays detected.\n\n"
    else:
        for _, flow in high_conviction.iterrows():
            move_pct = abs((flow['Strike Price'] - flow['Reference Price']) / flow['Reference Price'] * 100)
            side = flow.get('Side Code', 'N/A')
            sentiment = ("🟢" if flow['Contract Type'] == 'CALL' and side in ['A', 'AA'] else
                         "🔴" if flow['Contract Type'] == 'CALL' and side in ['B', 'BB'] else
                         "🔴" if flow['Contract Type'] == 'PUT' and side in ['A', 'AA'] else
                         "🟢" if flow['Contract Type'] == 'PUT' and side in ['B', 'BB'] else "N/A")
            flags = [f for c, f in [('Is Unusual', 'UNUSUAL'), ('Is Golden Sweep', 'GOLDEN SWEEP')] if flow[c] == 'Yes']
            flags_str = f" [{' '.join(flags)}]" if flags else ""
            score_str = f" [Score: {flow['Flow Score']:.1f}]" if include_scoring else ""
            rsi_str = f" [RSI: {flow['RSI']:.1f}]" if pd.notna(flow['RSI']) else ""
            
            newsletter += (f"• {flow['Ticker']} {flow['Contract Type']} ${flow['Strike Price']:,.2f} "
                         f"exp {flow['Expiration Date'].date()} - ${flow['Premium Price']:,.2f} "
                         f"({flow['Size']} contracts, {move_pct:.1f}% move, {sentiment}, {side}){flags_str}{score_str}{rsi_str}\n")
    newsletter += "\n"
    
    # Unusual Volume Patterns
    unusual_volume = identify_unusual_volume_patterns(df)
    if not unusual_volume.empty:
        newsletter += "=== 🧐 UNUSUAL VOLUME PATTERNS ===\n"
        for _, pattern in unusual_volume.head(5).iterrows():
            newsletter += (f"• {pattern['Ticker']}: Strong {pattern['Direction']} bias "
                         f"({pattern['Ratio']:.1f}:1), ${pattern['Total Premium']:,.2f}, {pattern['Flow Count']} flows\n")
        newsletter += "\n"
    
    # Repeat Flows
    repeat_flows = detect_repeat_flows(df)
    if not repeat_flows.empty:
        newsletter += "=== 🔄 REPEAT FLOW PATTERNS ===\n"
        for _, pattern in repeat_flows.head(5).iterrows():
            newsletter += (f"• {pattern['Ticker']}: {pattern['Flow Count']} {pattern['Direction']} flows, "
                         f"${pattern['Total Premium']:,.2f}, avg score: {pattern['Avg Score']:.1f}\n")
        newsletter += "\n"
    
    # Standard OTM Flows
    newsletter += "=== OTM FLOWS ===\n"
    aggressive_df = df[
        (df['Expiration Date'] > current_date) &
        (df['Premium Price'] >= premium_price) &
        (df['Side Code'].isin(side_codes)) &
        (df['Ticker'].isin(tickers)) &
        (~df['Ticker'].isin(exclude_tickers))
    ].sort_values(by=[sort_by, 'Ticker'], ascending=[False, True])
    
    if aggressive_df.empty:
        newsletter += "No aggressive OTM flows detected.\n\n"
    else:
        newsletter += f"Top Aggressive Flows (Sorted by {sort_by}):\n"
        for _, flow in aggressive_df.head(top_n_aggressive_flows).iterrows():
            move_pct = abs((flow['Strike Price'] - flow['Reference Price']) / flow['Reference Price'] * 100)
            side = flow.get('Side Code', 'N/A')
            sentiment = ("🟢" if flow['Contract Type'] == 'CALL' and side in ['A', 'AA'] else
                         "🔴" if flow['Contract Type'] == 'CALL' and side in ['B', 'BB'] else
                         "🔴" if flow['Contract Type'] == 'PUT' and side in ['A', 'AA'] else
                         "🟢" if flow['Contract Type'] == 'PUT' and side in ['B', 'BB'] else "N/A")
            flags = [f for c, f in [('Is Unusual', 'UNUSUAL'), ('Is Golden Sweep', 'GOLDEN SWEEP')] if flow[c] == 'Yes']
            flags_str = f" [{' '.join(flags)}]" if flags else ""
            score_str = f" [Score: {flow['Flow Score']:.1f}]" if include_scoring else ""
            
            newsletter += (f"• {flow['Ticker']} {flow['Contract Type']} ${flow['Strike Price']:,.2f} "
                         f"exp {flow['Expiration Date'].date()} - ${flow['Premium Price']:,.2f} "
                         f"({flow['Size']} contracts, {move_pct:.1f}% move, {sentiment}, {side}){flags_str}{score_str}\n")
        newsletter += "\n"
    
    newsletter += "Only for educational purposes!"
    return newsletter

def send_to_discord(content, webhook_url):
    """Send newsletter to Discord."""
    try:
        payload = {"content": content[:2000]}  # Discord 2000 char limit
        response = requests.post(webhook_url, json=payload)
        return "Newsletter sent to Discord!" if response.status_code == 204 else f"Failed to send: {response.text}"
    except Exception as e:
        return f"Error sending to Discord: {e}"

def main():
    st.set_page_config(page_title="Smart Options Flow Analyzer", page_icon="📈", layout="wide")
    
    default_webhook = os.environ.get("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1341974407102595082/HTKke4FEZIQe6Xd9AUv2IgVDJp0yx89Uhosv_iM-7BZBTn2jk2T-dP_TFbX2PgMuF75D")
    
    st.title("🔍 Smart Options Flow Analyzer")
    st.markdown("Generate a newsletter summarizing today's OUT-THE-MONEY options flows")
    
    uploaded_file = st.file_uploader("Upload your options flow CSV file", type=["csv"])
    
    if uploaded_file is not None:
        with st.spinner("Processing options data..."):
            df = load_csv(uploaded_file)
            
            if df is not None:
                # Flow Statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Premium", f"${df['Premium Price'].sum():,.2f}")
                with col2:
                    st.metric("Total Flows", f"{len(df):,}")
                with col3:
                    st.metric("Average Flow Score", f"{df['Flow Score'].mean():.2f}")
                
                # Top Tickers by Premium
                st.subheader("Top Tickers by Premium")
                top_tickers = df.groupby('Ticker')['Premium Price'].sum().sort_values(ascending=False).head(10)
                st.bar_chart(top_tickers)
                
                # Score Distribution
                st.subheader("Flow Score Distribution")
                hist_values = np.histogram(df['Flow Score'].dropna(), bins=10, range=(0, 20))[0]
                st.bar_chart(hist_values)
                
                # Newsletter Generation
                st.subheader("Options Flow Newsletter")
                top_n_aggressive_flows = st.number_input("Number of Flows to Display", min_value=1, max_value=100, value=50)
                premium_price = st.number_input("Minimum Premium Price", min_value=0, value=100000)
                side_codes = st.multiselect("Side Codes", options=['A', 'AA', 'B', 'BB'], default=['AA', 'BB'])
                with st.expander("Select Tickers", expanded=False):
                    tickers = st.multiselect("Tickers", options=df['Ticker'].unique().tolist(), default=df['Ticker'].unique().tolist())
                sort_by = st.selectbox("Sort By", options=["Flow Score", "Premium Price", "Ticker"])
                include_scoring = st.checkbox("Include Flow Scores in Newsletter", value=True)
                
                with st.expander("Discord Integration"):
                    webhook_url = st.text_input("Discord Webhook URL", value=default_webhook, type="password")
                    send_to_discord_enabled = st.checkbox("Send newsletter to Discord", value=False)
                
                if st.button("Generate Newsletter", type="primary"):
                    with st.spinner("Generating newsletter..."):
                        newsletter_content = generate_newsletter(df, top_n_aggressive_flows, premium_price, side_codes, tickers, sort_by, include_scoring)
                        st.markdown(f"```\n{newsletter_content}\n```")
                        
                        if send_to_discord_enabled:
                            with st.spinner("Sending newsletter to Discord..."):
                                discord_result = send_to_discord(newsletter_content, webhook_url)
                                st.info(discord_result)

if __name__ == "__main__":
    main()
