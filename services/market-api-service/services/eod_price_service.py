from db.eod_price_repo import EODPriceRepository
import logging

logger = logging.getLogger(__name__)

class EODPriceService:
    """Service for End-of-Day price data (price charts only - date and close)"""
    
    def __init__(self):
        self.repo = EODPriceRepository()
    
    def get_price_history(self, ticker: str, period: str = "3mo") -> list:
        """
        Get EOD price history for price charts.
        Returns full OHLCV: {date, open, high, low, close, volume}
        
        Args:
            ticker: Stock ticker symbol
            period: Period string (1d, 5d, 1mo, 3mo, 6mo, 1y, ytd, max)
                   Note: "1m" is NOT valid for EOD (use "1mo" for 1 month)
        
        Returns:
            List of dicts: [{"date": "2025-10-29", "open": 312.79, "high": 313.0, "low": 308.0, "close": 308.21, "volume": 1234567}, ...]
        """
        logger.info(f"[EODPriceService] get_price_history: ticker={ticker}, period={period}")
        
        # Resolve ticker to stock_id using market_data_oltp.stocks
        stock_id = self.repo.get_stock_id(ticker)
        if not stock_id:
            logger.warning(f"[EODPriceService] Stock ticker {ticker} not found in market_data_oltp.stocks")
            return []
        
        logger.info(f"[EODPriceService] Resolved {ticker} to stock_id={stock_id}")
        
        # Get price history from stock_eod_prices
        rows = self.repo.get_price_history(stock_id, period)
        
        # Transform to response format (full OHLCV)
        price_history = []
        for row in rows:
            if isinstance(row, dict):
                date_val = row.get('date')
                open_val = row.get('open')
                high_val = row.get('high')
                low_val = row.get('low')
                close_val = row.get('close')
                volume_val = row.get('volume')
            else:
                # Handle tuple result
                date_val = row[0] if len(row) > 0 else None
                open_val = row[1] if len(row) > 1 else None
                high_val = row[2] if len(row) > 2 else None
                low_val = row[3] if len(row) > 3 else None
                close_val = row[4] if len(row) > 4 else None
                volume_val = row[5] if len(row) > 5 else None
            
            price_history.append({
                "date": date_val.isoformat() if date_val and hasattr(date_val, 'isoformat') else (str(date_val) if date_val else None),
                "open": float(open_val) if open_val is not None else 0.0,
                "high": float(high_val) if high_val is not None else 0.0,
                "low": float(low_val) if low_val is not None else 0.0,
                "close": float(close_val) if close_val is not None else 0.0,
                "volume": int(volume_val) if volume_val is not None else 0
            })
        
        logger.info(f"[EODPriceService] Returning {len(price_history)} price records for {ticker}")
        return price_history

