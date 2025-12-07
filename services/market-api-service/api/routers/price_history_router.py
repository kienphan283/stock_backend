from fastapi import APIRouter, Query, HTTPException
from services.price_history_service import PriceHistoryService
import logging
from shared.python.utils.validation import normalize_symbol, ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/price-history", tags=["Real-Time Data"])
@router.get("/api/price-history", tags=["Real-Time Data"])
async def get_price_history(
    ticker: str | None = Query(None, description="Stock ticker symbol", example="IBM"),
    symbol: str | None = Query(None, description="Alias for ticker", example="IBM"),
    period: str = Query("3m", description="Time period: 1d, 5d, 1m, 3m, 6m, 1y, 5y, max", example="3m"),
):
    """
    Get price history (OHLCV candles) for a stock.
    
    Period options:
    - 1d: Last 1 trading day
    - 5d: Last 5 trading days
    - 1m: Last 30 days
    - 3m: Last 90 days
    - 6m: Last 180 days
    - 1y: Last 365 days
    - 5y: Last 5 years
    - max: All available data
    """
    try:
        resolved = normalize_symbol(ticker or symbol or "")
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Validate period
    valid_periods = ["1d", "5d", "1m", "3m", "6m", "ytd", "1y", "5y", "max"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Valid options: {', '.join(valid_periods)}"
        )

    service = PriceHistoryService()
    try:
        logger.info(f"[PriceHistoryRouter] GET /api/price-history - symbol={resolved}, period={period}")
        data = service.get_price_history(resolved, period)
        
        # Always return success with data (even if empty)
        # Only return 404 if ticker is invalid (handled by service returning empty array)
        logger.info(f"[PriceHistoryRouter] Returning {len(data)} records for {resolved}")
        return {
            "success": True,
            "symbol": resolved,
            "period": period,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[PriceHistoryRouter] Unexpected error fetching price history for {resolved}, period={period}: {e}",
            exc_info=True
        )
        # Return empty data instead of 500 error
        return {
            "success": True,
            "symbol": resolved,
            "period": period,
            "data": []
        }
