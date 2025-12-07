from fastapi import APIRouter, HTTPException, Query
from services.market_metadata_service import MarketMetadataService
import logging
from shared.python.utils.validation import parse_symbols_csv, ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/market/stocks", tags=["Market"])
async def get_market_stocks():
    """
    📊 Get market metadata for all active stocks.

    Response shape:
    {
      "success": true,
      "count": number,
      "stocks": [
        {
          "symbol": "AAPL",
          "name": "Apple Inc.",
          "exchange": "NASDAQ",
          "sector": "Technology" | null
        },
        ...
      ]
    }
    """
    service = MarketMetadataService()
    try:
        result = service.get_stocks_for_heatmap()
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/market/volumes", tags=["Market"])
async def get_accumulated_volumes(
    symbols: str = Query(..., description="Comma-separated list of ticker symbols", example="AAPL,MSFT,GOOGL")
):
    """
    📊 Get accumulated volumes from DB for multiple symbols (batch query, optimized with Redis cache).
    
    Volume được lấy từ cột `volume` trong `stock_trades_realtime` (đã được cộng dồn).
    Volume càng to → ticker càng lớn trong heatmap.
    
    Response shape:
    {
      "success": true,
      "volumes": {
        "AAPL": 12345.0,
        "MSFT": 67890.0,
        ...
      }
    }
    """
    try:
        symbol_list = parse_symbols_csv(symbols)
        
        logger.info(f"[MarketRouter] GET /api/market/volumes - symbols={len(symbol_list)}")
        
        service = MarketMetadataService()
        volumes = service.get_accumulated_volumes(symbol_list)
        
        logger.info(f"[MarketRouter] Returning volumes for {len(volumes)} symbols")
        return {"success": True, "volumes": volumes}
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MarketRouter] Error fetching volumes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))







