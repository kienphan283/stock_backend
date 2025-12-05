"""
Script to check EOD data in database
"""
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
ROOT_PATH = Path(__file__).resolve().parent.parent.parent
env_path = ROOT_PATH / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add parent directory to path
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2
from datetime import date

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "Web_quan_li_danh_muc"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

print("=" * 60)
print("Checking EOD Data in Database")
print("=" * 60)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check latest trading dates for some stocks
    query = """
        SELECT 
            s.stock_ticker,
            MAX(eod.trading_date) as latest_date,
            COUNT(*) as record_count
        FROM market_data_oltp.stocks AS s
        LEFT JOIN market_data_oltp.stock_eod_prices AS eod ON eod.stock_id = s.stock_id
        WHERE s.stock_ticker IN ('AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA')
            AND s.delisted IS FALSE
        GROUP BY s.stock_ticker
        ORDER BY s.stock_ticker
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print("\nLatest EOD dates for sample stocks:")
    print("-" * 60)
    for row in rows:
        ticker, latest_date, count = row
        print(f"{ticker:6s} | Latest: {latest_date} | Records: {count}")
    
    # Check what dates exist
    query2 = """
        SELECT DISTINCT trading_date
        FROM market_data_oltp.stock_eod_prices
        ORDER BY trading_date DESC
        LIMIT 10
    """
    
    cursor.execute(query2)
    dates = cursor.fetchall()
    
    print("\nLatest 10 trading dates in database:")
    print("-" * 60)
    for (date_val,) in dates:
        print(f"  {date_val}")
    
    print(f"\nToday's date: {date.today()}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

