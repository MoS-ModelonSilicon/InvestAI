"""
Admin panel — user management, system stats, account actions.
All endpoints require is_admin=1.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth import require_admin, hash_password
from src.database import get_db
from src.models import (
    User,
    Transaction,
    Category,
    Budget,
    Holding,
    Watchlist,
    Alert,
    DcaPlan,
    RiskProfile,
    PasswordReset,
    Suggestion,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    is_admin: int
    is_active: int
    created_at: datetime | None
    transaction_count: int = 0
    holding_count: int = 0
    watchlist_count: int = 0
    alert_count: int = 0

    class Config:
        from_attributes = True


class ToggleAdminBody(BaseModel):
    user_id: int


class ToggleActiveBody(BaseModel):
    user_id: int


class ResetPasswordBody(BaseModel):
    user_id: int
    new_password: str


class DeleteUserBody(BaseModel):
    user_id: int


# ── System Stats ──────────────────────────────────────────────


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """High-level system stats for the admin dashboard."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == 1).scalar() or 0
    admin_count = db.query(func.count(User.id)).filter(User.is_admin == 1).scalar() or 0
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    total_holdings = db.query(func.count(Holding.id)).scalar() or 0
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    total_dca_plans = db.query(func.count(DcaPlan.id)).scalar() or 0
    total_watchlist = db.query(func.count(Watchlist.id)).scalar() or 0
    total_suggestions = db.query(func.count(Suggestion.id)).scalar() or 0
    new_suggestions = db.query(func.count(Suggestion.id)).filter(Suggestion.status == "new").scalar() or 0

    # New users in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_7d = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0

    # New users in last 30 days
    month_ago = datetime.utcnow() - timedelta(days=30)
    new_users_30d = db.query(func.count(User.id)).filter(User.created_at >= month_ago).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "disabled_users": total_users - active_users,
        "admin_count": admin_count,
        "new_users_7d": new_users_7d,
        "new_users_30d": new_users_30d,
        "total_transactions": total_transactions,
        "total_holdings": total_holdings,
        "total_alerts": total_alerts,
        "total_dca_plans": total_dca_plans,
        "total_watchlist": total_watchlist,
        "total_suggestions": total_suggestions,
        "new_suggestions": new_suggestions,
    }


# ── User List ─────────────────────────────────────────────────


@router.get("/users")
def list_users(
    search: str = Query("", description="Filter by email or name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Paginated list of all users with activity counts."""
    q = db.query(User)

    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter((func.lower(User.email).like(pattern)) | (func.lower(User.name).like(pattern)))

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for u in users:
        results.append(
            UserOut(
                id=u.id,
                email=u.email,
                name=u.name or "",
                is_admin=u.is_admin or 0,
                is_active=u.is_active if u.is_active is not None else 1,
                created_at=u.created_at,
                transaction_count=db.query(func.count(Transaction.id)).filter(Transaction.user_id == u.id).scalar()
                or 0,
                holding_count=db.query(func.count(Holding.id)).filter(Holding.user_id == u.id).scalar() or 0,
                watchlist_count=db.query(func.count(Watchlist.id)).filter(Watchlist.user_id == u.id).scalar() or 0,
                alert_count=db.query(func.count(Alert.id)).filter(Alert.user_id == u.id).scalar() or 0,
            )
        )

    return {"users": [r.model_dump() for r in results], "total": total, "page": page, "per_page": per_page}


# ── User Detail ───────────────────────────────────────────────


@router.get("/users/{user_id}")
def get_user_detail(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Full detail for a single user including all their data counts."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name or "",
        "is_admin": user.is_admin or 0,
        "is_active": user.is_active if user.is_active is not None else 1,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "transactions": db.query(func.count(Transaction.id)).filter(Transaction.user_id == user.id).scalar() or 0,
        "holdings": db.query(func.count(Holding.id)).filter(Holding.user_id == user.id).scalar() or 0,
        "watchlist": db.query(func.count(Watchlist.id)).filter(Watchlist.user_id == user.id).scalar() or 0,
        "alerts": db.query(func.count(Alert.id)).filter(Alert.user_id == user.id).scalar() or 0,
        "dca_plans": db.query(func.count(DcaPlan.id)).filter(DcaPlan.user_id == user.id).scalar() or 0,
        "budgets": db.query(func.count(Budget.id)).filter(Budget.user_id == user.id).scalar() or 0,
        "risk_profiles": db.query(func.count(RiskProfile.id)).filter(RiskProfile.user_id == user.id).scalar() or 0,
    }


# ── Toggle Admin ──────────────────────────────────────────────


@router.post("/toggle-admin")
def toggle_admin(body: ToggleAdminBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Promote or demote a user to/from admin."""
    if body.user_id == admin.id:
        raise HTTPException(400, "You cannot change your own admin status")

    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_admin = 0 if user.is_admin else 1
    db.commit()
    return {"ok": True, "user_id": user.id, "is_admin": user.is_admin}


# ── Toggle Active (Enable / Disable) ─────────────────────────


@router.post("/toggle-active")
def toggle_active(body: ToggleActiveBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Enable or disable a user account."""
    if body.user_id == admin.id:
        raise HTTPException(400, "You cannot disable your own account")

    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = 0 if (user.is_active if user.is_active is not None else 1) else 1
    db.commit()
    return {"ok": True, "user_id": user.id, "is_active": user.is_active}


# ── Admin Reset Password ─────────────────────────────────────


@router.post("/reset-password")
def admin_reset_password(body: ResetPasswordBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Admin force-resets a user's password."""
    if len(body.new_password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters")

    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "user_id": user.id, "message": f"Password reset for {user.email}"}


# ── Delete User ───────────────────────────────────────────────


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Permanently delete a user and ALL their data. Use with caution."""
    if user_id == admin.id:
        raise HTTPException(400, "You cannot delete your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Delete all user data (cascade)
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.query(Holding).filter(Holding.user_id == user_id).delete()
    db.query(Watchlist).filter(Watchlist.user_id == user_id).delete()
    db.query(Alert).filter(Alert.user_id == user_id).delete()
    db.query(DcaPlan).filter(DcaPlan.user_id == user_id).delete()
    db.query(Budget).filter(Budget.user_id == user_id).delete()
    db.query(RiskProfile).filter(RiskProfile.user_id == user_id).delete()
    db.query(PasswordReset).filter(PasswordReset.user_id == user_id).delete()
    db.query(Category).filter(Category.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"ok": True, "message": f"User {user.email} and all their data deleted"}
