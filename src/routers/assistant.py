"""
AI Assistant router — chat streaming + suggestion CRUD.

Endpoints:
  POST /api/assistant/chat     — SSE streaming chat with model routing
  POST /api/assistant/suggest  — manual suggestion submission
  GET  /api/assistant/suggestions — admin: list all suggestions
  PUT  /api/assistant/suggestions/{id} — admin: update suggestion status
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth import get_current_user, require_admin
from src.database import get_db
from src.models import Suggestion, User
from src.schemas.assistant import (
    ChatRequest,
    SuggestionCreate,
    SuggestionOut,
    SuggestionUpdateStatus,
)
from src.services.assistant import chat_stream, _is_configured

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


# ── Chat (SSE streaming) ─────────────────────────────────────


@router.post("/chat")
def assistant_chat(
    req: ChatRequest,
    user=Depends(get_current_user),
):
    """Stream AI assistant response via Server-Sent Events."""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    return StreamingResponse(
        chat_stream(messages, user_id=user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
def assistant_status():
    """Check if AI assistant is configured."""
    return {"configured": _is_configured()}


# ── Suggestions (manual submit) ──────────────────────────────


@router.post("/suggest")
def submit_suggestion(
    body: SuggestionCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a feature suggestion manually."""
    message = body.message.strip()
    if not message:
        raise HTTPException(400, "Suggestion cannot be empty")
    if len(message) > 2000:
        raise HTTPException(400, "Suggestion too long (max 2000 chars)")

    suggestion = Suggestion(
        user_id=user.id,
        message=message,
        ai_summary=message[:200],
        category=body.category,
        status="new",
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return {"id": suggestion.id, "message": "Suggestion submitted. Thank you!"}


@router.post("/suggest/{suggestion_id}/vote")
def vote_suggestion(
    suggestion_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upvote a suggestion."""
    s = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(404, "Suggestion not found")
    s.votes = (s.votes or 0) + 1
    db.commit()
    return {"votes": s.votes}


# ── Admin: manage suggestions ────────────────────────────────


@router.get("/suggestions")
def list_suggestions(
    status: str = Query("", description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all suggestions (admin only)."""
    q = db.query(Suggestion)
    if status:
        q = q.filter(Suggestion.status == status)

    total = q.count()
    items = q.order_by(Suggestion.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for s in items:
        user = db.query(User).filter(User.id == s.user_id).first()
        results.append(
            SuggestionOut(
                id=s.id,
                user_id=s.user_id,
                message=s.message,
                ai_summary=s.ai_summary,
                category=s.category,
                status=s.status,
                admin_notes=s.admin_notes or "",
                votes=s.votes or 0,
                created_at=s.created_at,
                user_email=user.email if user else "",
            )
        )

    return {"items": results, "total": total, "page": page, "per_page": per_page}


@router.put("/suggestions/{suggestion_id}")
def update_suggestion(
    suggestion_id: int,
    body: SuggestionUpdateStatus,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update suggestion status (admin only)."""
    s = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(404, "Suggestion not found")

    valid = {"new", "reviewed", "planned", "done", "declined"}
    if body.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid)}")

    s.status = body.status
    if body.admin_notes is not None:
        s.admin_notes = body.admin_notes
    db.commit()
    return {"id": s.id, "status": s.status}


@router.get("/suggestions/stats")
def suggestion_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Suggestion stats for admin dashboard."""
    total = db.query(func.count(Suggestion.id)).scalar() or 0
    new_count = db.query(func.count(Suggestion.id)).filter(Suggestion.status == "new").scalar() or 0
    planned = db.query(func.count(Suggestion.id)).filter(Suggestion.status == "planned").scalar() or 0
    done = db.query(func.count(Suggestion.id)).filter(Suggestion.status == "done").scalar() or 0
    return {"total": total, "new": new_count, "planned": planned, "done": done}
