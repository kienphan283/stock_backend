from fastapi import APIRouter, HTTPException
from services.refresh_service import RefreshService

router = APIRouter()

@router.post("/refresh", tags=["System"])
async def refresh_data():
    """Refresh data from Finnhub API"""
    service = RefreshService()
    try:
        success = service.refresh_data()
        if success:
            return {"success": True, "message": "Data refreshed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Data refresh failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
