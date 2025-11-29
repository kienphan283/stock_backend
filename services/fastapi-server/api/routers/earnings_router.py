from fastapi import APIRouter, HTTPException
from services.earnings_service import EarningsService

router = APIRouter()

@router.get("/earnings", tags=["Company Info"])
async def get_earnings():
    """Get earnings data"""
    service = EarningsService()
    try:
        data = service.get_earnings()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
