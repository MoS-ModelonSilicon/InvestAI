import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import DcaPlan, User
from src.schemas.dca import DcaPlanCreate, DcaPlanUpdate
from src.services.dca import get_dca_dashboard, suggest_monthly_budget
from src.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dca", tags=["dca"])


# ── Dashboard (full overview) ────────────────────────────────


@router.get("/dashboard")
def dca_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return get_dca_dashboard(db, user.id)
    except Exception as e:
        logger.error("dca_dashboard error: %s", e)
        return {
            "plans": [],
            "opportunities": [],
            "monthly_allocation": {
                "total_monthly_budget": 0,
                "total_recommended": 0,
                "over_budget": False,
                "over_budget_amount": 0,
                "allocations": [],
                "month": "",
                "suggestions": [],
            },
            "portfolio_dca_value": 0,
            "next_buy_date": "",
        }


# ── Budget suggestion (based on risk profile) ───────────────


@router.get("/budget-suggestion")
def budget_suggestion(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return suggest_monthly_budget(db, user.id)
    except Exception as e:
        logger.error("budget_suggestion error: %s", e)
        return {"suggestions": ["Unable to load budget suggestions."], "monthly_budget": 0}


# ── CRUD for DCA Plans ───────────────────────────────────────


@router.get("/plans")
def list_plans(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plans = db.query(DcaPlan).filter(DcaPlan.user_id == user.id).order_by(DcaPlan.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "name": p.name,
            "monthly_budget": p.monthly_budget,
            "dip_threshold": p.dip_threshold,
            "dip_multiplier": p.dip_multiplier,
            "is_long_term": bool(p.is_long_term),
            "notes": p.notes,
            "active": bool(p.active),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.post("/plans")
def create_plan(payload: DcaPlanCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.query(DcaPlan).filter(DcaPlan.user_id == user.id, DcaPlan.symbol == payload.symbol.upper()).first()
    if existing:
        raise HTTPException(400, f"DCA plan for {payload.symbol.upper()} already exists")

    plan = DcaPlan(
        user_id=user.id,
        symbol=payload.symbol.upper(),
        name=payload.name,
        monthly_budget=payload.monthly_budget,
        dip_threshold=payload.dip_threshold,
        dip_multiplier=payload.dip_multiplier,
        is_long_term=1 if payload.is_long_term else 0,
        notes=payload.notes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id,
        "symbol": plan.symbol,
        "name": plan.name,
        "monthly_budget": plan.monthly_budget,
        "dip_threshold": plan.dip_threshold,
        "dip_multiplier": plan.dip_multiplier,
        "is_long_term": bool(plan.is_long_term),
        "notes": plan.notes,
        "active": bool(plan.active),
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    payload: DcaPlanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = db.query(DcaPlan).filter(DcaPlan.id == plan_id, DcaPlan.user_id == user.id).first()
    if not plan:
        raise HTTPException(404, "DCA plan not found")

    if payload.monthly_budget is not None:
        plan.monthly_budget = payload.monthly_budget
    if payload.dip_threshold is not None:
        plan.dip_threshold = payload.dip_threshold
    if payload.dip_multiplier is not None:
        plan.dip_multiplier = payload.dip_multiplier
    if payload.is_long_term is not None:
        plan.is_long_term = 1 if payload.is_long_term else 0
    if payload.notes is not None:
        plan.notes = payload.notes
    if payload.active is not None:
        plan.active = 1 if payload.active else 0

    db.commit()
    db.refresh(plan)
    return {"ok": True}


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = db.query(DcaPlan).filter(DcaPlan.id == plan_id, DcaPlan.user_id == user.id).first()
    if not plan:
        raise HTTPException(404, "DCA plan not found")
    db.delete(plan)
    db.commit()
    return {"ok": True}
