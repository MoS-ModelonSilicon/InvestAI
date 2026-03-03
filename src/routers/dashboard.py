from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Transaction, Budget
from src.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    if not date_from:
        today = date.today()
        date_from = today.replace(day=1) - timedelta(days=180)
    if not date_to:
        date_to = date.today()

    txs = db.query(Transaction).filter(
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    ).all()

    total_income = sum(t.amount for t in txs if t.type == "income")
    total_expenses = sum(t.amount for t in txs if t.type == "expense")

    cat_map: dict[int, dict] = {}
    for t in txs:
        if t.type != "expense":
            continue
        if t.category_id not in cat_map:
            cat_map[t.category_id] = {
                "category_id": t.category_id,
                "category_name": t.category.name,
                "color": t.category.color,
                "total": 0.0,
            }
        cat_map[t.category_id]["total"] += t.amount

    month_map: dict[str, dict] = {}
    for t in txs:
        key = t.date.strftime("%Y-%m")
        if key not in month_map:
            month_map[key] = {"month": key, "income": 0.0, "expenses": 0.0}
        if t.type == "income":
            month_map[key]["income"] += t.amount
        else:
            month_map[key]["expenses"] += t.amount
    monthly_trend = sorted(month_map.values(), key=lambda x: x["month"])

    budgets = db.query(Budget).all()
    current_month = date.today().strftime("%Y-%m")
    budget_status = []
    for b in budgets:
        spent = sum(
            t.amount for t in txs
            if t.category_id == b.category_id
            and t.type == "expense"
            and t.date.strftime("%Y-%m") == current_month
        )
        budget_status.append({
            "category_id": b.category_id,
            "category_name": b.category.name,
            "color": b.category.color,
            "monthly_limit": b.monthly_limit,
            "spent": spent,
            "percentage": round((spent / b.monthly_limit) * 100, 1) if b.monthly_limit else 0,
        })

    return DashboardStats(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_balance=round(total_income - total_expenses, 2),
        category_breakdown=list(cat_map.values()),
        monthly_trend=monthly_trend,
        budget_status=budget_status,
    )
