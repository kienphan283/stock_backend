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
async def get_price_history(
    ticker: str = Query(..., description="Stock ticker symbol", example="IBM"),
    period: str = Query("1m", description="Time period: 1d, 5d, 1m, 3m, 6m, ytd, 1y, 5y, max", example="1m")
):
    """📊 Get historical price data from database"""
    try:
        logger.info(f"Fetching price history for {ticker}, period: {period}")

        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get stock_id from ticker
                cur.execute(f"""
                    SELECT stock_id
                    FROM {MARKET_DATA_SCHEMA}.stocks
                    WHERE stock_ticker = %s
                """, (ticker.upper(),))

                stock_result = cur.fetchone()
                if not stock_result:
                    # Fallback to CSV loader if not in database
                    logger.warning(f"Stock {ticker} not found in database, using CSV loader")
                    temp_loader = StockDataLoader(ticker.upper())
                    data = temp_loader.get_price_history(period)
                    return {"success": True, "data": data}

                stock_id = stock_result['stock_id']

                # For 1d and 5d, use LIMIT to get N most recent trading days
                # For longer periods, use date-based filtering
                period_lower = period.lower()

                if period_lower == "1d":
                    # Get 1 most recent trading day
                    cur.execute(f"""
                        SELECT
                            trading_date as date,
                            open_price as open,
                            high_price as high,
                            low_price as low,
                            close_price as close,
                            volume,
                            pct_change
                        FROM {MARKET_DATA_SCHEMA}.stock_eod_prices
                        WHERE stock_id = %s
                        ORDER BY trading_date DESC
                        LIMIT 1
                    """, (stock_id,))
                elif period_lower == "5d":
                    # Get 5 most recent trading days
                    cur.execute(f"""
                        SELECT
                            trading_date as date,
                            open_price as open,
                            high_price as high,
                            low_price as low,
                            close_price as close,
                            volume,
                            pct_change
                        FROM {MARKET_DATA_SCHEMA}.stock_eod_prices
                        WHERE stock_id = %s
                        ORDER BY trading_date DESC
                        LIMIT 5
                    """, (stock_id,))
                elif period_lower == "ytd":
                    # Year to date: from January 1 of current year
                    cur.execute(f"""
                        SELECT
                            trading_date as date,
                            open_price as open,
                            high_price as high,
                            low_price as low,
                            close_price as close,
                            volume,
                            pct_change
                        FROM {MARKET_DATA_SCHEMA}.stock_eod_prices
                        WHERE stock_id = %s
                            AND trading_date >= DATE_TRUNC('year', CURRENT_DATE)
                        ORDER BY trading_date ASC
                    """, (stock_id,))
                else:
                    # For longer periods, use calendar days
                    period_to_days = {
                        "1m": 30,
                        "3m": 90,
                        "6m": 180,
                        "1y": 365,
                        "5y": 1825,
                        "max": 10000  # Effectively unlimited
                    }
                    days = period_to_days.get(period_lower, 30)

                    cur.execute(f"""
                        SELECT
                            trading_date as date,
                            open_price as open,
                            high_price as high,
                            low_price as low,
                            close_price as close,
                            volume,
                            pct_change
                        FROM {MARKET_DATA_SCHEMA}.stock_eod_prices
                        WHERE stock_id = %s
                            AND trading_date >= CURRENT_DATE - INTERVAL '%s days'
                        ORDER BY trading_date ASC
                    """, (stock_id, days))

                rows = cur.fetchall()

                # Reverse order for 1d and 5d to get chronological order
                if period_lower in ["1d", "5d"]:
                    rows = list(reversed(rows))

                if not rows:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No price history found for {ticker} in period {period}"
                    )

                # Format data for frontend
                data = []
                for row in rows:
                    data.append({
                        "date": row['date'].strftime("%Y-%m-%d"),
                        "open": float(row['open']) if row['open'] else None,
                        "high": float(row['high']) if row['high'] else None,
                        "low": float(row['low']) if row['low'] else None,
                        "close": float(row['close']) if row['close'] else None,
                        "volume": int(row['volume']) if row['volume'] else 0,
                        "pctChange": float(row['pct_change']) if row['pct_change'] else 0.0
                    })

                logger.info(f"Fetched {len(data)} price records for {ticker}")
                return {"success": True, "data": data}

        finally:
            conn.close()

    except HTTPException:
        raise
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

# ==========================================
# MARKET OVERVIEW ENDPOINTS
# ==========================================

