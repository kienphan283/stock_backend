from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from services.data_loader import StockDataLoader
import uvicorn
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from enum import Enum
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from collections import defaultdict
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration - Use environment variables with fallbacks
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Parse DATABASE_URL format: postgresql://user:password@host:port/dbname
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if match:
        DB_CONFIG = {
            "user": match.group(1),
            "password": match.group(2),
            "host": match.group(3),
            "port": int(match.group(4)),
            "dbname": match.group(5)
        }
    else:
        raise ValueError(f"Invalid DATABASE_URL format: {DATABASE_URL}")
else:
    # Fallback to individual environment variables
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "Web_quan_li_danh_muc"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    # Validate critical config
    if not DB_CONFIG["password"]:
        raise ValueError("DB_PASSWORD environment variable is required")

logger.info(f"Database config: host={DB_CONFIG['host']}, dbname={DB_CONFIG['dbname']}, user={DB_CONFIG['user']}")

# Database schema constants
MARKET_DATA_SCHEMA = "market_data_oltp"
FINANCIAL_DATA_SCHEMA = "financial_oltp"

# Optional Redis configuration - Use environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

try:
    import redis
    REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    # Test connection
    REDIS_CLIENT.ping()
    REDIS_ENABLED = True
    logger.info(f"Redis caching enabled at {REDIS_HOST}:{REDIS_PORT}")
except (ImportError, redis.ConnectionError, redis.ResponseError) as e:
    REDIS_CLIENT = None
    REDIS_ENABLED = False
    logger.warning(f"Redis not available: {e}")

# Enums for validation
class StatementType(str, Enum):
    IS = "IS"
    BS = "BS"
    CF = "CF"

class PeriodType(str, Enum):
    annual = "annual"
    quarterly = "quarterly"

# Pydantic response models
class FinancialDataResponse(BaseModel):
    company: str = Field(..., description="Company ticker symbol", example="IBM")
    type: str = Field(..., description="Statement type: IS, BS, or CF", example="IS")
    period: str = Field(..., description="Period type: annual or quarterly", example="quarterly")
    periods: List[str] = Field(..., description="List of periods in descending order", example=["2025-Q2", "2025-Q1", "2024-Q4"])
    data: Dict[str, Dict[str, float]] = Field(
        ..., 
        description="Pivoted financial data: {lineItem: {period: value}}",
        example={
            "Total Revenue": {
                "2025-Q2": 16977000000.0,
                "2025-Q1": 14541000000.0,
                "2024-Q4": 17553000000.0
            },
            "Gross Profit": {
                "2025-Q2": 9977000000.0,
                "2025-Q1": 8031000000.0,
                "2024-Q4": 9903000000.0
            }
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "company": "IBM",
                "type": "IS",
                "period": "quarterly",
                "periods": ["2025-Q2", "2025-Q1", "2024-Q4", "2024-Q3"],
                "data": {
                    "Total Revenue": {
                        "2025-Q2": 16977000000.0,
                        "2025-Q1": 14541000000.0,
                        "2024-Q4": 17553000000.0,
                        "2024-Q3": 14967000000.0
                    },
                    "Gross Profit": {
                        "2025-Q2": 9977000000.0,
                        "2025-Q1": 8031000000.0,
                        "2024-Q4": 9903000000.0,
                        "2024-Q3": 8257000000.0
                    },
                    "Net Income": {
                        "2025-Q2": 2413000000.0,
                        "2025-Q1": 2002000000.0,
                        "2024-Q4": 2571000000.0,
                        "2024-Q3": 2217000000.0
                    }
                }
            }
        }

# Initialize FastAPI app
app = FastAPI(
    title="Stock Data API",
    description="""
    🚀 **Stock Analytics API with Real Financial Data**
    
    ## Features
    - Real-time stock quotes from Finnhub
    - Multi-period financial statements from PostgreSQL
    - Company profiles and news
    - Dividend history and earnings data
    - Optional Redis caching for performance
    
    ## Financial Data Endpoint
    Use `/api/financials` to get comprehensive financial statements:
    - **Income Statement (IS)**: Revenue, expenses, net income
    - **Balance Sheet (BS)**: Assets, liabilities, equity
    - **Cash Flow (CF)**: Operating, investing, financing activities
    
    Data is returned in **pivoted format** with periods as columns.
    
    ## Important Notes
    - All monetary values are in **original currency units** (e.g., dollars, not millions)
    - Example: `16977000000.0` = $16.977 billion USD
    - Periods are sorted in **descending order** (newest first)
    - Format large numbers using: `value / 1_000_000_000` for billions
    
    ## Resources
    - [API Response Examples](./API_RESPONSE_EXAMPLES.md)
    - [Full Documentation](./API_FINANCIALS_DOCS.md)
    """,
    version="2.0.0",
    contact={
        "name": "Stock Analytics Team",
        "email": "support@example.com"
    }
)

