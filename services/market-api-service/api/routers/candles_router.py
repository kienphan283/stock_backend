from fastapi import APIRouter, Query, HTTPException
from services.candles_service import CandlesService
import logging
from shared.python.utils.validation import normalize_symbol, ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/candles", tags=["Candlestick Charts"])
async def get_candles(
    symbol: str = Query(..., description="Stock ticker symbol", example="IBM"),
    tf: str = Query("5m", description="Timeframe: 1m, 5m, 15m, 1h, 1d", example="5m"),
    limit: int = Query(300, description="Maximum number of candles to return", ge=1, le=1000, example=300),
):
    """
    Get intraday candles (OHLCV) for candlestick charts.
    
    Returns OHLCV data from stock_bars table or Redis cache.
    Source: market_data_oltp.stock_bars (or Redis cache: candles:<symbol>:<tf>)
    
    Timeframe options:
    - 1m: 1 minute candles
    - 5m: 5 minute candles
    - 15m: 15 minute candles
    - 1h: 1 hour candles
    - 1d: 1 day candles (intraday aggregation)
    """
    try:
        resolved = normalize_symbol(symbol)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    # Validate timeframe
    valid_timeframes = ["1m", "5m", "15m", "1h", "1d"]
    if tf not in valid_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe '{tf}'. Valid options: {', '.join(valid_timeframes)}"
        )
    
    service = CandlesService()
    try:
        logger.info(f"[CandlesRouter] GET /api/candles - symbol={resolved}, tf={tf}, limit={limit}")
        data = service.get_candles(resolved, tf, limit)
        logger.info(f"[CandlesRouter] Returning {len(data)} candles for {resolved}")
        return {"success": True, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[CandlesRouter] Error fetching candles for {resolved}, tf={tf}: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))