@app.get(
    "/api/market/indices",
    summary="Get Market Indices",
    description="""
    Get major market indices (SPY, QQQ, DIA, IWM) with current prices and sparkline data.
    
    TODO: Khi có database đầy đủ, query từ market_data_oltp.stocks và stock_eod_prices
    Hiện tại return mock data.
    
    Future WebSocket: /ws/market/indices - Realtime index updates
    """,
    tags=["Market Overview"],
)
async def get_market_indices():
    """
    Get market indices overview
    
    TODO: Replace with real database query
    Currently returns mock data for development
    """
    # MOCK DATA - Replace khi có database đầy đủ
    import random
    from datetime import datetime
    
    indices = [
        {"code": "SPY", "name": "S&P 500 ETF", "basePrice": 467.84},
        {"code": "QQQ", "name": "NASDAQ-100", "basePrice": 387.23},
        {"code": "DIA", "name": "Dow Jones", "basePrice": 350.15},
        {"code": "IWM", "name": "Russell 2000", "basePrice": 212.56},
    ]
    
    result = []
    for index in indices:
        change_percent = (random.random() - 0.45) * 2  # -0.9% to 1.1%
        change = index["basePrice"] * (change_percent / 100)
        price = index["basePrice"] + change
        
        # Generate sparkline data (last 50 points)
        sparkline = []
        start_price = index["basePrice"] * (1 - change_percent / 100)
        for i in range(50):
            progress = i / 49
            noise = (random.random() - 0.5) * (price - start_price) * 0.1
            sparkline.append(round(start_price + (price - start_price) * progress + noise, 2))
        
        result.append({
            "code": index["code"],
            "name": index["name"],
            "price": round(price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "volume": random.randint(30000000, 80000000),
            "high": round(price * 1.005, 2),
            "low": round(price * 0.995, 2),
            "sparklineData": sparkline,
            "timestamp": datetime.now().isoformat(),
        })
    
    return result

@app.get(
    "/api/market/candles/{ticker}",
    summary="Get Candlestick Bars",
    description="""
    Get candlestick bars for a ticker from database.
    
    **Current Implementation:**
    - Query from: market_data_oltp.stock_bars (production table)
    - TODO: Switch to stock_bars_staging when WebSocket integration is ready
    
    **Parameters:**
    - ticker: Stock ticker (e.g., "SPY", "AAPL")
    - timeframe: Candle interval (1m, 5m, 15m, 1h, 1D)
    - limit: Number of bars to return (default: 390 = 1 trading day at 1m)
    
    **Future WebSocket:**
    - WS /ws/market/candles/{ticker}
    - Stream realtime tick data
    - Frontend aggregates into candles
    """,
    tags=["Market Overview"],
)
async def get_market_candles(
    ticker: str,
    timeframe: str = Query("1m", description="Timeframe: 1m, 5m, 15m, 1h, 1D"),
    limit: int = Query(390, description="Number of bars to return"),
):
    """
    Get candlestick bars
    
    TODO: Query from market_data_oltp.stock_bars table
    Currently returns mock data
    """
    # MOCK DATA - Replace with database query
    import random
    from datetime import datetime, timedelta
    
    base_prices = {
        "SPY": 467.84,
        "QQQ": 387.23,
        "DIA": 350.15,
        "IWM": 212.56,
        "AAPL": 189.50,
        "MSFT": 378.90,
    }
    
    base_price = base_prices.get(ticker.upper(), 150.0)
    
    # Calculate interval in minutes
    interval_map = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "1D": 1440,
    }
    interval_minutes = interval_map.get(timeframe, 1)
    
    # Generate candles
    candles = []
    current_price = base_price
    now = datetime.now()
    
    for i in range(limit - 1, -1, -1):
        timestamp = now - timedelta(minutes=i * interval_minutes)
        
        # Random OHLC movement
        volatility = base_price * 0.002
        change = (random.random() - 0.5) * volatility * 2
        
        open_price = current_price
        close_price = open_price + change
        high_price = max(open_price, close_price) + random.random() * volatility
        low_price = min(open_price, close_price) - random.random() * volatility
        
        candles.append({
            "timestamp": int(timestamp.timestamp() * 1000),
            "time": timestamp.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": random.randint(100000, 2000000),
            "vwap": round((open_price + high_price + low_price + close_price) / 4, 2),
            "tradeCount": random.randint(50, 500),
        })
        
        current_price = close_price
    
    return {
        "ticker": ticker.upper(),
        "timeframe": timeframe,
        "bars": candles,
        "isLive": False,
        "lastUpdate": datetime.now().isoformat(),
    }

