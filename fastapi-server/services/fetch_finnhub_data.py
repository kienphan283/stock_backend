import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Constants
BASE_URL = "https://finnhub.io/api/v1"
RATE_LIMIT_DELAY = 1.0  # seconds between requests
TICKER = "APP"
MAX_RETRIES = 3
BACKOFF_FACTOR = 2

class FinnhubDataFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.call_count = 0
        self.start_time = time.time()

    def make_api_call(self, endpoint, params=None):
        """Make API call with rate limiting and error handling"""
        if params is None:
            params = {}

        params['token'] = self.api_key
        url = f"{BASE_URL}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                print(f"Making API call to: {endpoint}")
                response = self.session.get(url, params=params)
                self.call_count += 1

                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ Success: {endpoint}")
                    time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
                    return data
                elif response.status_code == 429:
                    # Rate limit exceeded - exponential backoff
                    wait_time = BACKOFF_FACTOR ** attempt
                    print(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 401:
                    raise ValueError("Invalid API key")
                else:
                    print(f"API error: {response.status_code} - {response.text}")
                    return None

            except requests.exceptions.RequestException as e:
                print(f"Network error on attempt {attempt + 1}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None
                time.sleep(BACKOFF_FACTOR ** attempt)

        return None

    def save_to_csv(self, data, filename):
        """Save data to CSV file"""
        if data is None or (isinstance(data, list) and len(data) == 0):
            print(f"No data to save for {filename}")
            # Create empty CSV with headers only
            if filename == "stock_quote.csv":
                headers = ["current_price", "change", "percent_change", "high", "low", "open", "previous_close", "timestamp"]
            elif filename == "company_profile.csv":
                headers = ["name", "ticker", "exchange", "country", "currency", "industry", "market_cap", "ipo_date", "logo", "shares_outstanding", "weburl", "phone"]
            elif filename == "stock_candles.csv":
                headers = ["date", "open", "high", "low", "close", "volume"]
            elif filename == "dividends.csv":
                headers = ["date", "amount", "adjusted_amount", "currency", "declared_date", "pay_date", "record_date"]
            elif filename == "company_news.csv":
                headers = ["id", "headline", "summary", "source", "url", "datetime", "category", "image"]
            elif filename == "financials_metrics.csv":
                headers = ["pe_ratio", "eps", "market_cap", "revenue_ttm", "profit_margin", "roe", "roa", "debt_to_equity", "current_ratio", "quick_ratio"]
            elif filename == "earnings.csv":
                headers = ["period", "actual_eps", "estimate_eps", "surprise", "surprise_percent", "actual_revenue", "estimate_revenue"]
            elif filename == "financials_reported.csv":
                headers = ["period", "year", "quarter", "report_type", "line_item_name", "value", "unit", "currency"]
            else:
                headers = []

            pd.DataFrame(columns=headers).to_csv(filename, index=False)
            print(f"Created empty CSV: {filename}")
            return 0

        try:
            if isinstance(data, pd.DataFrame):
                df = data
            else:
                df = pd.DataFrame(data)

            df.to_csv(filename, index=False)
            row_count = len(df)
            print(f"Saved {row_count} rows to {filename}")
            return row_count
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return 0

    def fetch_quote(self):
        """Fetch current stock quote"""
        data = self.make_api_call(f"/quote", {"symbol": TICKER})
        if data:
            quote_data = {
                "current_price": data.get("c", 0),
                "change": data.get("d", 0),
                "percent_change": data.get("dp", 0),
                "high": data.get("h", 0),
                "low": data.get("l", 0),
                "open": data.get("o", 0),
                "previous_close": data.get("pc", 0),
                "timestamp": datetime.fromtimestamp(data.get("t", 0)).strftime("%Y-%m-%d %H:%M:%S") if data.get("t") else ""
            }
            return [quote_data]
        return None

    def fetch_company_profile(self):
        """Fetch company profile"""
        data = self.make_api_call(f"/stock/profile2", {"symbol": TICKER})
        if data:
            profile_data = {
                "name": data.get("name", ""),
                "ticker": data.get("ticker", ""),
                "exchange": data.get("exchange", ""),
                "country": data.get("country", ""),
                "currency": data.get("currency", ""),
                "industry": data.get("finnhubIndustry", ""),
                "market_cap": data.get("marketCapitalization", 0),
                "ipo_date": data.get("ipo", ""),
                "logo": data.get("logo", ""),
                "shares_outstanding": data.get("shareOutstanding", 0),
                "weburl": data.get("weburl", ""),
                "phone": data.get("phone", "")
            }
            return [profile_data]
        return None

    def fetch_stock_candles(self):
        """Fetch historical price data (3 months)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        from_timestamp = int(start_date.timestamp())
        to_timestamp = int(end_date.timestamp())

        data = self.make_api_call(f"/stock/candle", {
            "symbol": TICKER,
            "resolution": "D",
            "from": from_timestamp,
            "to": to_timestamp
        })

        if data and data.get("s") == "ok":
            candles = []
            timestamps = data.get("t", [])
            opens = data.get("o", [])
            highs = data.get("h", [])
            lows = data.get("l", [])
            closes = data.get("c", [])
            volumes = data.get("v", [])

            for i in range(len(timestamps)):
                candles.append({
                    "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                    "open": opens[i] if i < len(opens) else 0,
                    "high": highs[i] if i < len(highs) else 0,
                    "low": lows[i] if i < len(lows) else 0,
                    "close": closes[i] if i < len(closes) else 0,
                    "volume": volumes[i] if i < len(volumes) else 0
                })
            return candles
        return None

    def fetch_dividends(self):
        """Fetch dividend history"""
        data = self.make_api_call(f"/stock/dividend", {
            "symbol": TICKER,
            "from": "2020-01-01",
            "to": "2025-12-31"
        })

        if data and isinstance(data, list):
            dividends = []
            for dividend in data:
                dividends.append({
                    "date": dividend.get("date", ""),
                    "amount": dividend.get("amount", 0),
                    "adjusted_amount": dividend.get("adjustedAmount", 0),
                    "currency": dividend.get("currency", ""),
                    "declared_date": dividend.get("declarationDate", ""),
                    "pay_date": dividend.get("payDate", ""),
                    "record_date": dividend.get("recordDate", "")
                })
            return dividends
        return None

    def fetch_company_news(self):
        """Fetch recent news (1 month)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        data = self.make_api_call(f"/company-news", {
            "symbol": TICKER,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        })

        if data and isinstance(data, list):
            news = []
            for article in data:
                news.append({
                    "id": article.get("id", ""),
                    "headline": article.get("headline", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "datetime": datetime.fromtimestamp(article.get("datetime", 0)).strftime("%Y-%m-%d %H:%M:%S") if article.get("datetime") else "",
                    "category": article.get("category", ""),
                    "image": article.get("image", "")
                })
            return news
        return None

    def fetch_financials_metrics(self):
        """Fetch financial metrics"""
        data = self.make_api_call(f"/stock/metric", {
            "symbol": TICKER,
            "metric": "all"
        })

        if data and data.get("metric"):
            metrics = data.get("metric", {})
            metrics_data = {
                "pe_ratio": metrics.get("peBasicExclExtraTTM", 0),
                "eps": metrics.get("epsBasicExclExtraAnnual", 0),
                "market_cap": metrics.get("marketCapitalization", 0),
                "revenue_ttm": metrics.get("revenueTTM", 0),
                "profit_margin": metrics.get("netProfitMarginTTM", 0),
                "roe": metrics.get("roeTTM", 0),
                "roa": metrics.get("roaTTM", 0),
                "debt_to_equity": metrics.get("totalDebt/totalEquityQuarterly", 0),
                "current_ratio": metrics.get("currentRatioQuarterly", 0),
                "quick_ratio": metrics.get("quickRatioQuarterly", 0)
            }
            return [metrics_data]
        return None

    def fetch_earnings(self):
        """Fetch earnings data"""
        data = self.make_api_call(f"/stock/earnings", {"symbol": TICKER})

        if data and isinstance(data, list):
            earnings = []
            for earning in data:
                earnings.append({
                    "period": earning.get("period", ""),
                    "actual_eps": earning.get("actual", 0),
                    "estimate_eps": earning.get("estimate", 0),
                    "surprise": earning.get("surprise", 0),
                    "surprise_percent": earning.get("surprisePercent", 0),
                    "actual_revenue": earning.get("actualRevenue", 0),
                    "estimate_revenue": earning.get("estimateRevenue", 0)
                })
            return earnings
        return None

    def fetch_financials_reported(self):
        """Fetch detailed financial statements"""
        data = self.make_api_call(f"/stock/financials-reported", {
            "symbol": TICKER,
            "freq": "quarterly"
        })

        if data and data.get("data"):
            financials = []
            for report in data.get("data", []):
                report_info = report.get("report", {})
                year = report.get("year", 0)
                quarter = report.get("quarter", 0)

                # Process different report types (IC = Income Statement, BS = Balance Sheet, CF = Cash Flow)
                for report_type, statements in report_info.items():
                    if isinstance(statements, list):
                        for statement in statements:
                            financials.append({
                                "period": f"{year}Q{quarter}",
                                "year": year,
                                "quarter": quarter,
                                "report_type": report_type,
                                "line_item_name": statement.get("concept", ""),
                                "value": statement.get("value", 0),
                                "unit": statement.get("unit", ""),
                                "currency": "USD"  # Default currency
                            })
            return financials
        return None

def main():
    """Main execution function"""
    load_dotenv()
    api_key = os.getenv("FINNHUB_API_KEY")

    if not api_key:
        raise ValueError("FINNHUB_API_KEY not found in .env file. Please create a .env file with your API key.")

    print(f"Starting data fetch for {TICKER}...")
    print(f"Base URL: {BASE_URL}")
    print(f"Rate limit: {RATE_LIMIT_DELAY} seconds between requests")
    print("-" * 50)

    fetcher = FinnhubDataFetcher(api_key)
    files_created = {}

    try:
        # Fetch all data
        print("1. Fetching stock quote...")
        quote_data = fetcher.fetch_quote()
        files_created["stock_quote.csv"] = fetcher.save_to_csv(quote_data, "stock_quote.csv")

        print("\n2. Fetching company profile...")
        profile_data = fetcher.fetch_company_profile()
        files_created["company_profile.csv"] = fetcher.save_to_csv(profile_data, "company_profile.csv")

        print("\n3. Fetching stock candles (3 months)...")
        candles_data = fetcher.fetch_stock_candles()
        files_created["stock_candles.csv"] = fetcher.save_to_csv(candles_data, "stock_candles.csv")

        print("\n4. Fetching dividends...")
        dividends_data = fetcher.fetch_dividends()
        files_created["dividends.csv"] = fetcher.save_to_csv(dividends_data, "dividends.csv")

        print("\n5. Fetching company news (1 month)...")
        news_data = fetcher.fetch_company_news()
        files_created["company_news.csv"] = fetcher.save_to_csv(news_data, "company_news.csv")

        print("\n6. Fetching financial metrics...")
        metrics_data = fetcher.fetch_financials_metrics()
        files_created["financials_metrics.csv"] = fetcher.save_to_csv(metrics_data, "financials_metrics.csv")

        print("\n7. Fetching earnings...")
        earnings_data = fetcher.fetch_earnings()
        files_created["earnings.csv"] = fetcher.save_to_csv(earnings_data, "earnings.csv")

        print("\n8. Fetching detailed financials...")
        financials_data = fetcher.fetch_financials_reported()
        files_created["financials_reported.csv"] = fetcher.save_to_csv(financials_data, "financials_reported.csv")

    except Exception as e:
        print(f"Error during data fetching: {e}")

    # Print summary
    total_time = time.time() - fetcher.start_time
    print("\n" + "="*50)
    print("FETCH SUMMARY")
    print("="*50)
    print(f"Ticker: {TICKER}")
    print(f"Total API calls made: {fetcher.call_count}")
    print(f"Total time taken: {total_time:.2f} seconds")
    print(f"Average time per call: {total_time/max(fetcher.call_count, 1):.2f} seconds")
    print("\nFiles created:")

    total_rows = 0
    for filename, row_count in files_created.items():
        print(f"  • {filename}: {row_count} rows")
        total_rows += row_count

    print(f"\nTotal rows across all files: {total_rows}")
    print(f"All files saved to: {os.getcwd()}")

if __name__ == "__main__":
    main()
