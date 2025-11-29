from fastapi import APIRouter, Query, HTTPException
from services.profile_service import ProfileService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/profile", tags=["Company Info"])
@router.get("/api/profile", tags=["Company Info"])
async def get_profile(
    ticker: str | None = Query(None, example="IBM"),
    symbol: str | None = Query(None, example="IBM"),
):
    """Get company profile with industry, sector, and description"""
    resolved = (ticker or symbol or "").upper()
    if not resolved:
        raise HTTPException(status_code=400, detail="ticker or symbol is required")

    service = ProfileService()
    try:
        logger.info(f"[profile_router] Fetching profile for {resolved}")
        data = service.get_profile(resolved)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"[profile_router] Error fetching profile for {resolved}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
