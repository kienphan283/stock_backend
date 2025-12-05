"""
Service to fetch EOD (End-of-Day) data from external APIs (Alpaca or yfinance)
and insert into database when needed.
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import requests
import logging
import pandas as pd
import yfinance as yf
from psycopg2.extras import execute_values
from db.base_repo import BaseRepository
from config.settings import settings

logger = logging.getLogger(__name__)


class EODFetchService:
    """Service to fetch EOD data from external APIs and insert into DB"""
    
    def __init__(self):
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        self.base_url = settings.ALPACA_BASE_URL
        
        if not self.api_key or not self.secret_key:
            logger.info("[EODFetchService] ALPACA credentials not configured, will use yfinance")
    
    def _get_alpaca_headers(self) -> Dict[str, str]:
        """Get Alpaca API headers"""
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }
    
    def _fetch_from_alpaca(self, symbols: List[str], target_date: date) -> Dict[str, Dict]:
        """Fetch EOD from Alpaca REST API"""
        if not self.api_key or not self.secret_key:
            return {}
        
        result = {}
        date_str = target_date.isoformat()
        
        try:
            url = f"{self.base_url}/v2/stocks/bars"
            
            for symbol in symbols:
                try:
                    params = {
                        "symbols": symbol,
                        "start": date_str,
                        "end": date_str,
                        "timeframe": "1Day",
                        "limit": 1,
                    }
                    
                    response = requests.get(
                        url,
                        headers=self._get_alpaca_headers(),
                        params=params,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        bars = data.get("bars", {}).get(symbol, [])
                        
                        if bars and len(bars) > 0:
                            bar = bars[0]
                            result[symbol.upper()] = {
                                "open": float(bar.get("o", 0)),
                                "high": float(bar.get("h", 0)),
                                "low": float(bar.get("l", 0)),
                                "close": float(bar.get("c", 0)),
                                "volume": int(bar.get("v", 0)),
                                "date": target_date,
                            }
                            logger.info(f"[EODFetchService] Fetched from Alpaca: {symbol} on {date_str}")
                except Exception as e:
                    logger.warning(f"[EODFetchService] Alpaca fetch failed for {symbol}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"[EODFetchService] Alpaca API error: {e}")
        
        return result
    
    def _fetch_from_yfinance(self, symbols: List[str], target_date: date) -> Dict[str, Dict]:
        """Fetch EOD from yfinance (Yahoo Finance)"""
        result = {}
        
        try:
            # yfinance needs date range (fetch a few days around target_date)
            start_date = target_date - timedelta(days=5)
            end_date = target_date + timedelta(days=1)
            
            # Process each symbol individually for better reliability
            for symbol in symbols:
                try:
                    # Download for single symbol
                    ticker = yf.Ticker(symbol.upper())
                    df = ticker.history(
                        start=start_date.isoformat(),
                        end=end_date.isoformat(),
                        auto_adjust=False,
                    )
                    
                    if df.empty:
                        logger.warning(f"[EODFetchService] No yfinance data for {symbol} on {target_date}")
                        continue
                    
                    # Reset index to get Date as column
                    df = df.reset_index()
                    if "Date" not in df.columns and len(df.columns) > 0:
                        df = df.rename(columns={df.columns[0]: "Date"})
                    
                    # Convert Date to date object
                    df["Date"] = pd.to_datetime(df["Date"]).dt.date
                    df = df.sort_values("Date")
                    
                    # Find row for target_date or closest before
                    target_row = df[df["Date"] <= target_date]
                    if target_row.empty:
                        logger.warning(f"[EODFetchService] No data for {symbol} on or before {target_date}. Available dates: {df['Date'].tolist() if not df.empty else 'N/A'}")
                        continue
                    
                    row = target_row.iloc[-1]  # Latest row <= target_date
                    
                    # Log if we're using a date different from target_date
                    if row["Date"] < target_date:
                        logger.warning(f"[EODFetchService] Using closest available date {row['Date']} for {symbol} (target was {target_date})")
                    
                    result[symbol.upper()] = {
                        "open": float(row.get("Open", 0)),
                        "high": float(row.get("High", 0)),
                        "low": float(row.get("Low", 0)),
                        "close": float(row.get("Close", 0)),
                        "volume": int(row.get("Volume", 0)),
                        "date": row["Date"],
                    }
                    logger.info(f"[EODFetchService] Fetched from yfinance: {symbol} on {row['Date']}")
                    
                except Exception as e:
                    logger.warning(f"[EODFetchService] yfinance fetch failed for {symbol}: {e}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"[EODFetchService] yfinance API error: {e}", exc_info=True)
        
        return result
    
    def fetch_eod_bars(self, symbols: List[str], target_date: date) -> Dict[str, Dict]:
        """
        Fetch EOD bars for given symbols and date.
        Tries Alpaca first, falls back to yfinance.
        
        Args:
            symbols: List of ticker symbols
            target_date: Trading date to fetch
            
        Returns:
            Dict {ticker: {open, high, low, close, volume, date}}
        """
        # Try Alpaca first if credentials available
        result = self._fetch_from_alpaca(symbols, target_date)
        
        # If Alpaca didn't return all symbols, try yfinance for missing ones
        missing_symbols = [s for s in symbols if s.upper() not in result]
        if missing_symbols:
            yfinance_result = self._fetch_from_yfinance(missing_symbols, target_date)
            result.update(yfinance_result)
        
        return result
    
    def insert_eod_to_db(self, repo: BaseRepository, eod_data: Dict[str, Dict]) -> int:
        """
        Insert EOD data into stock_eod_prices table.
        
        Args:
            repo: Database repository instance
            eod_data: Dict {ticker: {open, high, low, close, volume, date}}
            
        Returns:
            Number of records inserted/updated
        """
        if not eod_data:
            return 0
        
        conn = None
        try:
            conn = repo._get_connection()
            cursor = conn.cursor()
            
            records = []
            for ticker, data in eod_data.items():
                # Get stock_id
                stock_id_query = "SELECT stock_id FROM market_data_oltp.stocks WHERE stock_ticker = %s"
                stock_result = repo.execute_query(stock_id_query, (ticker.upper(),), fetch_one=True)
                
                if not stock_result:
                    logger.warning(f"[EODFetchService] Stock {ticker} not found in database")
                    continue
                
                stock_id = stock_result['stock_id'] if isinstance(stock_result, dict) else stock_result[0]
                
                # Calculate pct_change (need previous close)
                pct_change = None
                prev_close_query = """
                    SELECT close_price 
                    FROM market_data_oltp.stock_eod_prices 
                    WHERE stock_id = %s 
                    ORDER BY trading_date DESC 
                    LIMIT 1
                """
                prev_result = repo.execute_query(prev_close_query, (stock_id,), fetch_one=True)
                if prev_result:
                    prev_close = float(prev_result['close_price'] if isinstance(prev_result, dict) else prev_result[0])
                    if prev_close > 0:
                        pct_change = round(((data['close'] - prev_close) / prev_close) * 100, 2)
                
                records.append((
                    stock_id,
                    data['date'],
                    data['open'],
                    data['high'],
                    data['low'],
                    data['close'],
                    data['volume'],
                    pct_change,
                ))
            
            if records:
                execute_values(
                    cursor,
                    """
                    INSERT INTO market_data_oltp.stock_eod_prices (
                        stock_id, trading_date, open_price, high_price, low_price, 
                        close_price, volume, pct_change
                    )
                    VALUES %s
                    ON CONFLICT (stock_id, trading_date) DO UPDATE
                    SET open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        pct_change = EXCLUDED.pct_change,
                        inserted_at = CURRENT_TIMESTAMP
                    """,
                    records,
                    page_size=500,
                )
                conn.commit()
                logger.info(f"[EODFetchService] Inserted/updated {len(records)} EOD records")
                return len(records)
            
            cursor.close()
            if conn:
                conn.close()
            return 0
            
        except Exception as e:
            logger.error(f"[EODFetchService] Error inserting EOD to DB: {e}", exc_info=True)
            if conn:
                conn.rollback()
            raise

