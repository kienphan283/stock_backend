import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.data_loader import StockDataLoader
import json

def print_json(data, title):
    """Pretty print JSON data"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print('='*50)
    print(json.dumps(data, indent=2))

def main():
    """Test all data loader functions"""
    print("Testing Stock Data Loader for APP ticker")
    print("Loading data from CSV files...")

    # Initialize loader
    loader = StockDataLoader()

    # Get data summary first
    print_json(loader.get_data_summary(), "DATA SUMMARY")

    # Test each function
    print_json(loader.get_quote(), "STOCK QUOTE")

    print_json(loader.get_company_profile(), "COMPANY PROFILE")

    price_history = loader.get_price_history("3m")
    # Truncate price data for readability
    if price_history.get("series") and len(price_history["series"][0]["data"]) > 5:
        price_history["series"][0]["data"] = price_history["series"][0]["data"][:5] + ["... truncated"]
        price_history["dates"] = price_history["dates"][:5] + ["... truncated"]
    print_json(price_history, "PRICE HISTORY (3 months) - First 5 entries")

    dividends = loader.get_dividends()
    print_json(dividends[:3] if len(dividends) > 3 else dividends, "DIVIDENDS - First 3 entries")

    news = loader.get_news(limit=3)
    print_json(news, "NEWS - Limited to 3 articles")

    financials = loader.get_financials()
    # Truncate financial data for readability
    if financials.get("incomeStatement") and len(financials["incomeStatement"]) > 3:
        financials["incomeStatement"] = financials["incomeStatement"][:3] + [{"name": "... truncated"}]
    if financials.get("balanceSheet") and len(financials["balanceSheet"]) > 3:
        financials["balanceSheet"] = financials["balanceSheet"][:3] + [{"name": "... truncated"}]
    if financials.get("cashFlow") and len(financials["cashFlow"]) > 3:
        financials["cashFlow"] = financials["cashFlow"][:3] + [{"name": "... truncated"}]
    print_json(financials, "FINANCIALS - First 3 entries per section")

    earnings = loader.get_earnings()
    print_json(earnings, "EARNINGS")

    # Test data refresh (optional - commented out to avoid API calls)
    # print("\nTesting data refresh...")
    # refresh_success = loader.refresh_data()
    # print(f"Data refresh successful: {refresh_success}")

if __name__ == "__main__":
    main()
