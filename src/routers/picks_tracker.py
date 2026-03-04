import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Watchlist, User
from src.services.picks_tracker import evaluate_all_picks, get_unique_symbols
from src.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/picks", tags=["picks-tracker"])


@router.get("")
def get_picks(
    type: Optional[str] = Query(None, description="Filter: breakout, swing, options"),
):
    try:
        return evaluate_all_picks(pick_type=type)
    except Exception as e:
        logger.error("picks tracker error: %s", e)
        return {"picks": [], "stats": {}}


@router.post("/seed-watchlist")
def seed_watchlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Bulk-add all unique Discord pick symbols to the watchlist."""
    symbols = get_unique_symbols()
    added = 0
    skipped = 0
    for sym in symbols:
        existing = db.query(Watchlist).filter(Watchlist.user_id == user.id, Watchlist.symbol == sym).first()
        if existing:
            skipped += 1
            continue
        db.add(Watchlist(symbol=sym, name=sym, user_id=user.id))
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped, "total_symbols": len(symbols)}
