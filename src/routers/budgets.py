from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Budget
from src.schemas.budgets import BudgetCreate, BudgetOut

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(db: Session = Depends(get_db)):
    return db.query(Budget).all()


@router.post("", response_model=BudgetOut)
def upsert_budget(payload: BudgetCreate, db: Session = Depends(get_db)):
    existing = db.query(Budget).filter(Budget.category_id == payload.category_id).first()
    if existing:
        existing.monthly_limit = payload.monthly_limit
        db.commit()
        db.refresh(existing)
        return existing
    budget = Budget(**payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    b = db.query(Budget).filter(Budget.id == budget_id).first()
    if not b:
        raise HTTPException(404, "Budget not found")
    db.delete(b)
    db.commit()
    return {"ok": True}
