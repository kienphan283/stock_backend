from fastapi import APIRouter, HTTPException
from services.financials_legacy_service import FinancialsLegacyService

router = APIRouter()

@router.get("/financials", tags=["Financial Data"])
async def get_financials_legacy():
    """Get financial statements (legacy endpoint using data loader)"""
    service = FinancialsLegacyService()
    try:
        data = service.get_financials()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
