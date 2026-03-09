"""
Trading Advisor -- Background Scanner with Strategy Packages.

Scans the full stock universe using technical analysis indicators,
scores each stock, groups winners into themed strategy packages
(Momentum, Swing, Oversold Bargains), and provides per-pick
action cards with entry/exit/stop-loss.

Uses background threading (like value_scanner.py) so results are
instantly available and progressively updated.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from src.services import data_provider as dp
from src.services import technical_analysis as ta
from src.services import pattern_detection as pd
from src.services import advanced_indicators as adv
from src.services.market_data import (
    fetch_batch,
    fetch_stock_info,
    ALL_UNIVERSE,
    format_market_cap,
    _LOW_MEMORY,
)

logger = logging.getLogger(__name__)

CANDLE_LOOKBACK_DAYS = 420
_MAX_WORKERS = 2 if _LOW_MEMORY else 4
SCAN_CACHE_TTL = 1800  # 30 min

# Benchmark candles for relative strength (cached per scan)
_benchmark_lock = threading.Lock()
_benchmark_closes: list[float] = []

_scan_lock = threading.Lock()

# "Live" cache — always holds the LAST COMPLETED scan results.
# Never wiped mid-scan; only replaced atomically when a new scan finishes.
_scan_cache: dict = {
    "all_picks": [],
    "packages": {},
    "market_mood": {"bullish": 0, "neutral": 0, "bearish": 0},
    "scanned": 0,
    "total": 0,
    "complete": False,
    "updated_at": 0,
}

# Progress of the CURRENTLY RUNNING scan (separate from live results).
_scan_progress: dict = {"scanned": 0, "total": 0, "complete": True}

_scan_running = False


# ---------------------------------------------------------------------------
# Single-stock analysis
# ---------------------------------------------------------------------------


def _analyze_stock(symbol: str, candles: dict, fund_info: dict) -> Optional[dict]:
    """Compute all indicators (classic + advanced) and build an action card."""
    closes = candles.get("c", [])
    if len(closes) < 50:
        return None

    highs = candles.get("h", closes)
    lows = candles.get("l", closes)
    volumes = candles.get("v", [0] * len(closes))
    timestamps = candles.get("t", [])

    # Classic indicators
    sma50 = ta.sma(closes, 50)
    sma200 = ta.sma(closes, 200)
    rsi_vals = ta.rsi(closes)
    macd_data = ta.macd(closes)
    boll = ta.bollinger_bands(closes)
    stoch = ta.stochastic(highs, lows, closes)
    atr_vals = ta.atr(highs, lows, closes)
    obv_vals = ta.obv(closes, volumes)

    # Advanced indicators
    adx_data = ta.adx(highs, lows, closes)
    rsi_div = ta.detect_divergence(closes, rsi_vals)
    macd_div = ta.detect_divergence(closes, macd_data["histogram"])
    vol_anom = ta.volume_anomaly(closes, volumes)
    zscore_vals = ta.zscore(closes)
    ichi = ta.ichimoku(highs, lows, closes)
    ichi_sig = ta.ichimoku_signal(closes, ichi)
    fib = ta.fibonacci_levels(closes)

    # Relative strength vs SPY
    rs_data = None
    with _benchmark_lock:
        if _benchmark_closes and len(_benchmark_closes) >= 22:
            bench = _benchmark_closes
            n = min(len(closes), len(bench))
            if n >= 22:
                rs_data = ta.relative_strength(closes[-n:], bench[-n:])

    # Advanced composite score
    comp = ta.composite_score(
        rsi_vals,
        macd_data,
        closes,
        sma50,
        sma200,
        boll["pct_b"],
        stoch,
        obv_vals,
        adx_data=adx_data,
        rsi_div=rsi_div,
        macd_div=macd_div,
        vol_anomaly=vol_anom,
        ichimoku_sig=ichi_sig,
        zscore_vals=zscore_vals,
        rs_data=rs_data,
    )

    current = closes[-1]
    last_atr = ta._last_valid(atr_vals)
    boll_lower = ta._last_valid(boll["lower"])
    boll_upper = ta._last_valid(boll["upper"])
    cur_rsi = ta._last_valid(rsi_vals)
    cur_stoch_k = ta._last_valid(stoch["k"])
    s50 = ta._last_valid(sma50)
    s200 = ta._last_valid(sma200)

    # Entry/target/stop using Fibonacci when available
    entry = current
    if fib.get("nearest_support") and current > fib["nearest_support"]:
        entry = round((current + fib["nearest_support"]) / 2, 2)
    elif boll_lower and current > boll_lower:
        entry = round((current + boll_lower) / 2, 2)

    if fib.get("nearest_resistance"):
        target = round(fib["nearest_resistance"], 2)
    elif boll_upper:
        target = round(boll_upper, 2)
    else:
        target = round(current * 1.08, 2)

    stop = round(entry - 2 * last_atr, 2) if last_atr else round(entry * 0.95, 2)
    if stop >= entry:
        stop = round(entry * 0.95, 2)
    rr = round((target - entry) / (entry - stop), 2) if entry > stop else 0

    macd_hist = macd_data["histogram"]
    recent_hist = [h for h in macd_hist[-5:] if h is not None]
    macd_bullish_cross = len(recent_hist) >= 2 and any(h <= 0 for h in recent_hist[:-1]) and recent_hist[-1] > 0

    avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0
    vol_above_avg = volumes[-1] > avg_vol_20 * 1.2 if avg_vol_20 > 0 else False

    boll_pct_b = ta._last_valid(boll["pct_b"])
    boll_bandwidth = None
    if boll_upper and boll_lower:
        mid = ta._last_valid(boll["middle"])
        if mid and mid > 0:
            boll_bandwidth = (boll_upper - boll_lower) / mid

    sparkline = closes[-30:] if len(closes) >= 30 else closes

    # Build signal text: classic + edge signals
    signals_text = [s["detail"] for s in comp["signals"] if s["score"] != 0]
    edge_text = [s["detail"] for s in comp.get("edge_signals", []) if s["score"] != 0]
    all_signals_text = edge_text + signals_text

    name = fund_info.get("name", symbol)
    sector = fund_info.get("sector", "N/A")

    return {
        "symbol": symbol,
        "name": name,
        "sector": sector,
        "price": current,
        "market_cap_fmt": format_market_cap(fund_info.get("market_cap", 0)),
        "score": comp["score"],
        "raw_score": comp["raw_score"],
        "verdict": comp["verdict"],
        "confidence": comp["confidence"],
        "signals": comp["signals"],
        "edge_signals": comp.get("edge_signals", []),
        "signals_text": all_signals_text,
        "entry": round(entry, 2),
        "target": round(target, 2),
        "stop_loss": round(stop, 2),
        "risk_reward": rr,
        "rsi": round(cur_rsi, 1) if cur_rsi else None,
        "stoch_k": round(cur_stoch_k, 1) if cur_stoch_k else None,
        "macd_bullish_cross": macd_bullish_cross,
        "macd_hist_positive": recent_hist[-1] > 0 if recent_hist else False,
        "above_sma50": current > s50 if s50 else False,
        "above_sma200": current > s200 if s200 else False,
        "golden_cross": s50 is not None and s200 is not None and s50 > s200,
        "vol_above_avg": vol_above_avg,
        "boll_pct_b": round(boll_pct_b, 3) if boll_pct_b is not None else None,
        "boll_squeeze": boll_bandwidth is not None and boll_bandwidth < 0.06,
        "has_divergence": comp.get("has_divergence", False),
        "has_institutional_signal": comp.get("has_institutional_signal", False),
        "vol_anomaly_score": vol_anom.get("anomaly_score", 0),
        "quiet_accumulation": vol_anom.get("quiet_accumulation", False),
        "rs_outperforming": rs_data.get("outperforming", False) if rs_data else False,
        "rs_1m": rs_data.get("rs_1m") if rs_data else None,
        "ichimoku_bullish": ichi_sig.get("signal", 0) > 0,
        "zscore": ta._last_valid(zscore_vals),
        "fib_support": fib.get("nearest_support"),
        "fib_resistance": fib.get("nearest_resistance"),
        "sparkline": sparkline,
        "beta": fund_info.get("beta"),
        "dividend_yield": fund_info.get("dividend_yield"),
    }


# ---------------------------------------------------------------------------
# Strategy package builders
# ---------------------------------------------------------------------------


def _build_momentum_package(picks: list[dict]) -> dict:
    """Short-term momentum plays (days to weeks)."""
    pool = [
        p
        for p in picks
        if p["macd_bullish_cross"] and p["above_sma50"] and (p["rsi"] is not None and 45 <= p["rsi"] <= 75)
    ]
    if len(pool) < 3:
        pool = [
            p
            for p in picks
            if p["macd_hist_positive"] and p["above_sma50"] and (p["rsi"] is not None and p["rsi"] < 75)
        ]
    pool.sort(key=lambda x: x["score"], reverse=True)
    return {
        "id": "momentum",
        "name": "Momentum Plays",
        "subtitle": "Short-term opportunities riding upward trends",
        "timeframe": "Days to Weeks",
        "risk_level": "High",
        "picks": pool[:8],
    }


def _build_swing_package(picks: list[dict]) -> dict:
    """Medium-term swing trades (weeks to months)."""
    pool = [
        p
        for p in picks
        if p["golden_cross"] and p["macd_hist_positive"] and (p["rsi"] is not None and 35 <= p["rsi"] <= 65)
    ]
    if len(pool) < 3:
        pool = [p for p in picks if p["above_sma50"] and (p["rsi"] is not None and 30 <= p["rsi"] <= 65)]
    pool.sort(key=lambda x: x["risk_reward"], reverse=True)
    return {
        "id": "swing",
        "name": "Swing Trades",
        "subtitle": "Medium-term positions at technical inflection points",
        "timeframe": "Weeks to Months",
        "risk_level": "Medium",
        "picks": pool[:8],
    }


def _build_oversold_package(picks: list[dict]) -> dict:
    """Oversold bargains for patient buyers."""
    pool = [
        p
        for p in picks
        if p["rsi"] is not None and p["rsi"] < 40 and (p["boll_pct_b"] is not None and p["boll_pct_b"] < 0.3)
    ]
    if len(pool) < 3:
        pool = [p for p in picks if p["rsi"] is not None and p["rsi"] < 45]
    pool.sort(key=lambda x: x["rsi"] if x["rsi"] is not None else 100)
    return {
        "id": "oversold",
        "name": "Oversold Bargains",
        "subtitle": "Potential entry points for patient buyers — prices near support",
        "timeframe": "Weeks to Months",
        "risk_level": "Medium-Low",
        "picks": pool[:8],
    }


def _build_hidden_gems_package(picks: list[dict]) -> dict:
    """
    Hidden Gems: stocks showing divergences, quiet accumulation,
    or relative strength that most traders miss.
    """
    pool = [p for p in picks if (p.get("has_divergence") or p.get("quiet_accumulation") or p.get("rs_outperforming"))]
    if not pool:
        pool = [p for p in picks if p.get("has_institutional_signal")]
    pool.sort(
        key=lambda x: (
            (2 if x.get("has_divergence") else 0)
            + (1.5 if x.get("quiet_accumulation") else 0)
            + (1 if x.get("rs_outperforming") else 0)
            + x["score"] / 100
        ),
        reverse=True,
    )
    return {
        "id": "hidden",
        "name": "Hidden Gems",
        "subtitle": "Non-obvious opportunities: divergences, quiet accumulation, relative strength",
        "timeframe": "Days to Months",
        "risk_level": "Medium",
        "picks": pool[:8],
    }


def _build_institutional_package(picks: list[dict]) -> dict:
    """
    Institutional Accumulation: stocks with volume anomalies
    suggesting smart money is positioning.
    """
    pool = [
        p
        for p in picks
        if (p.get("has_institutional_signal") or p.get("vol_anomaly_score", 0) > 30 or p.get("quiet_accumulation"))
        and (p["rsi"] is not None and p["rsi"] < 70)
    ]
    if len(pool) < 3:
        pool = [p for p in picks if p.get("vol_above_avg")]
    pool.sort(key=lambda x: x.get("vol_anomaly_score", 0), reverse=True)
    return {
        "id": "institutional",
        "name": "Smart Money Flow",
        "subtitle": "Unusual volume patterns suggesting institutional positioning",
        "timeframe": "Weeks to Months",
        "risk_level": "Medium",
        "picks": pool[:8],
    }


# ---------------------------------------------------------------------------
# Background scanner
# ---------------------------------------------------------------------------


def _fetch_benchmark():
    """Fetch SPY daily closes for relative strength comparisons."""
    global _benchmark_closes
    to_ts = int(time.time())
    from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400
    try:
        candles = dp.get_candles("SPY", "D", from_ts, to_ts)
        if candles and candles.get("c") and len(candles["c"]) > 50:
            with _benchmark_lock:
                _benchmark_closes = candles["c"]
            logger.info("Trading advisor: SPY benchmark loaded (%d days)", len(candles["c"]))
    except Exception:
        logger.warning("Trading advisor: failed to fetch SPY benchmark")


def _run_background_scan():
    """Scan universe in batches.  Build results into local variables and only
    swap them into the live _scan_cache atomically when the scan completes.
    The old results stay visible the entire time a new scan is running."""
    global _scan_running

    try:
        _fetch_benchmark()

        # Use whatever is already cached, don't block on fetching fundamentals
        fundamentals = fetch_batch(ALL_UNIVERSE, cached_only=True)
        fund_map = {d["symbol"]: d for d in fundamentals if d.get("price", 0) > 0}

        # For symbols not yet cached, create minimal fund_info stubs so we can
        # still scan them — candles are what matter for technical analysis
        from src.services.market_data import WARM_PRIORITY

        for sym in ALL_UNIVERSE:
            if sym not in fund_map:
                fund_map[sym] = {"symbol": sym, "name": sym, "sector": "N/A", "price": 1, "market_cap": 0}

        # Prioritize: scan popular stocks first for faster initial picks
        priority_set = set(WARM_PRIORITY)
        priority_syms = [s for s in fund_map if s in priority_set]
        rest_syms = [s for s in fund_map if s not in priority_set]
        symbols = priority_syms + rest_syms
        total = len(symbols)

        # Update progress tracker (separate from live results)
        with _scan_lock:
            _scan_progress["total"] = total
            _scan_progress["scanned"] = 0
            _scan_progress["complete"] = False

        if not symbols:
            with _scan_lock:
                _scan_progress["complete"] = True
            return

        to_ts = int(time.time())
        from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400
        all_picks: list[dict] = []

        # Local copies — only promoted to _scan_cache at the end
        local_packages: dict = {}
        local_mood: dict = {"bullish": 0, "neutral": 0, "bearish": 0}

        BATCH = 16
        batch_num = 0
        for batch_start in range(0, len(symbols), BATCH):
            batch_syms = symbols[batch_start : batch_start + BATCH]
            batch_num += 1

            def _fetch(sym):
                try:
                    return sym, dp.get_candles(sym, "D", from_ts, to_ts)
                except Exception:
                    return sym, None

            with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
                futures = {pool.submit(_fetch, s): s for s in batch_syms}
                for fut in as_completed(futures):
                    sym, candles = fut.result()
                    if candles and candles.get("c"):
                        # Enrich fund_info from cache if it was a stub
                        fi = fund_map.get(sym, {})
                        if fi.get("name") == sym:
                            from src.services.market_data import _get_cached

                            cached = _get_cached(f"info:{sym}")
                            if cached:
                                fi = cached
                        pick = _analyze_stock(sym, candles, fi)
                        if pick:
                            all_picks.append(pick)

            all_picks.sort(key=lambda x: x["score"], reverse=True)

            # Cap stored picks to top 50 — API only shows 30, save memory
            all_picks = all_picks[:50]

            # Rebuild packages on 1st batch (fast initial results), every 3rd batch, and last batch
            is_final = batch_start + BATCH >= len(symbols)
            should_publish = batch_num <= 2 or batch_num % 3 == 0 or is_final
            if should_publish:
                local_packages = {
                    "hidden": _build_hidden_gems_package(all_picks),
                    "institutional": _build_institutional_package(all_picks),
                    "momentum": _build_momentum_package(all_picks),
                    "swing": _build_swing_package(all_picks),
                    "oversold": _build_oversold_package(all_picks),
                }

            bull = sum(1 for p in all_picks if p["verdict"] in ("Strong Buy", "Buy"))
            bear = sum(1 for p in all_picks if p["verdict"] in ("Sell", "Strong Sell"))
            neut = len(all_picks) - bull - bear
            total_so_far = len(all_picks) or 1
            local_mood = {
                "bullish": round(bull / total_so_far * 100),
                "neutral": round(neut / total_so_far * 100),
                "bearish": round(bear / total_so_far * 100),
            }

            scanned_so_far = min(batch_start + BATCH, total)

            # ── Publish intermediate results to live cache so users see
            #    data immediately instead of waiting for the full scan.
            #    On Render free tier, the instance may be killed before
            #    the scan completes, so we also persist to DB periodically.
            with _scan_lock:
                _scan_progress["scanned"] = scanned_so_far

            if should_publish and all_picks:
                with _scan_lock:
                    _scan_cache["all_picks"] = list(all_picks)
                    _scan_cache["packages"] = local_packages
                    _scan_cache["market_mood"] = local_mood
                    _scan_cache["scanned"] = scanned_so_far
                    _scan_cache["total"] = total
                    _scan_cache["complete"] = is_final
                    _scan_cache["updated_at"] = time.time()

                # Persist intermediate results to DB every few batches
                if batch_num <= 2 or batch_num % 6 == 0 or is_final:
                    try:
                        from src.services.persistence import save_scan

                        with _scan_lock:
                            snapshot = dict(_scan_cache)
                        save_scan("trading_scan", snapshot)
                    except Exception:
                        logger.warning("Trading advisor: failed to persist intermediate results")

        # ── Scan complete: finalize ──
        with _scan_lock:
            _scan_cache["complete"] = True
            _scan_cache["updated_at"] = time.time()
            _scan_progress["scanned"] = total
            _scan_progress["complete"] = True

        logger.info(
            "Trading advisor scan complete: %d picks, hidden=%d inst=%d momentum=%d swing=%d oversold=%d",
            len(all_picks),
            len(local_packages.get("hidden", {}).get("picks", [])),
            len(local_packages.get("institutional", {}).get("picks", [])),
            len(local_packages.get("momentum", {}).get("picks", [])),
            len(local_packages.get("swing", {}).get("picks", [])),
            len(local_packages.get("oversold", {}).get("picks", [])),
        )

        # Persist results to DB so they survive restarts
        try:
            from src.services.persistence import save_scan

            with _scan_lock:
                snapshot = dict(_scan_cache)
            save_scan("trading_scan", snapshot)
        except Exception:
            logger.exception("Trading advisor: failed to persist results")
    except Exception:
        logger.exception("Trading advisor background scan failed")
        with _scan_lock:
            _scan_progress["complete"] = True
            # Do NOT touch _scan_cache — keep the old good results
    finally:
        _scan_running = False


def run_full_scan():
    """Entry point called by the background scheduler.

    Runs a complete scan synchronously (blocking).  Safe to call from
    any thread — guards against concurrent scans internally.

    Skips the scan if the cache already contains complete, fresh data
    (e.g. restored from the database after a deploy).  This avoids
    wiping persisted results and forcing users to wait for a re-scan.
    """
    global _scan_running
    with _scan_lock:
        if _scan_running:
            logger.info("Trading advisor: scan already in progress, skipping")
            return
        # Skip if cache has complete results that are younger than 2x TTL
        if (
            _scan_cache["complete"]
            and _scan_cache["all_picks"]
            and _scan_cache["updated_at"]
            and (time.time() - _scan_cache["updated_at"]) < SCAN_CACHE_TTL * 2
        ):
            logger.info(
                "Trading advisor: cache is fresh (%ds old, TTL=%ds), skipping scan",
                int(time.time() - _scan_cache["updated_at"]),
                SCAN_CACHE_TTL,
            )
            return
        _scan_running = True
        _scan_progress["complete"] = False
        _scan_progress["scanned"] = 0

    _run_background_scan()


def _ensure_scan_running():
    """Safety-net fallback: start a background scan if cache is empty.

    Only used on first request before the scheduler has run.  Once the
    scheduler is producing results this is essentially a no-op.
    """
    global _scan_running
    with _scan_lock:
        if _scan_running:
            return
        # If we already have results, let the scheduler handle refreshes
        if _scan_cache["all_picks"]:
            return
        # No results at all — kick off a scan so the user isn't stuck
        _scan_running = True
        _scan_progress["complete"] = False
        _scan_progress["scanned"] = 0

    t = threading.Thread(target=_run_background_scan, daemon=True)
    t.start()


# Kept for backward compat but no longer needed — scheduler handles repeats
def start_trading_advisor():
    """Legacy entry point.  Now a no-op; use background_scheduler instead."""
    logger.info("start_trading_advisor() called — scanning is handled by background_scheduler")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_dashboard() -> dict:
    """Return current scan results for the dashboard.

    Pure read — never triggers a scan.  The background scheduler is
    responsible for keeping results fresh.  If the server just started
    and the scheduler hasn't run yet, _ensure_scan_running() kicks off
    one scan as a safety net.
    """
    _ensure_scan_running()  # safety-net: only fires when cache is empty

    with _scan_lock:
        # If we have completed results, show them with complete=True.
        # If a rescan is running, overlay the rescan progress so users
        # still see the progress bar, but the picks stay stable.
        have_results = bool(_scan_cache["all_picks"])
        rescan_running = not _scan_progress["complete"]

        if have_results and rescan_running:
            # Show old results + new scan progress
            progress = {
                "scanned": _scan_progress["scanned"],
                "total": _scan_progress["total"],
                "complete": False,
            }
        elif have_results:
            # Completed scan — show final numbers
            progress = {
                "scanned": _scan_cache["scanned"],
                "total": _scan_cache["total"],
                "complete": True,
            }
        else:
            # Very first scan still running, no old data yet
            progress = {
                "scanned": _scan_progress["scanned"],
                "total": _scan_progress["total"],
                "complete": False,
            }

        return {
            "packages": _scan_cache["packages"],
            "all_picks": _scan_cache["all_picks"][:30],
            "market_mood": _scan_cache["market_mood"],
            "progress": progress,
            "updated_at": _scan_cache.get("updated_at", 0),
        }


def get_single_analysis(symbol: str) -> Optional[dict]:
    """Deep analysis for a single stock with full indicator arrays + patterns."""
    to_ts = int(time.time())
    from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400

    candles = dp.get_candles(symbol, "D", from_ts, to_ts)
    if not candles or not candles.get("c") or len(candles["c"]) < 50:
        return None

    closes = candles["c"]
    highs = candles.get("h", closes)
    lows = candles.get("l", closes)
    opens = candles.get("o", closes)
    volumes = candles.get("v", [0] * len(closes))
    timestamps = candles.get("t", [])
    dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in timestamps]

    info = fetch_stock_info(symbol) or {}

    # ── Classic indicators ────────────────────────────
    sma50 = ta.sma(closes, 50)
    sma200 = ta.sma(closes, 200)
    ema12 = ta.ema(closes, 12)
    ema26 = ta.ema(closes, 26)
    rsi_vals = ta.rsi(closes)
    macd_data = ta.macd(closes)
    boll = ta.bollinger_bands(closes)
    stoch = ta.stochastic(highs, lows, closes)
    atr_vals = ta.atr(highs, lows, closes)
    obv_vals = ta.obv(closes, volumes)

    # ── Existing advanced indicators ──────────────────
    adx_data = ta.adx(highs, lows, closes)
    rsi_div = ta.detect_divergence(closes, rsi_vals)
    macd_div = ta.detect_divergence(closes, macd_data["histogram"])
    vol_anom = ta.volume_anomaly(closes, volumes)
    zscore_vals = ta.zscore(closes)
    ichi = ta.ichimoku(highs, lows, closes)
    ichi_sig = ta.ichimoku_signal(closes, ichi)
    fib = ta.fibonacci_levels(closes)
    cup_handle = ta.cup_and_handle(closes)

    rs_data = None
    with _benchmark_lock:
        if _benchmark_closes and len(_benchmark_closes) >= 22:
            bench = _benchmark_closes
            n = min(len(closes), len(bench))
            if n >= 22:
                rs_data = ta.relative_strength(closes[-n:], bench[-n:])

    # ── NEW: Pattern Detection ────────────────────────
    all_patterns = pd.detect_all_patterns(opens, highs, lows, closes, volumes)

    # ── NEW: Advanced Indicators ──────────────────────
    adv_data = adv.compute_all_advanced(opens, highs, lows, closes, volumes)

    # ── Composite score (original + new pattern/indicator boosts) ──
    comp = ta.composite_score(
        rsi_vals,
        macd_data,
        closes,
        sma50,
        sma200,
        boll["pct_b"],
        stoch,
        obv_vals,
        adx_data=adx_data,
        rsi_div=rsi_div,
        macd_div=macd_div,
        vol_anomaly=vol_anom,
        ichimoku_sig=ichi_sig,
        zscore_vals=zscore_vals,
        rs_data=rs_data,
    )

    # Merge pattern and advanced signals into edge signals
    merged_edge = list(comp.get("edge_signals", []))

    # Add pattern score as edge signal
    ps = all_patterns["pattern_score"]
    if abs(ps) > 0.2:
        merged_edge.append(
            {
                "name": "Chart Patterns",
                "score": ps,
                "detail": all_patterns["pattern_summary"],
                "direction": "bullish" if ps > 0 else "bearish",
            }
        )

    # Add advanced indicator signals
    for sig in adv_data.get("advanced_signals", []):
        merged_edge.append(sig)

    # Adjust raw score with new signals
    pattern_boost = ps * 0.08 + adv_data.get("advanced_score", 0) * 0.07
    adjusted_raw = comp["raw_score"] + pattern_boost
    adjusted_norm = round((adjusted_raw + 2) / 4 * 100)
    adjusted_norm = max(0, min(100, adjusted_norm))

    if adjusted_raw >= 1.2:
        verdict = "Strong Buy"
    elif adjusted_raw >= 0.5:
        verdict = "Buy"
    elif adjusted_raw > -0.5:
        verdict = "Neutral"
    elif adjusted_raw > -1.2:
        verdict = "Sell"
    else:
        verdict = "Strong Sell"

    # Recalculate confidence with all signals
    all_scores = [float(s["score"]) for s in comp["signals"]]
    all_scores += [float(e["score"]) for e in merged_edge]
    bullish_ct = sum(1 for s in all_scores if s > 0)
    total_ct = len(all_scores) or 1
    confidence = round(bullish_ct / total_ct * 100)

    current = closes[-1]
    last_atr = ta._last_valid(atr_vals)
    boll_lower = ta._last_valid(boll["lower"])
    boll_upper = ta._last_valid(boll["upper"])

    entry = current
    if fib.get("nearest_support") and current > fib["nearest_support"]:
        entry = round((current + fib["nearest_support"]) / 2, 2)
    elif boll_lower and current > boll_lower:
        entry = round((current + boll_lower) / 2, 2)

    if fib.get("nearest_resistance"):
        target = round(fib["nearest_resistance"], 2)
    elif boll_upper:
        target = round(boll_upper, 2)
    else:
        target = round(current * 1.08, 2)

    stop = round(entry - 2 * last_atr, 2) if last_atr else round(entry * 0.95, 2)
    if stop >= entry:
        stop = round(entry * 0.95, 2)
    rr = round((target - entry) / (entry - stop), 2) if entry > stop else 0

    # Build reasoning from all signals
    classic_parts = [s["detail"] for s in comp["signals"] if s["score"] != 0]
    edge_parts = [s["detail"] for s in merged_edge if s["score"] != 0]
    all_parts = edge_parts + classic_parts
    reasoning = ". ".join(all_parts[:8]) + "." if all_parts else "Insufficient data."

    # ── Build decision breakdown for visualization ────
    decision_breakdown: list[dict] = []
    weights = {"MACD": 0.22, "RSI": 0.18, "SMA": 0.18, "Bollinger": 0.14, "Stochastic": 0.10, "Volume": 0.08}
    for sig in comp["signals"]:
        w = weights.get(sig["name"], 0.1)
        decision_breakdown.append(
            {
                "name": sig["name"],
                "category": "classic",
                "raw_score": sig["score"],
                "weight": w,
                "weighted_score": round(float(sig["score"]) * w, 4),
                "direction": sig["direction"],
                "detail": sig["detail"],
            }
        )
    for sig in merged_edge:
        decision_breakdown.append(
            {
                "name": sig["name"],
                "category": "advanced",
                "raw_score": sig["score"],
                "weight": 0.10,
                "weighted_score": round(float(sig["score"]) * 0.10, 4),
                "direction": sig["direction"],
                "detail": sig["detail"],
            }
        )

    return {
        "symbol": symbol,
        "name": info.get("name", symbol),
        "sector": info.get("sector", "N/A"),
        "dates": dates,
        "price": {"close": closes, "high": highs, "low": lows, "open": opens, "volume": volumes},
        "indicators": {
            "sma_50": sma50,
            "sma_200": sma200,
            "ema_12": ema12,
            "ema_26": ema26,
            "rsi": rsi_vals,
            "macd": macd_data,
            "bollinger": boll,
            "stochastic": stoch,
            "obv": obv_vals,
            "atr": atr_vals,
            "ichimoku": ichi,
            "adx": adx_data,
            "zscore": zscore_vals,
            # New indicators
            "vwap": adv_data.get("vwap"),
            "keltner": adv_data.get("keltner"),
            "parabolic_sar": adv_data.get("parabolic_sar"),
            "williams_r": adv_data.get("williams_r"),
            "cmf": adv_data.get("cmf"),
            "donchian": adv_data.get("donchian"),
            "aroon": adv_data.get("aroon"),
            "cci": adv_data.get("cci"),
            "heikin_ashi": adv_data.get("heikin_ashi"),
            "force_index": adv_data.get("force_index"),
            "linear_regression": adv_data.get("linear_regression"),
            "momentum": adv_data.get("momentum"),
            "roc": adv_data.get("roc"),
        },
        "action": {
            "verdict": verdict,
            "score": adjusted_norm,
            "confidence": confidence,
            "entry": round(entry, 2),
            "target": round(target, 2),
            "stop_loss": round(stop, 2),
            "risk_reward": rr,
            "timeframe": "Short-term" if adjusted_raw > 1 else "Medium-term",
            "reasoning": reasoning,
            "signals": comp["signals"],
            "edge_signals": merged_edge,
        },
        "decision_breakdown": decision_breakdown,
        "patterns": {
            "chart_patterns": all_patterns["chart_patterns"],
            "candlestick_patterns": all_patterns["candlestick_patterns"],
            "gaps": all_patterns["gaps"],
            "pattern_score": all_patterns["pattern_score"],
            "pattern_summary": all_patterns["pattern_summary"],
        },
        "ttm_squeeze": {
            "squeeze_on": adv_data["ttm_squeeze"]["current_squeeze"],
            "squeeze_fired": adv_data["ttm_squeeze"]["squeeze_fired"],
            "detail": adv_data["ttm_squeeze"]["detail"],
        },
        "fibonacci": fib,
        "cup_and_handle": cup_handle,
        "volume_analysis": vol_anom,
        "relative_strength": rs_data,
    }
