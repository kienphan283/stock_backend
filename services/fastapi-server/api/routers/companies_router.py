from fastapi import APIRouter, HTTPException
from services.companies_service import CompaniesService

router = APIRouter()

@router.get("/api/companies", tags=["Company Info"])
async def get_companies():
    """📋 Get all available companies"""
    service = CompaniesService()
    try:
        result = service.get_companies()
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
