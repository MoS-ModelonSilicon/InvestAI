"""
Background Scheduler — single daemon thread running ALL periodic scans.

Decouples scanning from user requests: scans run on fixed server-side
intervals whether or not anyone is visiting the site.  The API endpoints
become pure reads (fast, no side-effects).

Usage (in main.py startup):
    from src.services.background_scheduler import start_background_scheduler
    start_background_scheduler()
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)

_stop_event = threading.Event()

# ── Intervals (seconds) ──────────────────────────────────────
VALUE_SCANNER_INTERVAL = 300    # 5 min
TRADING_ADVISOR_INTERVAL = 1800  # 30 min


# ── Individual scan runners ──────────────────────────────────
def _run_value_scan() -> bool:
    """Run the value scanner's full scan.  Returns True on success."""
    try:
        from src.services.value_scanner import run_full_scan
        logger.info("Scheduler: starting value scan")
        run_full_scan()
        logger.info("Scheduler: value scan complete")
        return True
    except Exception:
        logger.exception("Scheduler: value scan failed")
        return False


def _run_trading_scan() -> bool:
    """Run the trading advisor's full scan.  Returns True on success."""
    try:
        from src.services.trading_advisor import run_full_scan
        logger.info("Scheduler: starting trading advisor scan")
        run_full_scan()
        logger.info("Scheduler: trading advisor scan complete")
        return True
    except Exception:
        logger.exception("Scheduler: trading advisor scan failed")
        return False


# ── Main loop ────────────────────────────────────────────────
def _scheduler_loop():
    """Blocking loop run inside a daemon thread."""
    from src.services.market_data import _warm_done

    logger.info("Background scheduler: waiting for cache warmer...")
    _warm_done.wait(timeout=120)
    if _warm_done.is_set():
        logger.info("Background scheduler: cache warm — starting scan schedule")
    else:
        logger.info("Background scheduler: timed out waiting for cache warm, starting anyway")

    # Stagger initial scans — value scanner first (shorter / lighter)
    _run_value_scan()
    if _stop_event.wait(timeout=120):  # 2 min gap before heavier scan
        return
    _run_trading_scan()

    last_value = time.time()
    last_trading = time.time()

    while not _stop_event.is_set():
        now = time.time()

        if now - last_value >= VALUE_SCANNER_INTERVAL:
            _run_value_scan()
            last_value = time.time()

        if now - last_trading >= TRADING_ADVISOR_INTERVAL:
            _run_trading_scan()
            last_trading = time.time()

        # Sleep in small increments so stop_event is responsive
        _stop_event.wait(timeout=30)


# ── Public API ───────────────────────────────────────────────
def start_background_scheduler():
    """Start the background scheduler daemon thread.  Call once at startup."""
    _stop_event.clear()
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="bg-scheduler")
    t.start()
    logger.info("Background scheduler thread started")


def stop_background_scheduler():
    """Signal the scheduler to stop.  Used in tests or graceful shutdown."""
    _stop_event.set()
