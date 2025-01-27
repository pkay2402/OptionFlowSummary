import streamlit as st
import pandas as pd

# Streamlit App
st.title("NSE Bulk Deals, Block Deals, and Short-Selling Analyzer")
st.write("Upload your CSV files to analyze bulk deals, block deals, and short-selling data.")

# File uploaders
st.sidebar.header("Upload CSV Files")
bulk_deals_file = st.sidebar.file_uploader("Upload Bulk Deals CSV", type=["csv"])
block_deals_file = st.sidebar.file_uploader("Upload Block Deals CSV", type=["csv"])
short_selling_file = st.sidebar.file_uploader("Upload Short-Selling CSV", type=["csv"])

# Function to load CSV data
def load_csv(file):
    if file is not None:
        return pd.read_csv(file)
    return pd.DataFrame()

# Load data
bulk_deals_df = load_csv(bulk_deals_file)
block_deals_df = load_csv(block_deals_file)
short_selling_df = load_csv(short_selling_file)

# Display Bulk Deals Data
st.write("### Bulk Deals Data")
if not bulk_deals_df.empty:
    st.dataframe(bulk_deals_df)
else:
    st.warning("No bulk deals data uploaded.")

# Display Block Deals Data
st.write("### Block Deals Data")
if not block_deals_df.empty:
    st.dataframe(block_deals_df)
else:
    st.warning("No block deals data uploaded.")

# Display Short-Selling Data
st.write("### Short-Selling Data")
if not short_selling_df.empty:
    st.dataframe(short_selling_df)
else:
    st.warning("No short-selling data uploaded.")

# Add filters for Bulk Deals
st.sidebar.header("Bulk Deals Filters")
if not bulk_deals_df.empty:
    selected_stock_bulk = st.sidebar.text_input("Enter Stock Symbol for Bulk Deals (e.g., INFY):")
    if selected_stock_bulk:
        filtered_bulk_df = bulk_deals_df[bulk_deals_df["Symbol"] == selected_stock_bulk]
        st.write(f"### Filtered Bulk Deals Data for {selected_stock_bulk}")
        st.dataframe(filtered_bulk_df)

# Add filters for Block Deals
st.sidebar.header("Block Deals Filters")
if not block_deals_df.empty:
    selected_stock_block = st.sidebar.text_input("Enter Stock Symbol for Block Deals (e.g., INFY):")
    if selected_stock_block:
        filtered_block_df = block_deals_df[block_deals_df["Symbol"] == selected_stock_block]
        st.write(f"### Filtered Block Deals Data for {selected_stock_block}")
        st.dataframe(filtered_block_df)

# Add filters for Short-Selling
st.sidebar.header("Short-Selling Filters")
if not short_selling_df.empty:
    selected_stock_short = st.sidebar.text_input("Enter Stock Symbol for Short-Selling (e.g., INFY):")
    if selected_stock_short:
        filtered_short_df = short_selling_df[short_selling_df["Symbol"] == selected_stock_short]
        st.write(f"### Filtered Short-Selling Data for {selected_stock_short}")
        st.dataframe(filtered_short_df)

# Add download buttons
st.sidebar.header("Download Data")
if not bulk_deals_df.empty and st.sidebar.button("Download Bulk Deals as CSV"):
    csv_bulk = bulk_deals_df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download Bulk Deals CSV",
        data=csv_bulk,
        file_name="bulk_deals.csv",
        mime="text/csv",
    )

if not block_deals_df.empty and st.sidebar.button("Download Block Deals as CSV"):
    csv_block = block_deals_df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download Block Deals CSV",
        data=csv_block,
        file_name="block_deals.csv",
        mime="text/csv",
    )

if not short_selling_df.empty and st.sidebar.button("Download Short-Selling as CSV"):
    csv_short = short_selling_df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download Short-Selling CSV",
        data=csv_short,
        file_name="short_selling.csv",
        mime="text/csv",
    )

# Add visualizations
st.write("### Visualizations")

# Bulk Deals Visualization (example: total deals by stock)
if not bulk_deals_df.empty:
    st.write("#### Total Bulk Deals by Stock")
    bulk_deals_count = bulk_deals_df["Symbol"].value_counts()
    st.bar_chart(bulk_deals_count)

# Block Deals Visualization (example: total deals by stock)
if not block_deals_df.empty:
    st.write("#### Total Block Deals by Stock")
    block_deals_count = block_deals_df["Symbol"].value_counts()
    st.bar_chart(block_deals_count)

# Short-Selling Visualization (example: total short-selling by stock)
if not short_selling_df.empty:
    st.write("#### Total Short-Selling by Stock")
    short_selling_count = short_selling_df["Symbol"].value_counts()
    st.bar_chart(short_selling_count)
