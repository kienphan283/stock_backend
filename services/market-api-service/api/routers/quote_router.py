from fastapi import APIRouter, Query, HTTPException
from services.quote_service import QuoteService
import logging
from shared.python.utils.validation import (
    normalize_symbol,
    parse_symbols_csv,
    ValidationError,
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/quote", tags=["Real-Time Data"])
@router.get("/api/quote", tags=["Real-Time Data"])
async def get_quote(
    ticker: str | None = Query(None, description="Stock ticker symbol", example="IBM"),
    symbol: str | None = Query(None, description="Alias for ticker", example="IBM"),
):
    try:
        resolved = normalize_symbol(ticker or symbol or "")
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    service = QuoteService()
    try:
        logger.info(f"[quote_router] Fetching quote for {resolved}")
        data = service.get_quote(resolved)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"[quote_router] Error fetching quote for {resolved}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/quote/previous-closes", tags=["Real-Time Data"])
async def get_previous_closes_batch(
    symbols: str = Query(..., description="Comma-separated list of ticker symbols", example="AAPL,MSFT,GOOGL")
):
    """
    Batch API để lấy previousClose cho nhiều symbols cùng lúc (tối ưu performance).
    
    Lấy giá close của record đầu tiên (ngày mới nhất) từ bảng stock_eod_prices cho mỗi symbol.
    
    Response shape:
    {
      "success": true,
      "previousCloses": {
        "AAPL": 284.15,
        "MSFT": 490.00,
        ...
      }
    }
    """
    try:
        symbol_list = parse_symbols_csv(symbols)
        
        logger.info(f"[quote_router] GET /api/quote/previous-closes - symbols={len(symbol_list)}")
        
        service = QuoteService()
        previous_closes = service.get_previous_closes_batch(symbol_list)
        
        logger.info(f"[quote_router] Returning previousCloses for {len(previous_closes)} symbols")
        return {"success": True, "previousCloses": previous_closes}
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[quote_router] Error fetching previousCloses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/quote/latest-eod", tags=["Real-Time Data"])
async def get_latest_eod_batch(
    symbols: str = Query(..., description="Comma-separated list of ticker symbols", example="AAPL,MSFT,GOOGL"),
    auto_fetch: bool = Query(True, description="Automatically fetch and insert EOD if missing")
):
    """
    Batch API để lấy latest EOD data (price, volume, changePercent) cho nhiều symbols.
    Dùng khi market đóng để hiển thị dữ liệu của phiên vừa kết thúc.
    
    Nếu auto_fetch=True và không có dữ liệu của ngày mới nhất, sẽ tự động fetch từ API (Alpaca/yfinance) và insert vào DB.
    
    Response shape:
    {
      "success": true,
      "data": {
        "AAPL": {
          "price": 284.15,
          "volume": 12345678,
          "changePercent": 1.23,
          "previousClose": 280.50
        },
        ...
      }
    }
    """
    try:
        symbol_list = parse_symbols_csv(symbols)
        
        logger.info(f"[quote_router] GET /api/quote/latest-eod - symbols={len(symbol_list)}, auto_fetch={auto_fetch}")
        
        service = QuoteService()
        eod_data = service.get_latest_eod_batch(symbol_list, auto_fetch=auto_fetch)
        
        logger.info(f"[quote_router] Returning latest EOD data for {len(eod_data)} symbols")
        return {"success": True, "data": eod_data}
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[quote_router] Error fetching latest EOD data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
