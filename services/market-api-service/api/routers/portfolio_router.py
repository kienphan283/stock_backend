from fastapi import APIRouter, Depends, HTTPException, Body, Query
from services.portfolio_service import PortfolioService
from pydantic import BaseModel
from typing import Optional, List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class TransactionCreate(BaseModel):
    portfolio_id: str
    ticker: str
    transaction_type: str
    quantity: float
    price: float
    fee: Optional[float] = 0
    note: Optional[str] = None

class PortfolioCreate(BaseModel):
    user_id: str
    name: str
    currency: Optional[str] = 'USD'
    goal_type: Optional[str] = 'VALUE'
    target_amount: Optional[float] = None
    note: Optional[str] = None

# --- Endpoints ---

@router.get("/api/portfolio/holdings", tags=["Portfolio"])
async def get_holdings(
    portfolio_id: str = Query(..., description="Portfolio ID")
):
    try:
        service = PortfolioService()
        holdings = service.get_holdings_with_market_data(portfolio_id)
        return {"success": True, "data": holdings}
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/portfolio/transactions", tags=["Portfolio"])
async def add_transaction(
    transaction: TransactionCreate = Body(...)
):
    try:
        service = PortfolioService()
        tx_id = service.add_transaction(
            portfolio_id=transaction.portfolio_id,
            ticker=transaction.ticker.upper(),
            transaction_type=transaction.transaction_type.upper(),
            quantity=transaction.quantity,
            price=transaction.price,
            fee=transaction.fee,
            note=transaction.note
        )
        return {"success": True, "data": {"transaction_id": tx_id}}
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/transactions", tags=["Portfolio"])
async def get_transactions(
    portfolio_id: str = Query(..., description="Portfolio ID"),
    ticker: Optional[str] = Query(None, description="Filter by ticker")
):
    try:
        service = PortfolioService()
        transactions = service.get_transactions(portfolio_id, ticker)
        return {"success": True, "data": transactions}
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolio/portfolios", tags=["Portfolio"])
async def get_user_portfolios(
    user_id: str = Query(..., description="User ID")
):
    try:
        service = PortfolioService()
        result = service.get_portfolio_summary(user_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error fetching portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/portfolio/create", tags=["Portfolio"])
async def create_portfolio(
    portfolio: PortfolioCreate = Body(...)
):
    try:
        service = PortfolioService()
        p_id = service.create_portfolio(
            user_id=portfolio.user_id, 
            name=portfolio.name, 
            currency=portfolio.currency,
            goal_type=portfolio.goal_type,
            target_amount=portfolio.target_amount,
            note=portfolio.note
        )
        return {"success": True, "data": {"portfolio_id": p_id}}
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/portfolio/{portfolio_id}/transactions/{transaction_id}", tags=["Portfolio"])
async def delete_transaction(
    portfolio_id: str,
    transaction_id: str
):
    try:
        service = PortfolioService()
        success = service.delete_transaction(transaction_id, portfolio_id)
        if not success:
             raise HTTPException(status_code=404, detail="Transaction not found")
        return {"success": True, "message": "Transaction deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class TransactionUpdate(BaseModel):
    ticker: str
    transaction_type: str
    quantity: float
    price: float
    fee: Optional[float] = 0
    date: Optional[str] = None
    note: Optional[str] = None

@router.put("/api/portfolio/{portfolio_id}/transactions/{transaction_id}", tags=["Portfolio"])
async def update_transaction(
    portfolio_id: str,
    transaction_id: str,
    transaction: TransactionUpdate = Body(...)
):
    try:
        service = PortfolioService()
        success = service.update_transaction(
            transaction_id=transaction_id,
            portfolio_id=portfolio_id,
            ticker=transaction.ticker.upper(),
            transaction_type=transaction.transaction_type.upper(),
            quantity=transaction.quantity,
            price=transaction.price,
            fee=transaction.fee,
            date=transaction.date,
            note=transaction.note
        )
        if not success:
             raise HTTPException(status_code=404, detail="Transaction not found")
        return {"success": True, "message": "Transaction updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/portfolio/{portfolio_id}/holdings/{ticker}", tags=["Portfolio"])
async def delete_holding(
    portfolio_id: str,
    ticker: str
):
    try:
        service = PortfolioService()
        success = service.delete_holding(portfolio_id, ticker.upper())
        if not success:
             raise HTTPException(status_code=404, detail="Holding not found")
        return {"success": True, "message": "Holding deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting holding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/portfolio/{portfolio_id}", tags=["Portfolio"])
async def delete_portfolio(
    portfolio_id: str,
    user_id: str = Query(..., description="User ID") 
):
    try:
        service = PortfolioService()
        success = service.delete_portfolio(portfolio_id, user_id)
        if not success:
             raise HTTPException(status_code=404, detail="Portfolio not found or access denied")
        return {"success": True, "message": "Portfolio deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
