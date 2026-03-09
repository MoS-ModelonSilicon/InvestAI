"""
Unified pick-scraping pipeline: runs all configured scrapers, merges results
into the database (not a flat file), deduplicates, and makes them available
instantly to every user.

Can be called:
1. On-demand via API endpoint (POST /api/picks/refresh)
2. On a background schedule (configurable interval via env var)
3. Manually from the command line: python -m src.services.scrapers.pipeline
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Legacy JSON path – used only for one-time import into DB
_PICKS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static", "data", "discord-picks.json")

# How often the background scheduler re-fetches (default: 4 hours)
REFRESH_INTERVAL = int(os.getenv("PICKS_REFRESH_INTERVAL", str(4 * 3600)))

# Toggle sources on/off via env vars
ENABLE_REDDIT = os.getenv("PICKS_ENABLE_REDDIT", "true").lower() in ("1", "true", "yes")
ENABLE_TRADINGVIEW = os.getenv("PICKS_ENABLE_TRADINGVIEW", "true").lower() in ("1", "true", "yes")
ENABLE_FINVIZ = os.getenv("PICKS_ENABLE_FINVIZ", "true").lower() in ("1", "true", "yes")

# Track last refresh
_last_refresh: Optional[float] = None
_refresh_lock = threading.Lock()


# ── Database helpers ─────────────────────────────────────────


def _save_picks_to_db(pick_dicts: list[dict]) -> int:
    """Insert new picks into the database. Returns count of new rows added."""
    from src.database import SessionLocal
    from src.models import Pick

    db = SessionLocal()
    added = 0
    try:
        for d in pick_dicts:
            # Check for existing pick (dedup by symbol+date+entry+source)
            symbol = d["symbol"].upper().strip()
            date_str = d.get("date", "")
            entry = d.get("entry")
            source = d.get("source", "unknown")

            existing = (
                db.query(Pick)
                .filter(
                    Pick.symbol == symbol,
                    Pick.date == date_str,
                    Pick.entry == entry,
                    Pick.source == source,
                )
                .first()
            )
            if existing:
                continue

            pick = Pick.from_dict(d)
            db.add(pick)
            added += 1

        if added:
            db.commit()
        logger.info("Saved %d new picks to database", added)
    except Exception:
        logger.exception("Failed to save picks to database")
        db.rollback()
    finally:
        db.close()
    return added


def _load_picks_from_db(source_filter: Optional[str] = None) -> list[dict]:
    """Load all picks from the database, optionally filtered by source."""
    from src.database import SessionLocal
    from src.models import Pick

    db = SessionLocal()
    try:
        query = db.query(Pick)
        if source_filter:
            query = query.filter(Pick.source.ilike(f"{source_filter}%"))
        rows = query.order_by(Pick.date.desc()).all()
        return [row.to_dict() for row in rows]
    except Exception:
        logger.exception("Failed to load picks from database")
        return []
    finally:
        db.close()


def _get_db_pick_count() -> int:
    """Return total number of picks in the database."""
    from src.database import SessionLocal
    from src.models import Pick

    db = SessionLocal()
    try:
        return db.query(Pick).count()
    except Exception:
        return 0
    finally:
        db.close()


def seed_db_from_json() -> int:
    """One-time import: load discord-picks.json into the database.

    Safe to call multiple times — it deduplicates.
    Normalizes legacy sources: picks without a '/' in source (e.g. "Nick")
    are prefixed with "discord/" so filters work properly.
    """
    path = os.path.normpath(_PICKS_FILE)
    if not os.path.exists(path):
        logger.info("No legacy picks file found at %s — nothing to seed", path)
        return 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return 0
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read legacy picks file")
        return 0

    already = _get_db_pick_count()
    if already > 0:
        logger.info("DB already has %d picks — skipping bulk seed", already)
        return 0

    # Normalize legacy source names: bare author names → "discord/{author}"
    for d in data:
        src = d.get("source", "unknown")
        if "/" not in src and src.lower() not in ("reddit", "tradingview", "finviz", "unknown"):
            d["source"] = f"discord/{src}"

    added = _save_picks_to_db(data)
    logger.info("Seeded %d picks from JSON into database", added)
    return added


def _dedup_key(pick: dict) -> str:
    """Generate a dedup key for a pick: symbol + date + entry + source."""
    entry = pick.get("entry")
    entry_str = f"{entry:.2f}" if entry else "none"
    return f"{pick['symbol']}:{pick.get('date', '?')}:{entry_str}:{pick.get('source', '')}"


def run_pipeline(
    enable_reddit: Optional[bool] = None,
    enable_tradingview: Optional[bool] = None,
    enable_finviz: Optional[bool] = None,
) -> dict:
    """
    Run the full multi-source scraping pipeline.

    Scrapes all enabled sources, writes new picks to the database,
    and returns a summary.
    """
    global _last_refresh

    if enable_reddit is None:
        enable_reddit = ENABLE_REDDIT
    if enable_tradingview is None:
        enable_tradingview = ENABLE_TRADINGVIEW
    if enable_finviz is None:
        enable_finviz = ENABLE_FINVIZ

    start = time.time()
    summary: dict = {"sources": {}, "new_picks": 0, "total_picks": 0, "duration_sec": 0}

    # Collect picks from all enabled scrapers
    from .base import UnifiedPick

    new_picks: list[UnifiedPick] = []

    if enable_reddit:
        from .reddit_scraper import RedditScraper

        scraper = RedditScraper(
            sort="hot",
            min_upvotes=20,
            max_per_sub=30,
        )
        reddit_picks = scraper.fetch_safe()
        new_picks.extend(reddit_picks)
        summary["sources"]["reddit"] = len(reddit_picks)

    if enable_tradingview:
        from .tradingview_scraper import TradingViewScraper

        scraper = TradingViewScraper(  # type: ignore[assignment]
            max_ideas=40,
            min_volume=500_000,
        )
        tv_picks = scraper.fetch_safe()
        new_picks.extend(tv_picks)
        summary["sources"]["tradingview"] = len(tv_picks)

    if enable_finviz:
        from .finviz_scraper import FinvizScraper

        scraper = FinvizScraper(  # type: ignore[assignment]
            max_per_screen=15,
        )
        fv_picks = scraper.fetch_safe()
        new_picks.extend(fv_picks)
        summary["sources"]["finviz"] = len(fv_picks)

    # Convert to dicts and save to database
    new_dicts = [p.to_dict() for p in new_picks]
    added = _save_picks_to_db(new_dicts)

    summary["new_picks"] = added
    summary["total_picks"] = _get_db_pick_count()
    summary["duration_sec"] = round(time.time() - start, 1)
    summary["timestamp"] = datetime.utcnow().isoformat()

    with _refresh_lock:
        _last_refresh = time.time()

    logger.info(
        "Pipeline complete: %d new picks added (%d total) in %.1fs",
        added,
        summary["total_picks"],
        summary["duration_sec"],
    )

    # Invalidate picks_tracker cache so new picks appear immediately
    try:
        from src.services.picks_tracker import _cache, _cache_lock

        with _cache_lock:
            _cache.clear()
    except Exception:
        pass

    return summary


def get_last_refresh() -> Optional[str]:
    """Return ISO timestamp of last pipeline run, or None."""
    with _refresh_lock:
        if _last_refresh:
            return datetime.utcfromtimestamp(_last_refresh).isoformat()
    return None


def get_source_stats() -> dict:
    """Return counts of picks per source from the database."""
    from src.database import SessionLocal
    from src.models import Pick
    from sqlalchemy import func

    db = SessionLocal()
    try:
        rows = db.query(Pick.source, func.count(Pick.id)).group_by(Pick.source).all()
        stats: dict[str, int] = {}
        total = 0
        for source, count in rows:
            # Normalize: "reddit/r/wallstreetbets" → "reddit"
            base_source = source.split("/")[0] if "/" in source else source
            stats[base_source] = stats.get(base_source, 0) + count
            total += count
        stats["total"] = total
        return stats
    except Exception:
        logger.exception("Failed to get source stats")
        return {"total": 0}
    finally:
        db.close()


# --- Background scheduler ---

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop = threading.Event()


def start_background_scheduler():
    """Start a background thread that periodically refreshes picks."""
    global _scheduler_thread

    if REFRESH_INTERVAL <= 0:
        logger.info("Picks refresh scheduler disabled (interval=%d)", REFRESH_INTERVAL)
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.info("Picks scheduler already running")
        return

    def _run():
        logger.info(
            "Picks scheduler started (interval=%ds = %.1fh)",
            REFRESH_INTERVAL,
            REFRESH_INTERVAL / 3600,
        )
        # Wait a bit on startup before first fetch
        _scheduler_stop.wait(60)

        while not _scheduler_stop.is_set():
            try:
                run_pipeline()
            except Exception:
                logger.exception("Scheduled picks refresh failed")
            _scheduler_stop.wait(REFRESH_INTERVAL)

        logger.info("Picks scheduler stopped")

    _scheduler_thread = threading.Thread(target=_run, daemon=True, name="picks-scheduler")
    _scheduler_thread.start()


def stop_background_scheduler():
    """Signal the background scheduler to stop."""
    _scheduler_stop.set()


# --- CLI entry point ---

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_pipeline()
    print(json.dumps(result, indent=2))
