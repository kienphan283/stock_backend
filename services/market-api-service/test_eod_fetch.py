"""
Test script to check EOD fetch logic
"""
import sys
from pathlib import Path

# Add parent directory to path
ROOT_PATH = Path(__file__).resolve().parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from utils.market_hours import get_latest_trading_date
from services.quote_service import QuoteService
from datetime import datetime, date

print("=" * 60)
print("Testing EOD Fetch Logic")
print("=" * 60)

# Test 1: Check latest trading date
print("\n1. Testing get_latest_trading_date():")
try:
    latest_date = get_latest_trading_date()
    print(f"   ✅ Latest trading date: {latest_date}")
    print(f"   Today: {date.today()}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Check if EOD fetch is triggered
print("\n2. Testing QuoteService.get_latest_eod_batch():")
try:
    service = QuoteService()
    # Test with a few tickers
    test_tickers = ["AAPL", "MSFT", "GOOGL"]
    print(f"   Testing with tickers: {test_tickers}")
    
    result = service.get_latest_eod_batch(test_tickers, auto_fetch=True)
    print(f"   ✅ Got EOD data for {len(result)} tickers")
    
    for ticker, data in result.items():
        print(f"   - {ticker}: price={data.get('price')}, volume={data.get('volume')}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

