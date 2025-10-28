#!/usr/bin/env python3
"""
Import financial data from Alpha Vantage API into PostgreSQL
Using existing data.py script
"""

import os
import sys

# Set environment variables if not set
if not os.getenv("ALPHA_VANTAGE_API_KEY"):
    print("⚠️  ALPHA_VANTAGE_API_KEY not set. Please set it in .env.local or environment")
    print("   You can get a free API key from: https://www.alphavantage.co/support/#api-key")
    sys.exit(1)

# Import the existing module
from services.data import import_all_statements

def main():
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    # List of companies to import
    companies = [
        "AAPL",    # Apple
        "MSFT",    # Microsoft  
        "GOOGL",   # Alphabet (Google)
        "AMZN",    # Amazon
        "NVDA",    # Nvidia
        "META",    # Meta Platforms
        "TSLA",    # Tesla
        "IBM"      # IBM
    ]
    
    print("=" * 60)
    print(f"IMPORTING DATA FROM ALPHA VANTAGE API")
    print(f"Companies: {len(companies)}")
    print("=" * 60 + "\n")
    
    for idx, symbol in enumerate(companies, 1):
        print(f"[{idx}/{len(companies)}] Importing {symbol}...")
        try:
            import_all_statements(symbol, api_key)
            print(f"✓ {symbol} completed\n")
        except Exception as e:
            print(f"✗ {symbol} failed: {e}\n")
            continue
    
    print("=" * 60)
    print("✓ IMPORT COMPLETED!")
    print("=" * 60)

if __name__ == "__main__":
    main()

