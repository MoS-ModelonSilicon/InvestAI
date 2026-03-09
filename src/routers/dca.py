import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import DcaPlan, User
from src.schemas.dca import DcaPlanCreate, DcaPlanUpdate, DcaExecutionCreate
from src.services.dca import (
    get_dca_dashboard,
    suggest_monthly_budget,
    DCA_PRESETS,
    get_wizard_preview,
    log_execution,
    get_execution_history,
    backtest_dca,
    get_rebalance_suggestions,
)
from src.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dca", tags=["dca"])


# ── Dashboard (full overview) ────────────────────────────────


@router.get("/dashboard")
def dca_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        data = get_dca_dashboard(db, user.id)
        # Attach execution stats and rebalance suggestions
        try:
            hist = get_execution_history(db, user.id)
            data["execution_stats"] = hist["plan_stats"]
        except Exception:
            data["execution_stats"] = []
        try:
            data["rebalance_suggestions"] = get_rebalance_suggestions(db, user.id)
        except Exception:
            data["rebalance_suggestions"] = []
        return data
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
            "execution_stats": [],
            "rebalance_suggestions": [],
        }


# ── Budget suggestion (based on risk profile) ───────────────


@router.get("/budget-suggestion")
def budget_suggestion(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return suggest_monthly_budget(db, user.id)
    except Exception as e:
        logger.error("budget_suggestion error: %s", e)
        return {"suggestions": ["Unable to load budget suggestions."], "monthly_budget": 0}


# ── Wizard ───────────────────────────────────────────────────


@router.get("/wizard/presets")
def wizard_presets():
    """Return the three strategy presets for the setup wizard."""
    return {"presets": DCA_PRESETS}


@router.get("/wizard/preview")
def wizard_preview(
    symbol: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get stock info + suggested budget for the wizard."""
    return get_wizard_preview(symbol.upper().strip(), user.id, db)


# ── Backtest ─────────────────────────────────────────────────


@router.get("/backtest")
def run_backtest(
    symbol: str = Query(..., min_length=1),
    monthly: float = Query(200, gt=0),
    dip_threshold: float = Query(-15.0, le=0),
    dip_multiplier: float = Query(2.0, ge=1.0),
    months: int = Query(24, ge=3, le=120),
):
    """Run a historical DCA backtest simulation."""
    try:
        return backtest_dca(
            symbol=symbol.upper().strip(),
            monthly_budget=monthly,
            dip_threshold=dip_threshold,
            dip_multiplier=dip_multiplier,
            months=months,
        )
    except Exception as e:
        logger.error("backtest error: %s", e)
        return {"error": str(e)}


# ── Execution Tracking ───────────────────────────────────────


@router.post("/executions")
def create_execution(
    payload: DcaExecutionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Log a DCA buy or skip."""
    result = log_execution(
        db=db,
        user_id=user.id,
        plan_id=payload.plan_id,
        amount_invested=payload.amount_invested,
        shares_bought=payload.shares_bought,
        price=payload.price,
        was_dip_buy=payload.was_dip_buy,
        skipped=payload.skipped,
        skip_reason=payload.skip_reason,
        exec_date=payload.date,
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/executions")
def list_executions(
    plan_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get execution history with streak stats."""
    return get_execution_history(db, user.id, plan_id)


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
