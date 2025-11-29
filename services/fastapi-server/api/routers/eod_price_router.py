from fastapi import APIRouter, Query, HTTPException
from services.eod_price_service import EODPriceService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/price-history/eod", tags=["Price Charts"])
async def get_eod_price_history(
    symbol: str = Query(..., description="Stock ticker symbol", example="IBM"),
    period: str = Query("3mo", description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, ytd, max", example="3mo"),
):
    """
    Get End-of-Day price history for price charts (line charts).
    
    Returns full OHLCV: {date, open, high, low, close, volume}
    Source: market_data_oltp.stock_eod_prices
    
    Period options:
    - 1d: Last 1 trading day
    - 5d: Last 5 trading days
    - 1mo: Last 30 days (1 month)
    - 3mo: Last 90 days (3 months)
    - 6mo: Last 180 days (6 months)
    - 1y: Last 365 days (1 year)
    - ytd: Year to date
    - max: All available data
    
    Note: "1m" is NOT valid here (use "1mo" for 1 month). 
          For 1-minute candles, use /api/candles endpoint.
    """
    resolved = symbol.upper() if symbol else ""
    if not resolved:
        raise HTTPException(status_code=400, detail="symbol is required")
    
    # Validate period (allow common aliases)
    valid_periods = ["1d", "5d", "1mo", "1m", "3mo", "3m", "6mo", "6m", "ytd", "1y", "5y", "max"]
    if period.lower() not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Valid options: 1d, 5d, 1mo, 3mo, 6mo, 1y, ytd, max. Note: '1m' means 1 month here, not 1 minute."
        )
    
    service = EODPriceService()
    try:
        logger.info(f"[EODPriceRouter] GET /api/price-history/eod - symbol={resolved}, period={period}")
        data = service.get_price_history(resolved, period)
        logger.info(f"[EODPriceRouter] Returning {len(data)} records for {resolved}")
        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[EODPriceRouter] Error fetching EOD price history for {resolved}, period={period}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))

