from fastapi import APIRouter, HTTPException
from services.summary_service import SummaryService

router = APIRouter()

@router.get("/summary", tags=["System"])
async def get_summary():
    """Get data summary and status"""
    service = SummaryService()
    try:
        data = service.get_summary()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
