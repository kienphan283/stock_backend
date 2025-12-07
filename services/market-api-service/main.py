# SERVICE BOUNDARY: This service must NOT read Kafka or Redis Streams.
# It can access Postgres and Redis Cache only.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import (
    quote_router,
    financial_router,
    profile_router,
    price_history_router,
    eod_price_router,
    candles_router,
    dividends_router,
    news_router,
    earnings_router,
    refresh_router,
    summary_router,
    companies_router,
    market_router,
)
from config.settings import settings
from shared.python.utils.logging_config import get_logger
from shared.python.utils.env import validate_env

validate_env(["DB_PASSWORD"])

logger = get_logger(__name__)

app = FastAPI(
    title="Market Data API",
    description="Market and Financial Data API Service",
    version="3.0.0"
)

# Enable CORS
allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers (removed financials_legacy_router)
app.include_router(quote_router.router)
app.include_router(profile_router.router)
app.include_router(price_history_router.router)  # Legacy endpoint (kept for backward compatibility)
app.include_router(eod_price_router.router)  # EOD price charts (date, close only)
app.include_router(candles_router.router)  # Intraday candles (OHLCV)
app.include_router(dividends_router.router)
app.include_router(news_router.router)
app.include_router(earnings_router.router)
app.include_router(financial_router.router)
app.include_router(companies_router.router)
app.include_router(refresh_router.router)
app.include_router(summary_router.router)
app.include_router(market_router.router)

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Market Data API is running",
        "service": "market-api-service",
        "config": {
            "db_host": settings.DB_HOST,
            "redis_enabled": bool(settings.REDIS_HOST)
        }
    }

@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "service": "market-api-service"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

