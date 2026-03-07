from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.models import Budget, Transaction, User
from src.schemas.budgets import BudgetCreate, BudgetOut
from src.auth import get_current_user

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Budget).filter(Budget.user_id == user.id).all()


@router.get("/status")
def budget_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return budgets with pre-computed spent amounts — eliminates client-side aggregation."""
    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()
    if not budgets:
        return []

    today = date.today()
    month_start = today.replace(day=1)

    # Single query: sum expenses per category for this month
    spent_rows = (
        db.query(Transaction.category_id, func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            Transaction.date >= month_start,
            Transaction.date <= today,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    spent_map = dict(spent_rows)

    result = []
    for b in budgets:
        spent = round(spent_map.get(b.category_id, 0), 2)
        pct = round((spent / b.monthly_limit) * 100, 1) if b.monthly_limit else 0
        color = "var(--red)" if pct > 90 else "#eab308" if pct > 70 else b.category.color
        result.append({
            "id": b.id,
            "category_id": b.category_id,
            "category_name": b.category.name,
            "category_color": b.category.color,
            "monthly_limit": b.monthly_limit,
            "spent": spent,
            "percentage": pct,
            "bar_color": color,
        })
    return result


@router.post("", response_model=BudgetOut)
def upsert_budget(payload: BudgetCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.query(Budget).filter(Budget.user_id == user.id, Budget.category_id == payload.category_id).first()
    if existing:
        existing.monthly_limit = payload.monthly_limit
        db.commit()
        db.refresh(existing)
        return existing
    budget = Budget(**payload.model_dump(), user_id=user.id)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user.id).first()
    if not b:
        raise HTTPException(404, "Budget not found")
    db.delete(b)
    db.commit()
    return {"ok": True}
