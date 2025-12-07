from fastapi import APIRouter, Query, HTTPException
from services.dividends_service import DividendsService
from shared.python.utils.validation import normalize_symbol, ValidationError

router = APIRouter()

@router.get("/dividends", tags=["Company Info"])
async def get_dividends(ticker: str = Query("IBM", description="Stock ticker symbol", example="IBM")):
    """💰 Get historical dividend payments"""
    try:
        normalized = normalize_symbol(ticker)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    service = DividendsService()
    try:
        data = service.get_dividends(normalized)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
