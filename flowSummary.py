import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import streamlit as st

def fetch_data_from_urls(urls):
    all_data = pd.DataFrame()  # Initialize an empty DataFrame to combine data from all URLs
    for url in urls:
        try:
            # Fetch the CSV data from the URL
            response = requests.get(url)
            response.raise_for_status()  # Raise an error if the request fails
            
            # Check if the response is a CSV file
            if 'text/csv' in response.headers.get('Content-Type', ''):
                # Read the CSV content into a pandas DataFrame
                csv_data = StringIO(response.text)
                df = pd.read_csv(csv_data)

                # Filter out records with Volume less than 100
                df = df[df['Volume'] >= 100]

                # Convert Expiration to datetime and filter out records with the current date
                df['Expiration'] = pd.to_datetime(df['Expiration'])
                current_date = datetime.now().date()
                df = df[df['Expiration'].dt.date != current_date]

                # Append the current DataFrame to the all_data DataFrame
                all_data = pd.concat([all_data, df], ignore_index=True)
            else:
                st.warning(f"Data from {url} is not in CSV format. Skipping...")

        except Exception as e:
            st.error(f"Error fetching or processing data from {url}: {e}")
    
    return all_data

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
        filtered_df.groupby(['Symbol', 'Expiration', 'Strike Price', 'Call/Put','Last Price'])
        .agg({'Volume': 'sum'})
        .reset_index()
    )

    # Order by higher total volume
    summary = summary.sort_values(by='Volume', ascending=False)
    return summary

# Streamlit UI
st.title("Options Flow Analyzer")

# Input: List of URLs
urls = [
    "https://www.cboe.com/us/options/market_statistics/symbol_data/csv/?mkt=cone",
    "https://www.cboe.com/us/options/market_statistics/symbol_data/csv/?mkt=opt",
    "https://www.cboe.com/us/options/market_statistics/symbol_data/csv/?mkt=ctwo",
    "https://www.cboe.com/us/options/market_statistics/symbol_data/csv/?mkt=exo"
]

st.write("Fetching data from the following URLs:", urls)

# Fetch data from all URLs
data = fetch_data_from_urls(urls)

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
