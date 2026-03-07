"""
Persistence layer — saves and restores scan results / cache data
to the database so they survive server restarts on Render.

Uses the same SQLAlchemy engine as the rest of the app.  On PostgreSQL
(production) this means data lives in an external DB that persists
across deploys.  On SQLite (local dev) it persists across restarts too.

All functions are safe to call from any thread — they open and close
their own DB sessions.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Optional, cast

from src.database import SessionLocal
from src.models import ScanResult

logger = logging.getLogger(__name__)


# ── Low-level save / load ────────────────────────────────────


def save_scan(key: str, data) -> bool:
    """Upsert scan results into the scan_results table.

    Args:
        key:  Unique identifier, e.g. "value_scan", "trading_scan"
        data: Any JSON-serializable object (dict, list, etc.)

    Returns True on success.
    """
    db = SessionLocal()
    try:
        payload = json.dumps(data, default=str)
        existing = db.query(ScanResult).filter(ScanResult.key == key).first()
        if existing:
            existing.data = payload
            existing.updated_at = datetime.utcnow()
        else:
            db.add(ScanResult(key=key, data=payload, updated_at=datetime.utcnow()))
        db.commit()
        logger.debug("Persisted scan result: %s (%d bytes)", key, len(payload))
        return True
    except Exception:
        logger.exception("Failed to persist scan result: %s", key)
        db.rollback()
        return False
    finally:
        db.close()


def load_scan(key: str) -> Optional[dict[str, Any] | list[Any]]:
    """Load a previously saved scan result.  Returns None if not found."""
    db = SessionLocal()
    try:
        row = db.query(ScanResult).filter(ScanResult.key == key).first()
        if row:
            data: Any = json.loads(row.data)
            if isinstance(data, dict):
                logger.debug("Loaded scan result: %s (saved %s)", key, row.updated_at)
                return cast(dict[str, Any], data)
            if isinstance(data, list):
                logger.debug("Loaded scan result: %s (saved %s)", key, row.updated_at)
                return cast(list[Any], data)
            return None
        return None
    except Exception:
        logger.exception("Failed to load scan result: %s", key)
        return None
    finally:
        db.close()


def load_scan_with_age(key: str) -> tuple[Optional[dict[str, Any] | list[Any]], float]:
    """Load a scan result and return (data, age_in_seconds).

    Returns (None, 0) if not found.
    """
    db = SessionLocal()
    try:
        row = db.query(ScanResult).filter(ScanResult.key == key).first()
        if row:
            data: Any = json.loads(row.data)
            age = (datetime.utcnow() - row.updated_at).total_seconds() if row.updated_at else 0.0
            if isinstance(data, dict):
                return cast(dict[str, Any], data), age
            if isinstance(data, list):
                return cast(list[Any], data), age
            return None, 0
        return None, 0
    except Exception:
        logger.exception("Failed to load scan result: %s", key)
        return None, 0
    finally:
        db.close()


def load_scans_by_prefix(prefix: str) -> dict[str, Any]:
    """Load all scan results whose key starts with prefix.

    Returns {key: data} dict.
    """
    db = SessionLocal()
    try:
        rows = db.query(ScanResult).filter(ScanResult.key.like(f"{prefix}%")).all()
        result: dict[str, Any] = {}
        for row in rows:
            try:
                result[row.key] = json.loads(row.data)
            except Exception:
                pass
        logger.debug("Loaded %d scan results with prefix '%s'", len(result), prefix)
        return result
    except Exception:
        logger.exception("Failed to load scan results with prefix: %s", prefix)
        return {}
    finally:
        db.close()


def delete_scan(key: str) -> bool:
    """Delete a scan result by key."""
    db = SessionLocal()
    try:
        db.query(ScanResult).filter(ScanResult.key == key).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


# ── High-level: market_data cache snapshot ───────────────────

# Keys considered "important" enough to persist (survive restarts).
# We don't persist every cache entry — just the expensive/slow ones.
PERSIST_PREFIXES = (
    "info:",
    "advisor:",
    "news:",
    "company_dna:",
    "quote:",
    "live_quotes:",
    "sparklines:",
)


def load_home_snapshot() -> Optional[dict]:
    """Load the last persisted /api/market/home response from the DB.

    Returns the full {ticker, featured} dict, or None.
    Used as an instant fallback when the in-memory cache is cold.
    """
    result = load_scan("market_home_snapshot")
    return result if isinstance(result, dict) else None


def save_home_snapshot(data: dict) -> bool:
    """Persist the /api/market/home response to the DB for instant cold-start."""
    return save_scan("market_home_snapshot", data)


def save_market_cache_snapshot(cache: dict) -> bool:
    """Persist important entries from market_data._cache to the DB.

    Args:
        cache: The market_data._cache dict {key: (timestamp, data)}

    Only persists entries whose keys start with PERSIST_PREFIXES.
    Saves as a single JSON blob under key "market_cache_snapshot".
    """
    try:
        now = time.time()
        snapshot = {}
        for k, (ts, data) in cache.items():
            if any(k.startswith(p) for p in PERSIST_PREFIXES):
                # Only save entries that aren't too old (< 2 hours)
                if now - ts < 7200:
                    snapshot[k] = {"ts": ts, "data": data}

        if not snapshot:
            return True

        return save_scan("market_cache_snapshot", snapshot)
    except Exception:
        logger.exception("Failed to save market cache snapshot")
        return False


def restore_market_cache() -> dict[str, tuple[float, dict]]:
    """Restore market_data cache entries from the DB.

    Returns a dict in the same format as market_data._cache:
    {key: (timestamp, data)}

    Quote/sparkline entries get their timestamps bumped to *now* so they
    are treated as fresh cache hits immediately after a server restart.
    Without this, restored entries whose original ts is > 5 min old would
    be skipped by fetch_live_quotes() and the user would still wait for
    external API calls.
    """
    try:
        snapshot = load_scan("market_cache_snapshot")
        if not snapshot or not isinstance(snapshot, dict):
            return {}

        restored = {}
        now = time.time()
        # Prefixes whose entries should be stamped "now" so they survive
        # the short QUOTE_CACHE_TTL / CACHE_TTL checks on first access.
        REFRESH_PREFIXES = ("quote:", "live_quotes:", "sparklines:")
        for k, entry in snapshot.items():
            ts = entry.get("ts", 0)
            data = entry.get("data")
            # Only restore entries less than 2 hours old
            if data and now - ts < 7200:
                # Bump timestamp for volatile entries so they're usable
                if any(k.startswith(p) for p in REFRESH_PREFIXES):
                    restored[k] = (now, data)
                else:
                    restored[k] = (ts, data)

        logger.info("Restored %d market cache entries from DB", len(restored))
        return restored
    except Exception:
        logger.exception("Failed to restore market cache")
        return {}


# ── High-level: restore all caches on startup ────────────────


def restore_all_caches():
    """Called once at startup to pre-populate all in-memory caches
    from the database.  This makes the API serve data immediately
    instead of waiting 15-30 min for scans to complete.
    """
    logger.info("Restoring cached data from database...")

    # 1. Restore value scanner cache
    try:
        data = load_scan("value_scan")
        if data and isinstance(data, dict) and data.get("candidates"):
            from src.services.value_scanner import _scan_cache, _scan_lock

            with _scan_lock:
                _scan_cache["candidates"] = data.get("candidates", [])
                _scan_cache["rejected"] = data.get("rejected", [])
                _scan_cache["scanned"] = data.get("scanned", 0)
                _scan_cache["total"] = data.get("total", 0)
                _scan_cache["complete"] = True
                _scan_cache["updated_at"] = data.get("updated_at", time.time())
            logger.info("Restored value scanner: %d candidates", len(_scan_cache["candidates"]))
    except Exception:
        logger.exception("Failed to restore value scanner cache")

    # 2. Restore trading advisor cache
    try:
        data = load_scan("trading_scan")
        if data and isinstance(data, dict) and data.get("all_picks"):
            from src.services.trading_advisor import _scan_cache, _scan_lock

            with _scan_lock:
                _scan_cache["all_picks"] = data.get("all_picks", [])
                _scan_cache["packages"] = data.get("packages", {})
                _scan_cache["market_mood"] = data.get("market_mood", {})
                _scan_cache["scanned"] = data.get("scanned", 0)
                _scan_cache["total"] = data.get("total", 0)
                _scan_cache["complete"] = True
                _scan_cache["updated_at"] = data.get("updated_at", time.time())
            logger.info("Restored trading advisor: %d picks", len(_scan_cache["all_picks"]))
    except Exception:
        logger.exception("Failed to restore trading advisor cache")

    # 3. Restore picks tracker cache
    try:
        data = load_scan("picks_tracker")
        if data and isinstance(data, dict):
            from src.services.picks_tracker import _cache, _cache_lock

            with _cache_lock:
                for cache_key, val in data.items():
                    _cache[cache_key] = (time.time(), val)
            logger.info("Restored picks tracker: %d entries", len(data))
    except Exception:
        logger.exception("Failed to restore picks tracker cache")

    # 4. Restore market data cache
    try:
        restored = restore_market_cache()
        if restored:
            from src.services.market_data import _cache, _cache_lock

            with _cache_lock:
                _cache.update(restored)
            logger.info("Restored %d market data cache entries", len(restored))
    except Exception:
        logger.exception("Failed to restore market data cache")

    # 5. Restore ALL smart advisor scan + full analysis combos into market_data._cache
    try:
        from src.services.market_data import _cache, _cache_lock

        PERIODS = ["1y", "6m", "3m", "1m"]
        RISKS = ["balanced", "conservative", "aggressive"]
        DEFAULT_AMOUNT = 10000
        # Use a timestamp 15 minutes in the future so restored advisor data
        # survives the full CACHE_TTL (20 min) without expiring before the
        # scheduler has a chance to refresh it.  This gives effectively
        # 35 min of validity instead of 20.
        restore_ts = time.time() + 900  # now + 15 min

        # Restore scan results for all 4 periods
        scans_restored = 0
        for period in PERIODS:
            scan_data = load_scan(f"smart_advisor_scan:{period}")
            if scan_data and isinstance(scan_data, list) and len(scan_data) > 0:
                with _cache_lock:
                    _cache[f"advisor:scan:{period}"] = (restore_ts, scan_data)
                scans_restored += 1
        if scans_restored:
            logger.info("Restored %d smart advisor scan period keys", scans_restored)

        # If we only got 1y, replicate to other periods (scan is period-independent)
        if scans_restored == 1:
            scan_1y = load_scan("smart_advisor_scan:1y")
            if scan_1y and isinstance(scan_1y, list):
                with _cache_lock:
                    for period in PERIODS:
                        _cache[f"advisor:scan:{period}"] = (restore_ts, scan_1y)
                logger.info("Replicated 1y scan to all period keys")

        # Restore full analysis for ALL 12 risk x period combos
        analyses_restored = 0
        for period in PERIODS:
            for risk in RISKS:
                db_key = f"smart_advisor_full:{DEFAULT_AMOUNT}:{risk}:{period}"
                cache_key = f"advisor:full:{DEFAULT_AMOUNT}:{risk}:{period}"
                full_data = load_scan(db_key)
                if full_data and isinstance(full_data, dict) and full_data.get("rankings"):
                    with _cache_lock:
                        _cache[cache_key] = (restore_ts, full_data)
                    analyses_restored += 1
        if analyses_restored:
            logger.info("Restored %d smart advisor full analysis combos", analyses_restored)
    except Exception:
        logger.exception("Failed to restore smart advisor cache")

    logger.info("Cache restoration complete")
