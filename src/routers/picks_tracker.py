import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
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
    source: Optional[str] = Query(None, description="Filter by source: discord, reddit, tradingview, finviz"),
):
    try:
        return evaluate_all_picks(pick_type=type, source_filter=source)
    except Exception as e:
        logger.error("picks tracker error: %s", e)
        return {"picks": [], "stats": {}}


@router.post("/refresh")
def refresh_picks(background_tasks: BackgroundTasks):
    """
    Trigger a refresh of picks from all external sources (Reddit, TradingView, Finviz).
    Runs in the background so the response returns immediately.
    """
    from src.services.scrapers.pipeline import run_pipeline, get_last_refresh

    background_tasks.add_task(run_pipeline)
    return {
        "status": "refresh_started",
        "last_refresh": get_last_refresh(),
        "message": "Fetching new picks from all sources in the background. Refresh in ~60s to see results.",
    }


@router.post("/seed-db")
def seed_picks_db():
    """One-time import: load discord-picks.json into the database.

    Idempotent — skips if DB already has picks.
    """
    from src.services.scrapers.pipeline import seed_db_from_json

    added = seed_db_from_json()
    return {"seeded": added}


@router.get("/sources")
def get_source_stats():
    """Return pick counts per data source."""
    from src.services.scrapers.pipeline import get_source_stats, get_last_refresh

    stats = get_source_stats()
    stats["last_refresh"] = get_last_refresh()
    return stats


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
