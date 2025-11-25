from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from enum import Enum
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from collections import defaultdict

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = settings.db_config
logger.info(
    "Database config: host=%s, dbname=%s, user=%s",
    DB_CONFIG["host"],
    DB_CONFIG["dbname"],
    DB_CONFIG["user"],
)

# Database schema constants
MARKET_DATA_SCHEMA = "market_data_oltp"
FINANCIAL_DATA_SCHEMA = "financial_oltp"

# Optional Redis configuration - Use environment variables
REDIS_HOST = settings.redis_host
REDIS_PORT = settings.redis_port

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

@app.get("/", tags=["System"], summary="Health Check")
async def root():
    """🏥 API health check and available endpoints"""
    return {
        "message": "Stock Data API is running",
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
                    logger.warning(f"Ticker {ticker} not found in stocks table")
                    return {"success": True, "data": None}
                
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
                    logger.warning(f"No EOD price data for {ticker}")
                    return {"success": True, "data": None}
                
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
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quote: {e}")
        return {"success": True, "data": None}

@app.get("/bars/{symbol}", tags=["Bar Data"], summary="Get Bar Data for Symbol")
async def get_bars(
    symbol: str,
    limit: int = Query(100, description="Number of bars to return", ge=1, le=1000)
):
    """📊 Get OHLC bar data for a symbol from stock_bars_staging table"""
    try:
        logger.info(f"Fetching bars for {symbol}, limit: {limit}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Single JOIN query to get bars by symbol
                cur.execute("""
                    SELECT 
                        b.ts as timestamp,
                        b.open_price as open,
                        b.high_price as high,
                        b.low_price as low,
                        b.close_price as close,
                        b.volume,
                        b.trade_count,
                        b.vwap
                    FROM market_data_oltp.stock_bars_staging b
                    JOIN market_data_oltp.stocks s ON s.stock_id = b.stock_id
                    WHERE s.stock_ticker = %s
                    ORDER BY b.ts DESC
                    LIMIT %s
                """, (symbol.upper(), limit))
                
                bars = cur.fetchall()
                
                if not bars:
                    # Check if symbol exists at all
                    cur.execute("""
                        SELECT stock_id 
                        FROM market_data_oltp.stocks 
                        WHERE stock_ticker = %s
                    """, (symbol.upper(),))
                    stock_result = cur.fetchone()
                    if not stock_result:
                        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
                
                # Convert to list of dicts
                result = [dict(bar) for bar in bars]
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "count": len(result),
                    "data": result
                }
                
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bars: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bars/{symbol}/range", tags=["Bar Data"], summary="Get Bar Data for Symbol in Date Range")
async def get_bars_range(
    symbol: str,
    start: str = Query(..., description="Start date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    end: str = Query(..., description="End date (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    limit: int = Query(1000, description="Maximum number of bars to return", ge=1, le=10000)
):
    """📊 Get OHLC bar data for a symbol within a date range"""
    try:
        from datetime import datetime
        
        logger.info(f"Fetching bars for {symbol} from {start} to {end}")
        
        # Parse dates
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Single JOIN query to get bars by symbol in date range
                cur.execute("""
                    SELECT 
                        b.ts as timestamp,
                        b.open_price as open,
                        b.high_price as high,
                        b.low_price as low,
                        b.close_price as close,
                        b.volume,
                        b.trade_count,
                        b.vwap
                    FROM market_data_oltp.stock_bars_staging b
                    JOIN market_data_oltp.stocks s ON s.stock_id = b.stock_id
                    WHERE s.stock_ticker = %s
                    AND b.ts >= %s
                    AND b.ts <= %s
                    ORDER BY b.ts DESC
                    LIMIT %s
                """, (symbol.upper(), start_dt, end_dt, limit))
                
                bars = cur.fetchall()
                
                if not bars:
                    # Check if symbol exists at all
                    cur.execute("""
                        SELECT stock_id 
                        FROM market_data_oltp.stocks 
                        WHERE stock_ticker = %s
                    """, (symbol.upper(),))
                    stock_result = cur.fetchone()
                    if not stock_result:
                        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
                
                # Convert to list of dicts
                result = [dict(bar) for bar in bars]
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "start": start,
                    "end": end,
                    "count": len(result),
                    "data": result
                }
                
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bars range: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bars/latest", tags=["Bar Data"], summary="Get Latest Bar Data for All Symbols")
async def get_latest_bars(
    limit: int = Query(10, description="Number of latest bars per symbol", ge=1, le=100)
):
    """📊 Get latest bar data for all symbols"""
    try:
        logger.info(f"Fetching latest bars for all symbols, limit: {limit}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get latest bars for each symbol using JOIN
                cur.execute("""
                    SELECT DISTINCT ON (s.stock_ticker)
                        s.stock_ticker as symbol,
                        b.ts as timestamp,
                        b.open_price as open,
                        b.high_price as high,
                        b.low_price as low,
                        b.close_price as close,
                        b.volume,
                        b.trade_count,
                        b.vwap
                    FROM market_data_oltp.stock_bars_staging b
                    JOIN market_data_oltp.stocks s ON b.stock_id = s.stock_id
                    ORDER BY s.stock_ticker, b.ts DESC
                    LIMIT %s
                """, (limit * 10,))  # Get more to account for multiple symbols
                
                bars = cur.fetchall()
                
                # Group by symbol and take latest
                symbol_bars = {}
                for bar in bars:
                    symbol = bar['symbol']
                    if symbol not in symbol_bars:
                        symbol_bars[symbol] = dict(bar)
                
                result = list(symbol_bars.values())
                
                return {
                    "success": True,
                    "count": len(result),
                    "data": result
                }
                
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching latest bars: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile", tags=["Company Info"], summary="Get Company Profile")
async def get_company_profile(ticker: str = Query(..., description="Stock ticker symbol", example="IBM")):
    """🏢 Get company profile with industry, sector, and description"""
    try:
        logger.info(f"Fetching profile for {ticker}")
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        c.company_id AS ticker,
                        c.company_name,
                        c.sector,
                        COALESCE(s.exchange, c.exchange) AS exchange,
                        c.currency,
                        s.stock_name,
                        s.stock_ticker
                    FROM {FINANCIAL_DATA_SCHEMA}.company c
                    LEFT JOIN {MARKET_DATA_SCHEMA}.stocks s
                        ON s.company_id = c.company_id OR s.stock_ticker = c.company_id
                    WHERE c.company_id = %s
                """, (ticker.upper(),))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
                
                response = {
                    "name": result.get("company_name"),
                    "ticker": result.get("ticker"),
                    "exchange": result.get("exchange") or "UNKNOWN",
                    "sector": result.get("sector") or "Unknown",
                    "currency": result.get("currency") or "USD",
                    "stockName": result.get("stock_name"),
                    "stockTicker": result.get("stock_ticker") or result.get("ticker")
                }
                return {"success": True, "data": response}
        finally:
            conn.close()
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
                    raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found in database")

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
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        fs.fiscal_year,
                        fs.fiscal_quarter,
                        fs.report_date,
                        li.item_name,
                        li.item_value,
                        li.unit
                    FROM {FINANCIAL_DATA_SCHEMA}.financial_statement fs
                    JOIN {FINANCIAL_DATA_SCHEMA}.statement_type st 
                        ON fs.statement_type_id = st.statement_type_id
                    JOIN {FINANCIAL_DATA_SCHEMA}.financial_line_item li
                        ON fs.statement_id = li.statement_id
                    WHERE fs.company_id = %s
                      AND (
                        li.item_name ILIKE %s OR
                        li.item_code ILIKE %s
                      )
                    ORDER BY fs.fiscal_year DESC, fs.fiscal_quarter DESC, li.item_name
                """, (ticker.upper(), "%dividend%", "%dividend%"))
                
                rows = cur.fetchall()
                dividends = [
                    {
                        "period": f"{row['fiscal_year']}-{row['fiscal_quarter']}",
                        "reportDate": row["report_date"].isoformat() if row["report_date"] else None,
                        "item": row["item_name"],
                        "value": float(row["item_value"]) if row["item_value"] is not None else None,
                        "unit": row["unit"]
                    }
                    for row in rows
                ]
                
                return {"success": True, "count": len(dividends), "data": dividends}
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error fetching dividends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news", tags=["Company Info"], summary="Get Company News")
async def get_news(ticker: str = Query(..., description="Stock ticker symbol", example="IBM"), limit: int = Query(16, description="Number of news articles to return")):
    """📰 Get latest company news and headlines"""
    try:
        logger.info(f"Fetching news for {ticker}, limit: {limit}")
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT company_id
                    FROM {FINANCIAL_DATA_SCHEMA}.company
                    WHERE company_id = %s
                """, (ticker.upper(),))
                company = cur.fetchone()
                if not company:
                    raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
        finally:
            conn.close()
        
        # News data is populated by upstream ETL or external services.
        # For now, return an empty list indicating no stored articles.
        return {"success": True, "data": {"newsTotalCount": 0, "news": []}}
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
async def get_financials_legacy(
    company: str = Query("IBM", description="Company ticker symbol", example="IBM"),
    type: StatementType = Query(StatementType.IS, description="Statement type", example="IS"),
    period: PeriodType = Query(PeriodType.quarterly, description="Period type", example="quarterly")
):
    """Legacy endpoint kept for backward compatibility - proxies to /api/financials"""
    logger.info(f"Legacy financials endpoint called for company={company}, type={type}, period={period}")
    return await get_financials(company=company, type=type, period=period)

@app.get("/earnings")
async def get_earnings(
    ticker: str = Query(..., description="Stock ticker symbol", example="IBM"),
    limit: int = Query(20, description="Max number of earnings metrics to return", ge=1, le=100)
):
    """Get earnings-related metrics derived from financial statements"""
    try:
        logger.info(f"Fetching earnings metrics for {ticker}")
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        fs.fiscal_year,
                        fs.fiscal_quarter,
                        fs.report_date,
                        li.item_name,
                        li.item_value,
                        li.unit
                    FROM {FINANCIAL_DATA_SCHEMA}.financial_statement fs
                    JOIN {FINANCIAL_DATA_SCHEMA}.financial_line_item li
                        ON fs.statement_id = li.statement_id
                    WHERE fs.company_id = %s
                      AND (
                        li.item_name ILIKE %s
                        OR li.item_code ILIKE %s
                      )
                    ORDER BY fs.fiscal_year DESC, fs.fiscal_quarter DESC, li.item_name
                    LIMIT %s
                """, (ticker.upper(), "%eps%", "%eps%", limit))
                
                rows = cur.fetchall()
                if not rows:
                    raise HTTPException(status_code=404, detail=f"No EPS metrics found for {ticker}")
                
                earnings = [
                    {
                        "period": f"{row['fiscal_year']}-{row['fiscal_quarter']}",
                        "reportDate": row["report_date"].isoformat() if row["report_date"] else None,
                        "metric": row["item_name"],
                        "value": float(row["item_value"]) if row["item_value"] is not None else None,
                        "unit": row["unit"]
                    }
                    for row in rows
                ]
                
                return {"success": True, "count": len(earnings), "data": earnings}
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refresh")
async def refresh_data():
    """Notify clients that ETL refresh must be performed via dedicated pipeline"""
    logger.info("Refresh endpoint invoked - no action performed (handled by ETL pipeline)")
    raise HTTPException(
        status_code=409,
        detail="Data refresh is handled by the ETL pipeline. Please run `python etl/runner.py bctc --symbol <TICKER>`."
    )

@app.get("/summary")
async def get_data_summary():
    """Get data summary and status"""
    try:
        logger.info("Fetching data summary from PostgreSQL")
        conn = psycopg2.connect(**DB_CONFIG)
        summary = {}
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {FINANCIAL_DATA_SCHEMA}.company")
                summary["companies"] = cur.fetchone()[0]
                
                cur.execute(f"SELECT COUNT(*) FROM {FINANCIAL_DATA_SCHEMA}.financial_statement")
                summary["financialStatements"] = cur.fetchone()[0]
                
                cur.execute(f"SELECT COUNT(*) FROM {FINANCIAL_DATA_SCHEMA}.financial_line_item")
                summary["financialLineItems"] = cur.fetchone()[0]
                
                cur.execute(f"SELECT COUNT(*) FROM {MARKET_DATA_SCHEMA}.stocks")
                summary["stocks"] = cur.fetchone()[0]
                
                cur.execute(f"SELECT COUNT(*) FROM {MARKET_DATA_SCHEMA}.stock_eod_prices")
                summary["eodPrices"] = cur.fetchone()[0]
                
                cur.execute(f"SELECT COUNT(*) FROM {MARKET_DATA_SCHEMA}.stock_bars_staging")
                summary["bars"] = cur.fetchone()[0]
                
                cur.execute(f"SELECT MAX(report_date) FROM {FINANCIAL_DATA_SCHEMA}.financial_statement")
                latest_row = cur.fetchone()
                summary["latestReportDate"] = latest_row[0].isoformat() if latest_row and latest_row[0] else None
        finally:
            conn.close()
        
        return {"success": True, "data": summary}
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
