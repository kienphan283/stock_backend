from fastapi import APIRouter, Query, HTTPException
from services.quote_service import QuoteService
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