@app.get(
    "/api/market/heatmap",
    summary="Get Market Heatmap",
    description="""
    Get heatmap data for all stocks grouped by sector.
    
    **Returns:**
    - Stocks grouped by sector
    - Size: Market capitalization
    - Color: Percentage change (red = decrease, green = increase)
    
    **TODO:**
    - Query from market_data_oltp tables
    - Add sector classification
    - WebSocket: /ws/market/heatmap - Batch price updates every 5 seconds
    """,
    tags=["Market Overview"],
)
async def get_market_heatmap(
    sector: Optional[str] = Query(None, description="Filter by sector"),
):
    """
    Get market heatmap data
    
    TODO: Query from database with sector grouping
    Currently returns mock data
    """
    # MOCK DATA - Replace with database query
    import random
    from datetime import datetime
    
    sectors_data = [
        {
            "sector": "Technology",
            "displayName": "Công nghệ",
            "color": "#3b82f6",
            "stocks": [
                {"ticker": "AAPL", "name": "Apple Inc.", "basePrice": 189.5, "marketCap": 3000},
                {"ticker": "MSFT", "name": "Microsoft", "basePrice": 378.9, "marketCap": 2800},
                {"ticker": "GOOGL", "name": "Alphabet", "basePrice": 141.8, "marketCap": 1800},
                {"ticker": "NVDA", "name": "NVIDIA", "basePrice": 495.2, "marketCap": 1200},
            ],
        },
        {
            "sector": "Financials",
            "displayName": "Tài chính",
            "color": "#10b981",
            "stocks": [
                {"ticker": "JPM", "name": "JPMorgan Chase", "basePrice": 152.3, "marketCap": 450},
                {"ticker": "BAC", "name": "Bank of America", "basePrice": 34.2, "marketCap": 280},
                {"ticker": "WFC", "name": "Wells Fargo", "basePrice": 48.5, "marketCap": 180},
            ],
        },
        {
            "sector": "Healthcare",
            "displayName": "Y tế",
            "color": "#ef4444",
            "stocks": [
                {"ticker": "UNH", "name": "UnitedHealth", "basePrice": 528.3, "marketCap": 500},
                {"ticker": "JNJ", "name": "Johnson & Johnson", "basePrice": 156.8, "marketCap": 380},
                {"ticker": "PFE", "name": "Pfizer", "basePrice": 28.4, "marketCap": 160},
            ],
        },
    ]
    
    sectors = []
    total_stocks = 0
    
    for sector_info in sectors_data:
        stocks = []
        for stock in sector_info["stocks"]:
            change_percent = (random.random() - 0.45) * 6  # -2.7% to 3.3%
            change = stock["basePrice"] * (change_percent / 100)
            price = stock["basePrice"] + change
            
            stocks.append({
                "ticker": stock["ticker"],
                "name": stock["name"],
                "sector": sector_info["sector"],
                "price": round(price, 2),
                "change": round(change, 2),
                "changePercent": round(change_percent, 2),
                "marketCap": stock["marketCap"] * 1_000_000_000,
                "volume": random.randint(1000000, 50000000),
            })
            total_stocks += 1
        
        total_market_cap = sum(s["marketCap"] for s in stocks)
        avg_change = sum(s["changePercent"] for s in stocks) / len(stocks) if stocks else 0
        
        sectors.append({
            "sector": sector_info["sector"],
            "displayName": sector_info["displayName"],
            "color": sector_info["color"],
            "stocks": stocks,
            "totalMarketCap": total_market_cap,
            "avgChange": round(avg_change, 2),
        })
    
    return {
        "sectors": sectors,
        "totalStocks": total_stocks,
        "lastUpdate": datetime.now().isoformat(),
    }

@app.get(
    "/api/market/status",
    summary="Get Market Status",
    description="""
    Get market overview statistics.
    
    **Returns:**
    - Advancing/Declining/Unchanged stock counts
    - Cash flow distribution
    - Foreign trading activity
    
    **TODO:**
    - Calculate from real-time stock data
    - WebSocket: /ws/market/status - Update every 30 seconds
    """,
    tags=["Market Overview"],
)
async def get_market_status():
    """
    Get market status overview
    
    TODO: Calculate from database
    Currently returns mock data
    """
    # MOCK DATA
    import random
    from datetime import datetime
    
    total_stocks = 30
    advancing = random.randint(12, 18)
    declining = random.randint(8, 14)
    unchanged = total_stocks - advancing - declining
    
    return {
        "advancing": advancing,
        "declining": declining,
        "unchanged": unchanged,
        "cashFlow": {
            "advancing": round(random.uniform(4000, 12000), 2),
            "declining": round(random.uniform(2000, 8000), 2),
            "unchanged": round(random.uniform(500, 2500), 2),
        },
        "foreignTrading": {
            "buy": round(random.uniform(200, 700), 2),
            "sell": round(random.uniform(200, 700), 2),
            "net": round((random.random() - 0.5) * 300, 2),
        },
        "timestamp": datetime.now().isoformat(),
    }

