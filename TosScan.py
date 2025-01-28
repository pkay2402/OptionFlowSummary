import streamlit as st
import time
import imaplib
import email
from email.header import decode_header
import pandas as pd

# Constants
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
IMAP_SERVER = "imap.gmail.com"
KEYWORDS = ["Buy", "Sell"]
POLL_INTERVAL = 10  # Poll every 10 seconds
processed_email_ids = set()

# Email fetching function
def fetch_emails():
    try:
        with imaplib.IMAP4_SSL(IMAP_SERVER) as mail:
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            mail.select("inbox")
            _, search_data = mail.search(None, 'FROM', '"alerts@thinkorswim.com"')
            email_ids = search_data[0].split()
            
            st.write(f"Total emails fetched: {len(email_ids)}")  # Debug: Display total emails
            emails = []
            
            for email_id in email_ids:
                if email_id in processed_email_ids:
                    continue  # Skip already processed emails
                _, data = mail.fetch(email_id, "(RFC822)")
                for response_part in data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        emails.append(msg)
                        processed_email_ids.add(email_id)
                        
            st.write(f"Emails to process: {len(emails)}")  # Debug: Emails left to process
            return emails
    except Exception as e:
        st.write(f"Error fetching emails: {e}")  # Debug: Show error details
        return []

# Extract stock symbols from emails
def extract_stock_symbols(emails, keyword):
    try:
        data = []
        for msg in emails:
            subject = msg["subject"]
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
            else:
                body = msg.get_payload(decode=True).decode()
            
            st.write(f"Processing email: Subject: {subject}, Body: {body[:50]}")  # Debug: Preview email
            if keyword in body:
                data.append({"Subject": subject, "Body": body})
        
        st.write(f"Extracted data: {data}")  # Debug: Display extracted data
        return pd.DataFrame(data)
    except Exception as e:
        st.write(f"Error extracting stock symbols: {e}")  # Debug: Show error details
        return pd.DataFrame()

# Main app logic
def main():
    st.title("📈 Thinkorswim Alerts Analyzer")
    st.markdown("---")
    st.write("Polling for new emails...")

    while True:
        emails = fetch_emails()
        if emails:
            for keyword in KEYWORDS:
                df = extract_stock_symbols(emails, keyword)
                if not df.empty:
                    st.dataframe(df)  # Display extracted data in the app
        else:
            st.write("No new emails found.")  # Debug: Inform no emails found
        st.write("Polling completed. Next update in 10 seconds.")
        time.sleep(POLL_INTERVAL)
        st.experimental_rerun()

if __name__ == "__main__":
    main()
