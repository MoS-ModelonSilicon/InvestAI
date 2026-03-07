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
MARKET_DATA_INTERVAL = 120       # 2 min  — lightweight (quotes + sparklines)
NEWS_INTERVAL = 900              # 15 min — 8 Finnhub calls
SMART_ADVISOR_INTERVAL = 900     # 15 min — heavy scan (40-80 candles)
CACHE_SNAPSHOT_INTERVAL = 600    # 10 min — persist market cache to DB


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


def _run_market_data_refresh() -> bool:
    """Refresh live quotes + sparklines for homepage symbols."""
    try:
        from src.services.market_data import refresh_active_symbols
        refresh_active_symbols()
        return True
    except Exception:
        logger.exception("Scheduler: market data refresh failed")
        return False


def _run_news_refresh() -> bool:
    """Pre-fetch news for the default symbols."""
    try:
        from src.services.news import refresh_news_cache
        refresh_news_cache()
        return True
    except Exception:
        logger.exception("Scheduler: news refresh failed")
        return False


def _run_smart_advisor_scan() -> bool:
    """Pre-compute the smart advisor scan + full analysis for ALL combos.

    scan_and_score() results are identical regardless of period (same stocks,
    same candles, same scoring).  Period only affects the cache key.  So we
    scan ONCE and replicate the result across all 4 period cache keys.
    Then we build full analyses for every risk × period combo.

    Combinations: 3 risk profiles × 4 periods = 12 full analyses.
    """
    PERIODS = ["1y", "6m", "3m", "1m"]
    RISKS = ["balanced", "conservative", "aggressive"]
    DEFAULT_AMOUNT = 10000

    try:
        from src.services.smart_advisor import scan_and_score, run_full_analysis
        from src.services.market_data import _set_cache
        from src.services.persistence import save_scan

        # Phase 1: Scan ONCE (heavy — 40-80 candle fetches)
        # scan_and_score uses CANDLE_LOOKBACK_DAYS constant, not the period
        # param, so results are identical.  We scan "1y" then copy to all keys.
        logger.info("Scheduler: smart advisor scan (one scan for all periods)")
        rankings = scan_and_score("1y")
        count = len(rankings) if rankings else 0
        logger.info("Scheduler: smart advisor scan done (%d stocks)", count)

        if not rankings:
            logger.warning("Scheduler: scan returned no rankings — skipping warm-up")
            return False

        # Replicate scan results to other period cache keys
        for period in PERIODS[1:]:  # skip "1y" — already cached by scan_and_score
            cache_key = f"advisor:scan:{period}"
            _set_cache(cache_key, rankings)
            try:
                save_scan(f"smart_advisor_scan:{period}", rankings)
            except Exception:
                pass  # non-critical
        logger.info("Scheduler: replicated scan to %d period keys", len(PERIODS))

        # Phase 2: Pre-compute full analysis for every risk × period combo
        for period in PERIODS:
            for risk in RISKS:
                logger.info(
                    "Scheduler: pre-computing full analysis %s/%s/%s",
                    DEFAULT_AMOUNT, risk, period,
                )
                run_full_analysis(amount=DEFAULT_AMOUNT, risk=risk, period=period)

        logger.info(
            "Scheduler: smart advisor warm-up complete — 1 scan, %d analyses",
            len(PERIODS) * len(RISKS),
        )
        return True
    except Exception:
        logger.exception("Scheduler: smart advisor scan failed")
        return False


def _run_cache_snapshot() -> bool:
    """Persist important market_data cache entries to the database."""
    try:
        from src.services.market_data import _cache, _cache_lock
        from src.services.persistence import save_market_cache_snapshot
        with _cache_lock:
            snapshot = dict(_cache)
        save_market_cache_snapshot(snapshot)
        logger.info("Scheduler: cache snapshot saved (%d entries)", len(snapshot))
        return True
    except Exception:
        logger.exception("Scheduler: cache snapshot failed")
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

    # ── Initial staggered runs ──────────────────────────────
    # Lightest → heaviest, with small gaps to avoid API rate-limit spikes
    _run_market_data_refresh()                 # ~10 quote + 6 sparkline calls
    if _stop_event.wait(timeout=10):
        return
    _run_news_refresh()                        # 8 Finnhub calls
    if _stop_event.wait(timeout=30):
        return
    _run_value_scan()                          # value scanner
    if _stop_event.wait(timeout=60):
        return
    _run_trading_scan()                        # trading advisor
    if _stop_event.wait(timeout=60):
        return
    _run_smart_advisor_scan()                  # smart advisor (heaviest)

    last_value = time.time()
    last_trading = time.time()
    last_market = time.time()
    last_news = time.time()
    last_smart = time.time()
    last_snapshot = time.time()

    while not _stop_event.is_set():
        now = time.time()

        if now - last_market >= MARKET_DATA_INTERVAL:
            _run_market_data_refresh()
            last_market = time.time()

        if now - last_value >= VALUE_SCANNER_INTERVAL:
            _run_value_scan()
            last_value = time.time()

        if now - last_news >= NEWS_INTERVAL:
            _run_news_refresh()
            last_news = time.time()

        if now - last_smart >= SMART_ADVISOR_INTERVAL:
            _run_smart_advisor_scan()
            last_smart = time.time()

        if now - last_trading >= TRADING_ADVISOR_INTERVAL:
            _run_trading_scan()
            last_trading = time.time()

        if now - last_snapshot >= CACHE_SNAPSHOT_INTERVAL:
            _run_cache_snapshot()
            last_snapshot = time.time()

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
