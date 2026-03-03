from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from database import engine, get_db, Base
from models import Category, Transaction, Budget
from schemas import (
    CategoryCreate, CategoryOut,
    TransactionCreate, TransactionUpdate, TransactionOut,
    BudgetCreate, BudgetOut, DashboardStats,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Tracker")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


def _seed_default_categories(db: Session):
    if db.query(Category).count() > 0:
        return
    defaults = [
        ("Salary", "#22c55e", "income"),
        ("Freelance", "#10b981", "income"),
        ("Investments", "#06b6d4", "income"),
        ("Food & Dining", "#f97316", "expense"),
        ("Transportation", "#eab308", "expense"),
        ("Housing", "#ef4444", "expense"),
        ("Utilities", "#8b5cf6", "expense"),
        ("Entertainment", "#ec4899", "expense"),
        ("Shopping", "#6366f1", "expense"),
        ("Healthcare", "#14b8a6", "expense"),
        ("Education", "#3b82f6", "expense"),
        ("Other", "#64748b", "expense"),
    ]
    for name, color, typ in defaults:
        db.add(Category(name=name, color=color, type=typ))
    db.commit()


@app.on_event("startup")
def startup():
    db = next(get_db())
    _seed_default_categories(db)
    db.close()


# ── Categories ──────────────────────────────────────────────

@app.get("/api/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@app.post("/api/categories", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    cat = Category(**payload.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    tx_count = db.query(Transaction).filter(Transaction.category_id == category_id).count()
    if tx_count > 0:
        raise HTTPException(400, "Cannot delete category with existing transactions")
    db.delete(cat)
    db.commit()
    return {"ok": True}


# ── Transactions ────────────────────────────────────────────

@app.get("/api/transactions", response_model=list[TransactionOut])
def list_transactions(
    type: Optional[str] = None,
    category_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if type:
        q = q.filter(Transaction.type == type)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    return q.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()


@app.post("/api/transactions", response_model=TransactionOut)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == payload.category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    tx = Transaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@app.put("/api/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(404, "Transaction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(404, "Transaction not found")
    db.delete(tx)
    db.commit()
    return {"ok": True}


# ── Budgets ─────────────────────────────────────────────────

@app.get("/api/budgets", response_model=list[BudgetOut])
def list_budgets(db: Session = Depends(get_db)):
    return db.query(Budget).all()


@app.post("/api/budgets", response_model=BudgetOut)
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


@app.delete("/api/budgets/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    b = db.query(Budget).filter(Budget.id == budget_id).first()
    if not b:
        raise HTTPException(404, "Budget not found")
    db.delete(b)
    db.commit()
    return {"ok": True}


# ── Dashboard ───────────────────────────────────────────────

@app.get("/api/dashboard", response_model=DashboardStats)
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
