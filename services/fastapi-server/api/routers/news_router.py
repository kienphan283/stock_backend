from fastapi import APIRouter, Query, HTTPException
from services.news_service import NewsService

router = APIRouter()

@router.get("/news", tags=["Company Info"])
async def get_news(
    ticker: str = Query("IBM", description="Stock ticker symbol", example="IBM"),
    limit: int = Query(16, description="Number of news articles to return")
):
    """📰 Get latest company news and headlines"""
    service = NewsService()
    try:
        data = service.get_news(ticker, limit)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
