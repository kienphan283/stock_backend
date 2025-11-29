from fastapi import APIRouter, Depends, HTTPException, Query
from services.financial_service import FinancialService
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class StatementType(str, Enum):
    IS = "IS"
    BS = "BS"
    CF = "CF"

class PeriodType(str, Enum):
    annual = "annual"
    quarterly = "quarterly"

class FinancialDataResponse(BaseModel):
    company: str
    type: str
    period: str
    periods: List[str]
    data: Dict[str, Dict[str, float]]

@router.get("/api/financials", response_model=FinancialDataResponse, tags=["Financial Data"])
async def get_financials(
    symbol: str = Query(None, description="Stock ticker symbol (alias for company)", example="IBM"),
    company: str = Query(None, description="Company ticker symbol", example="IBM"),
    type: StatementType = Query(...),
    period: PeriodType = Query(...)
):
    """
    Get financial statements (IS, BS, CF) for a company.
    
    Schema mapping:
    - symbol/company (e.g., "IBM") → company.company_id (ticker = company_id for US stocks)
    - Uses financial_oltp schema (independent from market_data_oltp)
    
    Args:
        symbol: Stock ticker symbol (preferred)
        company: Company ticker symbol (alias, for backward compatibility)
        type: Statement type (IS, BS, CF)
        period: Period type (annual, quarterly)
    """
    # Resolve symbol or company parameter
    resolved = (symbol or company or "").upper()
    if not resolved:
        raise HTTPException(status_code=400, detail="symbol or company is required")
    
    logger.info(f"[FinancialRouter] GET /api/financials - symbol={resolved}, type={type.value}, period={period.value}")
    service = FinancialService()
    try:
        # Use resolved symbol as company_id (ticker = company_id for US stocks)
        result = service.get_financials(resolved, type.value, period.value)
        # Return result even if empty (empty periods/data arrays)
        # This allows frontend to handle "no data" gracefully instead of 404
        if result is None:
            logger.warning(f"[FinancialRouter] Service returned None for {resolved}")
            result = {
                "company": resolved,
                "type": type.value,
                "period": period.value,
                "periods": [],
                "data": {}
            }
        logger.info(f"[FinancialRouter] Returning result with {len(result.get('periods', []))} periods")
        return result
    except ValueError as e:
        logger.error(f"[FinancialRouter] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[FinancialRouter] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
