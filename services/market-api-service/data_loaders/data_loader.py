"""
CSV-backed data loader used by several API services at runtime.

NOTE:
- This module is imported by production services (e.g. summary, news, dividends, etc.)
  and should be treated as runtime-critical until those services are refactored to rely
  solely on database-backed data.
"""

import pandas as pd
import json
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CURRENT_FILE_PATH = Path(__file__).resolve()
ENV_PATH = CURRENT_FILE_PATH.parents[2] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

class StockDataLoader:
    """Load real stock data from CSV files"""

    def __init__(self, ticker: str = "APP", data_dir: str = "./data"):
        # Validate ticker: allow A-Z, 0-9, -, ^, . (e.g., ^GSPC, BRK.B, AAPL)
        # Relaxed validation to support indices and special tickers
        if not ticker or not isinstance(ticker, str) or len(ticker) > 10:
            raise ValueError(f"Invalid ticker format: {ticker}")
        
        # Check for valid characters (alphanumeric + special chars)
        import re
        if not re.match(r'^[A-Z0-9\-\^\.]+$', ticker):
            raise ValueError(f"Ticker contains invalid characters: {ticker}")
        self.ticker = ticker
        self.data_dir = data_dir

        # Database configuration
        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }

    def _file_exists(self, filename: str) -> bool:
        """Check if CSV file exists"""
        return os.path.exists(os.path.join(self.data_dir, filename))

    def _safe_read_csv(self, filename: str) -> Optional[pd.DataFrame]:
        """Safely read CSV file, return None if not found or empty"""
        try:
            file_path = os.path.join(self.data_dir, filename)
            if not os.path.exists(file_path):
                return None
            df = pd.read_csv(file_path)
            return df if not df.empty else None
        except Exception as e:
            return None

    def _format_number(self, value: Any, decimals: int = 2) -> float:
        """Format number with specified decimal places"""
        try:
            if pd.isna(value) or value is None:
                return 0.0
            return round(float(value), decimals)
        except (ValueError, TypeError):
            return 0.0

    def _format_date_iso(self, date_str: str) -> str:
        """Convert date string to ISO 8601 format with timezone"""
        try:
            if pd.isna(date_str) or not date_str:
                return datetime.now(timezone.utc).isoformat()

            # Try different date formats
            formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue

            # If no format matches, return current time
            return datetime.now(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    def get_quote(self) -> Dict[str, Any]:
        """Load quote data and format for API response"""
        # print(f"[DEBUG] StockDataLoader.get_quote called for {self.ticker}")
        
        # USER REQUEST: Disabled mock data fallback
        df = None # self._safe_read_csv("stock_quote.csv")

        if df is None or df.empty:
            # print(f"[DEBUG] stock_quote.csv usage disabled or empty")
            # If no CSV, we return zeros, but we still try DB below to get company metadata
            pass

        try:
            conn = psycopg2.connect(**self.DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Query company data from database
            cursor.execute("""
                SELECT 
                    company_id as ticker,
                    company_name as name,
                    exchange,
                    currency,
                    market_cap,
                    dividend_yield
                FROM company
                WHERE company_id = %s
            """, (self.ticker,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                # Handle 0.0 values correctly by checking for None
                market_cap_raw = result.get('market_cap')
                market_cap = self._format_number(market_cap_raw) if market_cap_raw is not None else 185000000000.0

                div_yield_raw = result.get('dividend_yield')
                div_yield = self._format_number(div_yield_raw) if div_yield_raw is not None else 1.25

                # Get extended data (PE, EPS) from CSV if available
                pe = 0.0
                eps = 0.0
                if df is not None and not df.empty:
                    # Column names in CSV are lower case: ticker,current_price,change,percent_change,high,low,open,previous_close,pe,eps
                    print(f"[DEBUG] Loaded stock_quote.csv with {len(df)} rows")
                    row = df[df['ticker'] == self.ticker]
                    if not row.empty:
                        pe_raw = row.iloc[0].get('pe', 0)
                        eps_raw = row.iloc[0].get('eps', 0)
                        print(f"[DEBUG] Found {self.ticker} in CSV. Raw PE: {pe_raw}, Raw EPS: {eps_raw}")
                        pe = self._format_number(pe_raw)
                        eps = self._format_number(eps_raw)
                    else:
                        print(f"[DEBUG] Ticker {self.ticker} NOT found in stock_quote.csv. Available tickers: {df['ticker'].tolist()[:5]}...")
                else:
                    print(f"[DEBUG] stock_quote.csv is None or empty in {self.data_dir}")

                return {
                    "name": result['name'],
                    "ticker": result['ticker'],
                    "exchange": result['exchange'] or "NYSE",
                    "country": "US",
                    "currency": result['currency'] or "USD",
                    "industry": "Technology",  # Default since not in table
                    "marketCap": market_cap,
                    "ipoDate": "",
                    "logo": "",
                    "sharesOutstanding": 0.0,
                    "website": "",
                    "phone": "",
                    "dividendYield": div_yield,
                    "latestQuarter": datetime.now().strftime("%Y-%m-%d"), # Today
                    "pe": pe,
                    "eps": eps
                }
        except Exception as e:
            pass
        
        # Try reading from CSV
        df = self._safe_read_csv("company_profile.csv")
        if df is not None and not df.empty:
            # Filter by ticker to ensure exact match
            if 'ticker' in df.columns:
                df = df[df['ticker'] == self.ticker]

            if not df.empty:
                row = df.iloc[0]
                return {
                    "name": str(row.get('name', f"{self.ticker} Corporation")),
                    "ticker": str(row.get('ticker', self.ticker)),
                    "exchange": str(row.get('exchange', "NYSE")),
                    "country": "US",
                    "currency": "USD",
                    "industry": str(row.get('industry', "Technology")),
                    "marketCap": self._format_number(row.get('market_cap', 0)),
                    "dividendYield": self._format_number(row.get('dividend_yield', 0), 4),
                    "latestQuarter": str(row.get('latest_quarter', '')),
                    "logo": str(row.get('logo', '')),
                    "sector": str(row.get('sector', 'Technology')),
                    "ipoDate": "",
                    "sharesOutstanding": 0.0,
                    "website": str(row.get('website', '')),
                    "phone": ""
                }

    def _get_fallback_profile(self) -> Dict[str, Any]:
        """Return a basic fallback profile structure"""
        return {
            "name": f"{self.ticker} Corporation",
            "ticker": self.ticker,
            "exchange": "NASDAQ",
            "industry": "Technology",
            "sector": "Technology", 
            "marketCap": 150000000000,
            "ipoDate": "1980-12-12",
            "logo": "https://logo.clearbit.com/apple.com",
            "phone": "+1 408-996-1010",
            "website": "https://www.apple.com",
            "description": "Mock description because data was missing.",
            "currency": "USD",
            "country": "US",
            "sharesOutstanding": 16000000000,
            "dividendYield": 1.5,
            "pe": 0.0,
            "eps": 0.0,
            "beta": 1.0,
            "latestQuarter": datetime.now().strftime("%Y-%m-%d"),
            "revenueGrowth": 0.0,
            "netIncomeGrowth": 0.0,
            "fcfGrowth": 0.0
        }

    # Load company profile data
    def get_company_profile(self):
        try:
            logger.warning(f"[DEBUG] get_company_profile called for {self.ticker}. CWD: {os.getcwd()}, DataDir: {self.data_dir}")
            if not self._file_exists('company_profile.csv'):
                logger.warning(f"[DEBUG] company_profile.csv not found via _file_exists")
                return self._get_fallback_profile()

            df = self._safe_read_csv('company_profile.csv')
            if df is None or df.empty:
                return self._get_fallback_profile()
            
            # Since company_profile usually contains one row per file/ticker in this context
            # Or if it's a shared file, filter by ticker
            record = None
            if 'ticker' in df.columns:
               # Normalize ticker for matching
               df['ticker'] = df['ticker'].astype(str).str.strip().str.upper()
               target_ticker = str(self.ticker).strip().upper()
               
               logger.warning(f"[DEBUG] Matching profile for {target_ticker} in {df['ticker'].head().tolist()}")
               
               record_df = df[df['ticker'] == target_ticker]
               if not record_df.empty:
                   record = record_df.iloc[0]
               else:
                   logger.warning(f"[DEBUG] Profile for {target_ticker} not found in CSV")
                   return self._get_fallback_profile()
            else:
                # If no ticker column, assume single-record file
                record = df.iloc[0]

            def safe_get(key, default=""):
                 val = record.get(key, default)
                 return val if pd.notna(val) else default
            
            # Initialize result with profile data
            result = {
                "name": safe_get('name', f"{self.ticker} Inc."),
                "ticker": self.ticker,
                "exchange": safe_get('exchange', 'NASDAQ'),
                "industry": safe_get('industry', 'Technology'),
                "marketCap": float(safe_get('market_cap', 0)), 
                "ipoDate": safe_get('ipo', ''),
                "logo": safe_get('logo', ''),
                "phone": safe_get('phone', ''),
                "website": safe_get('weburl', ''),
                "description": safe_get('description', ''),
                "sector": safe_get('sector', ''), 
                "currency": safe_get('currency', 'USD'),
                "country": safe_get('country', 'US'),
                "sharesOutstanding": 0, # Not in CSV
                "dividendYield": float(safe_get('dividend_yield', 0)),
                "latestQuarter": safe_get('latest_quarter', ''),
                "beta": float(safe_get('beta', 0)),
                "revenueGrowth": float(safe_get('revenue_yoy', 0)),
                "netIncomeGrowth": float(safe_get('net_income_yoy', 0)),
                "fcfGrowth": float(safe_get('fcf_yoy', 0)),
                # Fallback PE/EPS from stock_quote.csv if this is being called directly
                "pe": 0.0,
                "eps": 0.0
            }

            # Attempt to enrich with PE/EPS from stock_quote.csv
            try:
                 df_quote = self._safe_read_csv("stock_quote.csv")
                 if df_quote is not None and not df_quote.empty:
                     # Debug logging
                     logger.warning(f"[DEBUG] CSV Loaded. Columns: {df_quote.columns.tolist()}")
                     
                     # Ensure string comparison and strip whitespace
                     df_quote['ticker'] = df_quote['ticker'].astype(str).str.strip()
                     target_ticker = str(self.ticker).strip()
                     
                     logger.warning(f"[DEBUG] Looking for ticker: '{target_ticker}' in first 5: {df_quote['ticker'].head().tolist()}")

                     row_quote = df_quote[df_quote['ticker'] == target_ticker]
                     
                     if not row_quote.empty:
                         pe_val = row_quote.iloc[0].get('pe', 0)
                         eps_val = row_quote.iloc[0].get('eps', 0)
                         logger.warning(f"[DEBUG] Found match for {target_ticker}. PE: {pe_val}, EPS: {eps_val}")
                         result["pe"] = self._format_number(pe_val)
                         result["eps"] = self._format_number(eps_val)
                     else:
                         logger.warning(f"[DEBUG] No match found for {target_ticker} in stock_quote.csv")
                 else:
                     logger.warning("[DEBUG] stock_quote.csv is None or empty")
            except Exception as e:
                 logger.error(f"[DEBUG] Error enriching profile with CSV: {e}")
                 pass
            
            return result

        except Exception as e:
            print(f"Error loading profile: {e}")
            return self._get_fallback_profile()

    def _get_fallback_profile(self):
        return {
            "name": f"{self.ticker} Corporation",
            "ticker": self.ticker,
            "exchange": "NASDAQ",
            "industry": "Technology",
            "sector": "Technology", 
            "marketCap": 150000000000,
            "ipoDate": "1980-12-12",
            "logo": "https://logo.clearbit.com/apple.com",
            "phone": "+1 408-996-1010",
            "website": "https://www.apple.com",
            "description": "Mock description because data was missing.",
            "currency": "USD",
            "country": "US",
            "sharesOutstanding": 16000000000
        }

    def get_price_history(self, period: str = "3m") -> Dict[str, Any]:
        """Load price history and format for Snowball price-history response"""
        df = self._safe_read_csv("stock_candles.csv")

        if df is None or df.empty:
            # Generate mock data for 3 months if no real data available
            dates = []
            prices = []
            base_price = 600.0

            for i in range(60):  # 60 trading days ≈ 3 months
                date = datetime.now() - pd.Timedelta(days=i)
                dates.append(date.strftime("%Y-%m-%dT09:30:00+00:00"))
                # Generate realistic price variation
                price_change = np.random.normal(0, 0.02) * base_price
                base_price = max(base_price + price_change, base_price * 0.8)
                prices.append(self._format_number(base_price))

            dates.reverse()
            prices.reverse()

            return {
                "dates": dates,
                "series": [{"name": self.ticker, "data": prices}]
            }

        # Process real data
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        dates = [self._format_date_iso(date.strftime("%Y-%m-%d")) for date in df['date']]
        prices = [self._format_number(price) for price in df['close']]

        return {
            "dates": dates,
            "series": [{"name": self.ticker, "data": prices}]
        }

    def get_dividends(self) -> List[Dict[str, Any]]:
        """Load dividend history"""
        df = self._safe_read_csv("dividends.csv")

        if df is None or df.empty:
            return []

        dividends = []
        for _, row in df.iterrows():
            dividends.append({
                "date": self._format_date_iso(row.get('date', '')),
                "amount": self._format_number(row.get('amount', 0), 4),
                "adjustedAmount": self._format_number(row.get('adjusted_amount', 0), 4),
                "currency": str(row.get('currency', 'USD')),
                "declaredDate": self._format_date_iso(row.get('declared_date', '')),
                "payDate": self._format_date_iso(row.get('pay_date', '')),
                "recordDate": self._format_date_iso(row.get('record_date', ''))
            })

        return dividends

    def get_news(self, limit: int = 16) -> Dict[str, Any]:
        """Load news articles"""
        df = self._safe_read_csv("company_news.csv")

        if df is None or df.empty:
            return {
                "newsTotalCount": 0,
                "news": []
            }

        # Limit the number of articles
        df_limited = df.head(limit)

        news_articles = []
        for _, row in df_limited.iterrows():
            # Convert datetime to ISO format
            datetime_str = str(row.get('datetime', ''))
            if datetime_str and datetime_str != 'nan':
                try:
                    # Parse the datetime string and convert to ISO format
                    dt = pd.to_datetime(datetime_str)
                    iso_datetime = dt.isoformat() + 'Z'
                except:
                    iso_datetime = datetime.now(timezone.utc).isoformat()
            else:
                iso_datetime = datetime.now(timezone.utc).isoformat()

            news_articles.append({
                "id": str(row.get('id', '')),
                "headline": str(row.get('headline', '')),
                "summary": str(row.get('summary', '')),
                "source": str(row.get('source', '')),
                "url": str(row.get('url', '')),
                "datetime": iso_datetime,
                "category": str(row.get('category', 'general')),
                "image": str(row.get('image', '')),
                "assetInfoIds": [self.ticker]  # Mock asset info IDs
            })

        return {
            "newsTotalCount": len(df),
            "news": news_articles
        }

    def get_financials(self) -> Dict[str, Any]:
        """Load financial statements and format for Snowball financials response"""
        df = self._safe_read_csv("financials_reported.csv")

        if df is None or df.empty:
            return {
                "incomeStatement": [],
                "balanceSheet": [],
                "cashFlow": [],
                "supplemental": [],
                "ratios": self._get_financial_ratios()
            }

        # Group by report type
        income_statement = self._process_financial_statements(df, "IC")
        balance_sheet = self._process_financial_statements(df, "BS")
        cash_flow = self._process_financial_statements(df, "CF")
        supplemental = self._create_supplemental_data()

        return {
            "incomeStatement": income_statement,
            "balanceSheet": balance_sheet,
            "cashFlow": cash_flow,
            "supplemental": supplemental,
            "ratios": self._get_financial_ratios()
        }

    def _process_financial_statements(self, df: pd.DataFrame, report_type: str) -> List[Dict[str, Any]]:
        """Process financial statements for a specific report type"""
        # Handle both uppercase and lowercase report types
        filtered_df = df[df['report_type'].str.upper() == report_type.upper()].copy()

        if filtered_df.empty:
            return []

        # Group by line item and create periods
        statements = []
        line_items = filtered_df['line_item_name'].unique()

        for line_item in line_items:
            if pd.isna(line_item) or line_item == '':
                continue

            item_data = filtered_df[filtered_df['line_item_name'] == line_item]

            # Create period columns
            periods = {}
            for _, row in item_data.iterrows():
                period = str(row.get('period', ''))
                value = self._format_number(row.get('value', 0))
                if period and value != 0:  # Only include non-zero values
                    periods[period] = value

            # Skip items with no meaningful data
            if not periods:
                continue

            # Convert line item name to camelCase-like format
            camel_case_name = self._to_camel_case(str(line_item))

            # Clean up display name
            display_name = str(line_item).replace('us-gaap_', '').replace('_', ' ').title()

            statement_item = {
                "name": camel_case_name,
                "displayName": display_name,
                **periods
            }

            statements.append(statement_item)

        return statements

    def _create_supplemental_data(self) -> List[Dict[str, Any]]:
        """Create supplemental financial data with EBIT and EBITDA"""
        # Mock supplemental data since it's not in the CSV
        return [
            {
                "name": "ebit",
                "displayName": "EBIT",
                "2024Q3": 1250000000,
                "2024Q2": 1180000000,
                "2024Q1": 1100000000,
                "2023Q4": 1050000000
            },
            {
                "name": "ebitda",
                "displayName": "EBITDA",
                "2024Q3": 1350000000,
                "2024Q2": 1280000000,
                "2024Q1": 1200000000,
                "2023Q4": 1150000000
            }
        ]

    def _get_financial_ratios(self) -> List[Dict[str, Any]]:
        """Get financial ratios from metrics CSV"""
        df = self._safe_read_csv("financials_metrics.csv")

        if df is None or df.empty:
            return []

        row = df.iloc[0]
        ratios = []

        ratio_mappings = {
            "pe_ratio": ("P/E Ratio", "peRatio"),
            "profit_margin": ("Profit Margin", "profitMargin"),
            "roe": ("Return on Equity", "returnOnEquity"),
            "roa": ("Return on Assets", "returnOnAssets"),
            "debt_to_equity": ("Debt to Equity", "debtToEquity"),
            "current_ratio": ("Current Ratio", "currentRatio"),
            "quick_ratio": ("Quick Ratio", "quickRatio")
        }

        for csv_field, (display_name, camel_name) in ratio_mappings.items():
            value = row.get(csv_field, 0)
            if not pd.isna(value) and value != 0:
                ratios.append({
                    "name": camel_name,
                    "displayName": display_name,
                    "value": self._format_number(value, 4),
                    "unit": "ratio" if "ratio" in camel_name.lower() else "percentage"
                })

        return ratios

    def _to_camel_case(self, text: str) -> str:
        """Convert text to camelCase"""
        if not text:
            return ""

        # Remove special characters and split by spaces/underscores
        words = text.replace('/', ' ').replace('-', ' ').replace('_', ' ').split()
        if not words:
            return ""

        # First word lowercase, rest title case
        camel = words[0].lower()
        for word in words[1:]:
            camel += word.capitalize()

        return camel

    def get_earnings(self) -> List[Dict[str, Any]]:
        """Load earnings data"""
        df = self._safe_read_csv("earnings.csv")

        if df is None or df.empty:
            return []

        earnings = []
        for _, row in df.iterrows():
            actual_eps = self._format_number(row.get('actual_eps', 0), 4)
            estimate_eps = self._format_number(row.get('estimate_eps', 0), 4)
            actual_revenue = self._format_number(row.get('actual_revenue', 0))
            estimate_revenue = self._format_number(row.get('estimate_revenue', 0))

            earnings.append({
                "period": str(row.get('period', '')),
                "actualEps": actual_eps,
                "estimateEps": estimate_eps,
                "surprise": self._format_number(row.get('surprise', 0), 4),
                "surprisePercent": self._format_number(row.get('surprise_percent', 0), 2),
                "actualRevenue": actual_revenue,
                "estimateRevenue": estimate_revenue,
                "revenueSurprise": actual_revenue - estimate_revenue if actual_revenue and estimate_revenue else 0.0
            })

        return earnings

    def refresh_data(self) -> bool:
        """Re-run the fetch script to get latest data"""
        try:
            script_path = os.path.join(self.data_dir, "fetch_finnhub_data.py")
            if not os.path.exists(script_path):
                return False

            result = subprocess.run(
                ["python", script_path],
                cwd=self.data_dir,
                capture_output=True,
                text=True
            )

            return result.returncode == 0

        except Exception:
            return False

    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of available data"""
        files = [
            "stock_quote.csv",
            "company_profile.csv",
            "stock_candles.csv",
            "dividends.csv",
            "company_news.csv",
            "financials_metrics.csv",
            "earnings.csv",
            "financials_reported.csv"
        ]

        summary = {
            "ticker": self.ticker,
            "dataDirectory": self.data_dir,
            "files": {},
            "totalRows": 0
        }

        for file in files:
            df = self._safe_read_csv(file)
            if df is not None:
                row_count = len(df)
                summary["files"][file] = {
                    "exists": True,
                    "rows": row_count,
                    "lastModified": self._get_file_modified_time(file)
                }
                summary["totalRows"] += row_count
            else:
                summary["files"][file] = {
                    "exists": False,
                    "rows": 0,
                    "lastModified": None
                }

        return summary

    def _get_file_modified_time(self, filename: str) -> Optional[str]:
        """Get file last modified time"""
        try:
            file_path = os.path.join(self.data_dir, filename)
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                return datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            pass
        return None