# Enable CORS for frontend and backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend Next.js
        "http://localhost:5000",  # Backend Express
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data loader
loader = StockDataLoader()

@app.get("/", tags=["System"], summary="Health Check")
async def root():
    """🏥 API health check and available endpoints"""
    return {
        "message": "Stock Data API is running",
        "ticker": loader.ticker,
        "endpoints": [
            "/quote",
            "/profile",
            "/price-history",
            "/dividends",
            "/news",
            "/financials (legacy)",
            "/api/financials (PostgreSQL)",
            "/earnings",
            "/refresh",
            "/summary"
        ],
        "redis_enabled": REDIS_ENABLED
    }

@app.get("/quote", tags=["Real-Time Data"], summary="Get Stock Quote")
async def get_quote(ticker: str = Query(..., description="Stock ticker symbol", example="IBM")):
    """📈 Get current stock quote with price, volume, and market data from database"""
    try:
        logger.info(f"Fetching quote for {ticker}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get stock_id
                cur.execute(f"""
                    SELECT stock_id 
                    FROM {MARKET_DATA_SCHEMA}.stocks 
                    WHERE stock_ticker = %s
                """, (ticker.upper(),))
                
                stock_result = cur.fetchone()
                if not stock_result:
                    # Fallback to CSV loader if not in database
                    temp_loader = StockDataLoader(ticker.upper())
                    data = temp_loader.get_quote()
                    return {"success": True, "data": data}
                
                stock_id = stock_result['stock_id']
                
                # Get latest EOD price data
                cur.execute(f"""
                    SELECT 
                        close_price as current_price,
                        open_price,
                        high_price,
                        low_price,
                        volume,
                        pct_change as percent_change
                    FROM {MARKET_DATA_SCHEMA}.stock_eod_prices 
                    WHERE stock_id = %s 
                    ORDER BY trading_date DESC 
                    LIMIT 1
                """, (stock_id,))
                
                latest = cur.fetchone()
                
                if not latest:
                    # Fallback to CSV loader if no price data
                    temp_loader = StockDataLoader(ticker.upper())
                    data = temp_loader.get_quote()
                    return {"success": True, "data": data}
                
                # Get previous close for change calculation
                cur.execute(f"""
                    SELECT close_price
                    FROM {MARKET_DATA_SCHEMA}.stock_eod_prices 
                    WHERE stock_id = %s 
                    ORDER BY trading_date DESC 
                    OFFSET 1
                    LIMIT 1
                """, (stock_id,))
                
                prev = cur.fetchone()
                previous_close = float(prev['close_price']) if prev else float(latest['current_price'])
                current_price = float(latest['current_price'])
                change = current_price - previous_close
                
                data = {
                    "currentPrice": round(current_price, 2),
                    "change": round(change, 2),
                    "percentChange": round(float(latest['percent_change'] or 0), 2),
                    "high": round(float(latest['high_price'] or 0), 2),
                    "low": round(float(latest['low_price'] or 0), 2),
                    "open": round(float(latest['open_price'] or 0), 2),
                    "previousClose": round(previous_close, 2)
                }
                
                return {"success": True, "data": data}
                
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile", tags=["Company Info"], summary="Get Company Profile")
async def get_company_profile(ticker: str = Query(..., description="Stock ticker symbol", example="IBM")):
    """🏢 Get company profile with industry, sector, and description"""
    try:
        logger.info(f"Fetching profile for {ticker}")
        temp_loader = StockDataLoader(ticker.upper())
        data = temp_loader.get_company_profile()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/price-history")
async def get_price_history(ticker: str = Query(..., description="Stock ticker symbol", example="IBM"), period: str = "3m"):
    """Get price history data"""
    try:
        logger.info(f"Fetching price history for {ticker}, period: {period}")
        temp_loader = StockDataLoader(ticker.upper())
        data = temp_loader.get_price_history(period)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dividends", tags=["Company Info"], summary="Get Dividend History")
async def get_dividends(ticker: str = Query(..., description="Stock ticker symbol", example="IBM")):
    """💰 Get historical dividend payments"""
    try:
        logger.info(f"Fetching dividends for {ticker}")
        temp_loader = StockDataLoader(ticker.upper())
        data = temp_loader.get_dividends()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching dividends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news", tags=["Company Info"], summary="Get Company News")
async def get_news(ticker: str = Query(..., description="Stock ticker symbol", example="IBM"), limit: int = Query(16, description="Number of news articles to return")):
    """📰 Get latest company news and headlines"""
    try:
        logger.info(f"Fetching news for {ticker}, limit: {limit}")
        temp_loader = StockDataLoader(ticker.upper())
        data = temp_loader.get_news(limit)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/financials",
    response_model=FinancialDataResponse,
    summary="Get Financial Statements",
    description="""
    📊 **Fetch multi-period financial statements from PostgreSQL database**
    
    ### Statement Types
    - **IS** - Income Statement (Revenue, Expenses, Net Income)
    - **BS** - Balance Sheet (Assets, Liabilities, Equity)
    - **CF** - Cash Flow Statement (Operating, Investing, Financing)
    
    ### Period Types
    - **quarterly** - Returns last 10 quarters (e.g., 2025-Q2, 2025-Q1, ...)
    - **annual** - Returns last 3 years (e.g., 2024, 2023, 2022)
    
    ### Response Format
    The API returns **pivoted data** in this structure:
    ```json
    {
      "company": "IBM",
      "type": "IS",
      "period": "quarterly",
      "periods": ["2025-Q2", "2025-Q1", "2024-Q4", ...],
      "data": {
        "Total Revenue": {
          "2025-Q2": 16977000000.0,
          "2025-Q1": 14541000000.0,
          ...
        },
        "Net Income": { ... }
      }
    }
    ```
    
    ### Important Notes
    - Values are in **original units** (dollars, not millions/billions)
    - `16977000000.0` = $16.977B USD (divide by 1B for display)
    - Periods are **sorted descending** (newest first)
    - Missing values may appear as `null` or be omitted
    - Redis caching enabled (30 min TTL) for performance
    
    ### Example Usage
    ```bash
    # Get IBM quarterly income statement
    GET /api/financials?company=IBM&type=IS&period=quarterly
    
    # Get GOOGL annual balance sheet
    GET /api/financials?company=GOOGL&type=BS&period=annual
    ```
    
    ### Common Line Items
    
    **Income Statement (IS):**
    - Total Revenue, Cost Of Revenue, Gross Profit
    - Operating Income, Operating Expenses
    - Net Income, EBIT, EBITDA
    
    **Balance Sheet (BS):**
    - Total Assets, Total Current Assets
    - Cash And Cash Equivalents, Inventory
    - Total Liabilities, Stockholders Equity
    
    **Cash Flow (CF):**
    - Operating Cash Flow, Investing Cash Flow
    - Financing Cash Flow, Free Cash Flow
    - Capital Expenditures, Dividends Paid
    """,
    tags=["Financial Data"],
    responses={
        200: {
            "description": "Successfully retrieved financial data",
            "content": {
                "application/json": {
                    "example": {
                        "company": "IBM",
                        "type": "IS",
                        "period": "quarterly",
                        "periods": ["2025-Q2", "2025-Q1", "2024-Q4", "2024-Q3"],
                        "data": {
                            "Total Revenue": {
                                "2025-Q2": 16977000000.0,
                                "2025-Q1": 14541000000.0,
                                "2024-Q4": 17553000000.0,
                                "2024-Q3": 14967000000.0
                            },
                            "Gross Profit": {
                                "2025-Q2": 9977000000.0,
                                "2025-Q1": 8031000000.0,
                                "2024-Q4": 9903000000.0,
                                "2024-Q3": 8257000000.0
                            },
                            "Cost Of Revenue": {
                                "2025-Q2": 7001000000.0,
                                "2025-Q1": 6510000000.0,
                                "2024-Q4": 7651000000.0,
                                "2024-Q3": 6710000000.0
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid type. Must be 'IS', 'BS', or 'CF'"
                    }
                }
            }
        },
        404: {
            "description": "No data found for company",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No financial data found for company 'INVALID'"
                    }
                }
            }
        },
        500: {
            "description": "Server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Database connection error"
                    }
                }
            }
        }
    }
)
async def get_financials(
    company: str = Query(
        ..., 
        description="🏢 Company ticker symbol",
        example="IBM",
        min_length=1,
        max_length=10
    ),
    type: StatementType = Query(
        ..., 
        description="📄 Statement type: IS (Income Statement), BS (Balance Sheet), CF (Cash Flow)",
        example="IS"
    ),
    period: PeriodType = Query(
        ..., 
        description="📅 Period type: quarterly (last 10 quarters) or annual (last 3 years)",
        example="quarterly"
    )
) -> FinancialDataResponse:
    try:
        # Convert enum to string for processing
        type_str = type.value
        period_str = period.value
        
        logger.info(f"Fetching financials: company={company}, type={type_str}, period={period_str}")
        
        # Check Redis cache first (if enabled)
        cache_key = f"bctc:{company}:{type_str}:{period_str}"
        if REDIS_ENABLED and REDIS_CLIENT:
            try:
                cached_data = REDIS_CLIENT.get(cache_key)
                if cached_data:
                    logger.info(f"Cache hit for {cache_key}")
                    return json.loads(cached_data)
            except Exception as redis_error:
                logger.warning(f"Redis error: {redis_error}")
        
        # Map statement type to view name
        view_mapping = {
            "IS": "financial_oltp.vw_income_statement_recent",
            "BS": "financial_oltp.vw_balance_sheet_recent",
            "CF": "financial_oltp.vw_cashflow_statement_recent"
        }
        
        view_name = view_mapping[type_str]
        
        # Query database
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"SELECT * FROM {view_name} WHERE company_id = %s"
                cur.execute(query, (company,))
                rows = cur.fetchall()
                
                if not rows:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"No financial data found for company '{company}'"
                    )
                
                # Transform data: pivot from flat to nested structure
                result = transform_financial_data(rows, company, type_str, period_str)
                
                # Cache the result in Redis (if enabled)
                if REDIS_ENABLED and REDIS_CLIENT:
                    try:
                        REDIS_CLIENT.setex(
                            cache_key,
                            1800,  # TTL: 30 minutes
                            json.dumps(result)
                        )
                        logger.info(f"Cached result for {cache_key}")
                    except Exception as redis_error:
                        logger.warning(f"Redis caching error: {redis_error}")
                
                return result
                
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching financials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def transform_financial_data(
    rows: List[Dict[str, Any]], 
    company: str, 
    statement_type: str, 
    period_type: str
) -> Dict[str, Any]:
    """
    Transform flat database rows into pivoted JSON structure.
    
    Args:
        rows: List of database records with columns like item_name, item_value, fiscal_year, fiscal_quarter
        company: Company ticker
        statement_type: Statement type code (IS, BS, CF)
        period_type: Period type (annual, quarterly)
    
    Returns:
        Pivoted data structure with periods and line items
    """
    # Data structure to hold pivoted data
    data_dict = defaultdict(dict)
    periods_set = set()
    
    for row in rows:
        item_name = row['item_name']
        item_value = float(row['item_value']) if row['item_value'] is not None else 0
        fiscal_year = row['fiscal_year']
        fiscal_quarter = row['fiscal_quarter']
        
        # Create period key based on period_type
        if period_type == "annual":
            # For annual, we group by year only
            # We'll aggregate quarters if needed, or take Q4 data
            period_key = str(fiscal_year)
        else:
            # For quarterly
            period_key = f"{fiscal_year}-{fiscal_quarter}"
        
        # Store the value
        # If multiple values exist for same item_name and period, keep the latest
        data_dict[item_name][period_key] = item_value
        periods_set.add(period_key)
    
    # Sort periods in descending order
    if period_type == "annual":
        # Sort years descending
        periods_sorted = sorted(list(periods_set), key=lambda x: int(x), reverse=True)
    else:
        # Sort quarterly periods descending (year first, then quarter)
        def sort_key(period_str):
            year_str, quarter_str = period_str.split('-')
            year = int(year_str)
            quarter_num = int(quarter_str[1])  # Extract number from "Q1", "Q2", etc.
            return (year, quarter_num)
        
        periods_sorted = sorted(list(periods_set), key=sort_key, reverse=True)
    
    # Build final response structure
    response = {
        "company": company,
        "type": statement_type,
        "period": period_type,
        "periods": periods_sorted[:10],  # Limit to 10 most recent periods
        "data": dict(data_dict)
    }
    
    return response


