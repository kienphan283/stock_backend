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
    financials_legacy_router,
    refresh_router,
    summary_router,
    companies_router
)
from config.settings import settings
from streaming.manager import manager
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    manager.start()
    yield
    # Shutdown
    logger.info("Shutting down...")
    manager.stop()

app = FastAPI(
    title="Stock Data API",
    description="Stock Analytics API with Real Financial Data",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Should be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(quote_router.router)
app.include_router(profile_router.router)
app.include_router(price_history_router.router)  # Legacy endpoint (kept for backward compatibility)
app.include_router(eod_price_router.router)  # New: EOD price charts (date, close only)
app.include_router(candles_router.router)  # New: Intraday candles (OHLCV)
app.include_router(dividends_router.router)
app.include_router(news_router.router)
app.include_router(earnings_router.router)
app.include_router(financials_legacy_router.router)
app.include_router(financial_router.router)
app.include_router(companies_router.router)
app.include_router(refresh_router.router)
app.include_router(summary_router.router)

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Stock Data API is running",
        "config": {
            "db_host": settings.DB_HOST,
            "redis_enabled": bool(settings.REDIS_HOST)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
