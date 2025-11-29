from fastapi import APIRouter, Query, HTTPException
from services.dividends_service import DividendsService

router = APIRouter()

@router.get("/dividends", tags=["Company Info"])
async def get_dividends(ticker: str = Query("IBM", description="Stock ticker symbol", example="IBM")):
    """💰 Get historical dividend payments"""
    service = DividendsService()
    try:
        data = service.get_dividends(ticker)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
