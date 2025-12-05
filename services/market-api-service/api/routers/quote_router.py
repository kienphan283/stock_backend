from fastapi import APIRouter, Query, HTTPException
from services.quote_service import QuoteService
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/quote", tags=["Real-Time Data"])
@router.get("/api/quote", tags=["Real-Time Data"])
async def get_quote(
    ticker: str | None = Query(None, description="Stock ticker symbol", example="IBM"),
    symbol: str | None = Query(None, description="Alias for ticker", example="IBM"),
):
    resolved = (ticker or symbol or "").upper()
    if not resolved:
        raise HTTPException(status_code=400, detail="ticker or symbol is required")

    service = QuoteService()
    try:
        logger.info(f"[quote_router] Fetching quote for {resolved}")
        data = service.get_quote(resolved)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"[quote_router] Error fetching quote for {resolved}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/quote/previous-closes", tags=["Real-Time Data"])
async def get_previous_closes_batch(
    symbols: str = Query(..., description="Comma-separated list of ticker symbols", example="AAPL,MSFT,GOOGL")
):
    """
    Batch API để lấy previousClose cho nhiều symbols cùng lúc (tối ưu performance).
    
    Lấy giá close của record đầu tiên (ngày mới nhất) từ bảng stock_eod_prices cho mỗi symbol.
    
    Response shape:
    {
      "success": true,
      "previousCloses": {
        "AAPL": 284.15,
        "MSFT": 490.00,
        ...
      }
    }
    """
    try:
        # Parse comma-separated symbols
        symbol_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="At least one symbol is required")
        
        logger.info(f"[quote_router] GET /api/quote/previous-closes - symbols={len(symbol_list)}")
        
        service = QuoteService()
        previous_closes = service.get_previous_closes_batch(symbol_list)
        
        logger.info(f"[quote_router] Returning previousCloses for {len(previous_closes)} symbols")
        return {"success": True, "previousCloses": previous_closes}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[quote_router] Error fetching previousCloses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
