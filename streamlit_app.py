import pandas as pd
from datetime import datetime
import streamlit as st

def load_data(file):
    try:
        # Read the uploaded CSV content into a pandas DataFrame
        df = pd.read_csv(file)

        # Filter out records with Volume less than 100
        df = df[df['Volume'] >= 100]

        # Convert Expiration to datetime and filter out records with current date
        df['Expiration'] = pd.to_datetime(df['Expiration'])
        current_date = datetime.now().date()
        df = df[df['Expiration'].dt.date != current_date]

        return df
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame()

def summarize_flows(df, symbol, call_put=None, expiration=None):
    # Filter by selected symbol
    filtered_df = df[df['Symbol'] == symbol]
    
    # Apply optional Call/Put filter
    if call_put:
        filtered_df = filtered_df[filtered_df['Call/Put'] == call_put]
    
    # Apply optional Expiration filter
    if expiration:
        filtered_df = filtered_df[filtered_df['Expiration'].dt.date == expiration]
    
    # Summarize by expiration, strike price, call/put, and total volume
    summary = (
        filtered_df.groupby(['Symbol', 'Expiration', 'Strike Price', 'Call/Put'])
        .agg({'Volume': 'sum'})
        .reset_index()
    )

    # Order by higher total volume
    summary = summary.sort_values(by='Volume', ascending=False)
    return summary

# Streamlit UI
st.title("Options Flow Analyzer")

# Input: Upload the CSV file
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    # Load data from uploaded CSV
    data = load_data(uploaded_file)

    if not data.empty:
        # Show available symbols for filtering
        symbols = sorted(data['Symbol'].unique())
        selected_symbol = st.selectbox("Select Symbol to Analyze", symbols)

        # Optional filter for Call/Put
        call_put_options = ['All', 'C', 'P']
        selected_call_put = st.selectbox("Select Call/Put", call_put_options)

        # Optional filter for Expiration
        expiration_dates = sorted(data['Expiration'].dt.date.unique())
        selected_expiration = st.selectbox("Select Expiration Date", [None] + expiration_dates)

        # Apply filters and summarize
        if selected_symbol:
            if selected_call_put == 'All':
                selected_call_put = None  # Set to None to filter out if "All" is selected
            
            summary = summarize_flows(data, selected_symbol, selected_call_put, selected_expiration)
            st.subheader(f"Summary of Flows for {selected_symbol}")
            st.dataframe(summary)

            # Option to download the summary
            csv = summary.to_csv(index=False)
            st.download_button(
                label="Download Summary as CSV",
                data=csv,
                file_name=f"{selected_symbol}_summary.csv",
                mime="text/csv"
            )
