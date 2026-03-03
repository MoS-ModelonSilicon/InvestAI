from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Holding
from src.schemas.portfolio import HoldingCreate, HoldingOut, PortfolioSummary
from src.services.portfolio import calculate_portfolio, get_portfolio_performance

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/summary")
def portfolio_summary(db: Session = Depends(get_db)):
    return calculate_portfolio(db)


@router.get("/performance")
def portfolio_performance(db: Session = Depends(get_db)):
    return get_portfolio_performance(db)


@router.get("/holdings")
def list_holdings(db: Session = Depends(get_db)):
    return db.query(Holding).order_by(Holding.buy_date.desc()).all()


@router.post("/holdings")
def add_holding(payload: HoldingCreate, db: Session = Depends(get_db)):
    holding = Holding(**payload.model_dump())
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/holdings/{holding_id}")
def remove_holding(holding_id: int, db: Session = Depends(get_db)):
    h = db.query(Holding).filter(Holding.id == holding_id).first()
    if not h:
        raise HTTPException(404, "Holding not found")
    db.delete(h)
    db.commit()
    return {"ok": True}
