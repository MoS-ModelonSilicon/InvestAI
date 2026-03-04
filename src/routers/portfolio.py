import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Holding, User
from src.schemas.portfolio import HoldingCreate, HoldingOut, PortfolioSummary
from src.services.portfolio import calculate_portfolio, get_portfolio_performance
from src.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

_EMPTY_SUMMARY = {
    "total_invested": 0,
    "total_value": 0,
    "total_gain_loss": 0,
    "total_gain_loss_pct": 0,
    "holdings": [],
    "sector_allocation": [],
    "best_performer": None,
    "worst_performer": None,
}


@router.get("/summary")
def portfolio_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return calculate_portfolio(db, user.id)
    except Exception as e:
        logger.error("portfolio_summary error: %s", e)
        return _EMPTY_SUMMARY


@router.get("/performance")
def portfolio_performance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return get_portfolio_performance(db, user.id)
    except Exception as e:
        logger.error("portfolio_performance error: %s", e)
        return {"dates": [], "portfolio": [], "benchmark": []}


@router.get("/holdings")
def list_holdings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Holding).filter(Holding.user_id == user.id).order_by(Holding.buy_date.desc()).all()


@router.post("/holdings")
def add_holding(payload: HoldingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    holding = Holding(**payload.model_dump(), user_id=user.id)
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}")
def remove_holding(holding_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    h = db.query(Holding).filter(Holding.id == holding_id, Holding.user_id == user.id).first()
    if not h:
        raise HTTPException(404, "Holding not found")
    db.delete(h)
    db.commit()
    return {"ok": True}