@app.get(
    "/api/market/news",
    summary="Get Featured News",
    description="""
    Get featured news articles for the market overview dashboard.
    
    **Current Implementation:**
    - Returns mock news data
    - TODO: Integrate with news API (Bloomberg, Reuters, etc.)
    - TODO: Add database caching layer
    
    **Parameters:**
    - limit: Number of articles to return (default: 6)
    
    **Future WebSocket:**
    - WS /ws/market/news - Real-time news updates as they're published
    """,
    tags=["Market Overview"],
)
async def get_featured_news(limit: int = 6):
    """
    Get featured news articles
    
    TODO: Replace with actual news aggregation service
    Currently returns mock data for development
    """
    # MOCK DATA - Replace với news API integration
    import random
    from datetime import datetime, timedelta
    
    news_titles = [
        "Cập nhật mới nhất về lệ năm giữ của khối ngoại",
        "Dòn bẩy vốn cho tăng trưởng",
        "EU đạt thỏa thuận tạm thời về ngân sách năm 2026",
        "Canada đầu tư 1,4 tỷ USD mở rộng đường ống dẫn dầu xuất khẩu",
        "Vàng và bitcoin tiếp tục được xem như 'tài sản' trước biến động thị trường",
        "Ngại xếp hàng, người dân đổ xô mua bạc 'trao tay'",
        "Fed dự kiến duy trì lãi suất ổn định trong quý I/2026",
        "Thị trường châu Á phục hồi nhờ tín hiệu tích cực từ Trung Quốc",
        "Giá dầu tăng mạnh sau quyết định cắt giảm sản xuất của OPEC+",
        "Cổ phiếu công nghệ dẫn dắt đà tăng của phố Wall",
    ]
    
    news_thumbnails = [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=300&h=200&fit=crop",
        "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=300&h=200&fit=crop",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=300&h=200&fit=crop",
        "https://images.unsplash.com/photo-1559526324-593bc073d938?w=300&h=200&fit=crop",
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=300&h=200&fit=crop",
    ]
    
    news_sources = ["Bloomberg", "Reuters", "CNBC", "Financial Times", "Wall Street Journal"]
    news_categories = ["market", "economy", "stock", "commodity", "crypto"]
    
    now = datetime.now()
    result = []
    
    for i in range(min(limit, len(news_titles))):
        published_at = now - timedelta(hours=i)
        result.append({
            "id": f"news-{i + 1}",
            "title": news_titles[i],
            "thumbnail": news_thumbnails[i % len(news_thumbnails)],
            "source": random.choice(news_sources),
            "publishedAt": published_at.isoformat(),
            "category": random.choice(news_categories),
        })
    
    return result

# ==========================================
# WEBSOCKET ENDPOINTS (Future Implementation)
# ==========================================

# TODO: Uncomment khi WebSocket backend ready

# from fastapi import WebSocket, WebSocketDisconnect
# import asyncio

# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: List[WebSocket] = []
#     
#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections.append(websocket)
#     
#     def disconnect(self, websocket: WebSocket):
#         self.active_connections.remove(websocket)
#     
#     async def broadcast(self, message: dict):
#         for connection in self.active_connections:
#             await connection.send_json(message)

# manager = ConnectionManager()

# @app.websocket("/ws/market/candles/{ticker}")
# async def websocket_candles(websocket: WebSocket, ticker: str):
#     """
#     WebSocket endpoint for realtime candle updates
#     
#     Flow:
#     1. Client connects and receives last 100 candles
#     2. Stream tick data every ~100ms
#     3. Client aggregates ticks into current candle
#     4. Send new candle when timeframe completes
#     """
#     await manager.connect(websocket)
#     try:
#         while True:
#             # TODO: Fetch latest candle from stock_bars_staging
#             # data = await get_latest_candle(ticker)
#             # await websocket.send_json(data)
#             await asyncio.sleep(1)
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)

# @app.websocket("/ws/market/heatmap")
# async def websocket_heatmap(websocket: WebSocket):
#     """
#     WebSocket endpoint for heatmap price updates
#     
#     Batch updates every 5 seconds to optimize performance
#     """
#     await manager.connect(websocket)
#     try:
#         while True:
#             # TODO: Collect price changes and batch send
#             # data = await get_market_prices()
#             # await websocket.send_json(data)
#             await asyncio.sleep(5)
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)

# @app.websocket("/ws/market/indices")
# async def websocket_indices(websocket: WebSocket):
#     """
#     WebSocket endpoint for index updates
#     """
#     await manager.connect(websocket)
#     try:
#         while True:
#             # TODO: Stream index data
#             await asyncio.sleep(2)
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)

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