@app.get("/financials")
async def get_financials_legacy():
    """Get financial statements (legacy endpoint using data loader)"""
    try:
        logger.info(f"Fetching financials for {loader.ticker}")
        data = loader.get_financials()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching financials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/earnings")
async def get_earnings():
    """Get earnings data"""
    try:
        logger.info(f"Fetching earnings for {loader.ticker}")
        data = loader.get_earnings()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refresh")
async def refresh_data():
    """Refresh data from Finnhub API"""
    try:
        logger.info("Refreshing data from Finnhub API...")
        success = loader.refresh_data()
        if success:
            return {"success": True, "message": "Data refreshed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Data refresh failed")
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summary")
async def get_data_summary():
    """Get data summary and status"""
    try:
        logger.info("Fetching data summary")
        data = loader.get_data_summary()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companies", summary="📋 Get all available companies")
async def get_companies():
    """
    Retrieve list of all companies available in the database.
    """
    try:
        logger.info("Fetching list of companies from database")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT DISTINCT 
                company_id as ticker,
                company_name as name,
                sector,
                exchange
            FROM financial_oltp.company
            ORDER BY company_name
        """
        
        cursor.execute(query)
        companies = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(companies)} companies in database")
        
        return {
            "success": True,
            "count": len(companies),
            "companies": companies
        }
        
    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PriceChangeResponse(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol", example="IBM")
    currentPrice: float = Field(..., description="Current stock price", example=150.25)
    previousClose: float = Field(..., description="Previous day's closing price", example=149.19)
    absoluteChange: float = Field(..., description="Absolute price change (current - previous)", example=1.06)
    percentageChange: float = Field(..., description="Percentage price change", example=0.71)

@app.get(
    "/api/stocks/{ticker}/price-change",
    response_model=PriceChangeResponse,
    summary="📈 Get Stock Price Change",
    description="""
    **Calculate stock price changes from database**
    
    ### Calculation Logic
    - **Current Price**: Latest price from `stock_trades_realtime` or today's close from `stock_eod_prices`
    - **Previous Close**: Most recent closing price from `stock_eod_prices` (previous trading day)
    - **Absolute Change**: Current Price - Previous Close
    - **Percentage Change**: (Absolute Change / Previous Close) × 100
    
    ### Example
    ```json
    {
      "ticker": "IBM",
      "currentPrice": 150.25,
      "previousClose": 149.19,
      "absoluteChange": 1.06,
      "percentageChange": 0.71
    }
    ```
    """,
    tags=["Stock Data"],
    responses={
        200: {
            "description": "Successfully retrieved price change data"
        },
        404: {
            "description": "Stock not found or no price data available"
        },
        500: {
            "description": "Server error"
        }
    }
)
async def get_price_change(ticker: str):
    """
    Get stock price change calculations from database.
    Calculates absolute and percentage changes based on current price vs previous day's close.
    """
    try:
        logger.info(f"Fetching price change for ticker: {ticker}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # First, get stock_id from ticker
                cur.execute(f"""
                    SELECT stock_id 
                    FROM {MARKET_DATA_SCHEMA}.stocks 
                    WHERE stock_ticker = %s
                """, (ticker.upper(),))
                
                stock_result = cur.fetchone()
                if not stock_result:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stock ticker '{ticker}' not found in database"
                    )
                
                stock_id = stock_result['stock_id']
                
                # Get latest EOD price as current price
                cur.execute(f"""
                    SELECT close_price, pct_change
                    FROM {MARKET_DATA_SCHEMA}.stock_eod_prices 
                    WHERE stock_id = %s 
                    ORDER BY trading_date DESC 
                    LIMIT 1
                """, (stock_id,))
                
                latest = cur.fetchone()
                if not latest or not latest['close_price']:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No price data found for ticker '{ticker}'"
                    )
                
                current_price = float(latest['close_price'])
                
                # Get previous EOD price
                cur.execute(f"""
                    SELECT close_price
                    FROM {MARKET_DATA_SCHEMA}.stock_eod_prices 
                    WHERE stock_id = %s 
                    ORDER BY trading_date DESC 
                    OFFSET 1
                    LIMIT 1
                """, (stock_id,))
                
                prev = cur.fetchone()
                previous_close = float(prev['close_price']) if prev else current_price
                
                # Calculate changes
                absolute_change = current_price - previous_close
                percentage_change = (absolute_change / previous_close) * 100 if previous_close != 0 else 0.0
                
                result = {
                    "ticker": ticker.upper(),
                    "currentPrice": round(current_price, 2),
                    "previousClose": round(previous_close, 2),
                    "absoluteChange": round(absolute_change, 2),
                    "percentageChange": round(percentage_change, 2)
                }
                
                logger.info(f"Price change calculated for {ticker}: {result}")
                return result
                
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price change for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting Stock Data API Server...")
    print("Ticker: APP (AppLovin Corporation)")
    print("Server: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("Health: http://localhost:8000")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
