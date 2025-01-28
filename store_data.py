import sqlite3
import pandas as pd

def store_data(df, table_name='alerts'):
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    
    # Create table if not exists
    c.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}
                  (symbol text, date text, signal text, alert_price real, today_price real, return_alert real)''')
    
    # Convert DataFrame to a list of tuples for bulk insert
    data = [tuple(row) for row in df[['Symbol', 'Alert Date', 'Signal', 'Alert Date Close', 'Today Close', 'Return Alert(%)']].itertuples(index=False, name=None)]
    
    # Insert data
    c.executemany(f'INSERT OR REPLACE INTO {table_name} VALUES (?, ?, ?, ?, ?, ?)', data)
    conn.commit()
    
    # Close connection
    conn.close()

def fetch_data(table_name='alerts'):
    conn = sqlite3.connect('alerts.db')
    df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY date DESC", conn)
    conn.close()
    return df
