"""
Picks Tracker: loads community trade alerts from the **database**, backtests them
against real price data, and computes win/loss statistics per pick and overall.

Picks are stored in the `picks` table (see models.Pick) so they survive
Render deploys and are available to every user immediately.
"""

import json
import logging
import math
import os
import threading
import time
from datetime import datetime
from typing import Any, Optional, cast

from src.services import data_provider as dp
from src.services.market_data import get_currency

logger = logging.getLogger(__name__)

# Legacy JSON path – kept only for fallback / one-time seed
_PICKS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "static", "data", "discord-picks.json")

_cache: dict[str, tuple[float, object]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 86400  # 24h — background job handles freshness

# Cache key for the pre-computed evaluated picks list
_EVAL_CACHE_KEY = "picks_evaluated_all"


def _sanitize(val):
    """Replace NaN / Infinity floats with None so JSON serialisation never fails."""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _sanitize_dict(d: dict) -> dict:
    """Recursively sanitize all float values in a dict."""
    out: dict = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            out[k] = [
                _sanitize_dict(i) if isinstance(i, dict) else _sanitize(i) for i in v
            ]
        else:
            out[k] = _sanitize(v)
    return out


def _get_cached(key: str):
    with _cache_lock:
        if key in _cache:
            ts, val = _cache[key]
            if time.time() - ts < CACHE_TTL:
                return val
    return None


def _set_cache(key: str, val):
    with _cache_lock:
        _cache[key] = (time.time(), val)


def load_picks(source_filter: Optional[str] = None) -> list[dict]:
    """Load picks from the database. Falls back to JSON if DB is empty."""
    try:
        from src.services.scrapers.pipeline import _load_picks_from_db

        picks = _load_picks_from_db(source_filter=source_filter)
        if picks:
            return picks
    except Exception:
        logger.warning("Failed to load picks from database — falling back to JSON")

    # Fallback: read legacy JSON file
    path = os.path.normpath(_PICKS_FILE)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        result = cast(list[dict[str, Any]], data) if isinstance(data, list) else []
    if source_filter:
        result = [p for p in result if (p.get("source") or "").lower().startswith(source_filter.lower())]
    return result


def _parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")


def _evaluate_pick(pick: dict) -> dict:
    """Fetch price data after the call date and determine if targets/stops were hit."""
    symbol = pick["symbol"]
    entry = pick.get("entry")
    targets = pick.get("targets", [])
    stop = pick.get("stop")
    call_date = pick.get("date")

    result = {
        **pick,
        "status": "unknown",
        "current_price": None,
        "high_after": None,
        "low_after": None,
        "targets_hit": 0,
        "stopped_out": False,
        "best_gain_pct": None,
        "worst_loss_pct": None,
        "pnl_pct": None,
        "days_held": None,
        "risk_reward": None,
        "speed_score": None,
        "currency": get_currency(symbol),
    }

    if not entry or not call_date:
        result["status"] = "no_entry"
        return result

    # Compute Risk/Reward ratio from entry/target/stop
    first_target = targets[0] if targets else None
    if first_target and stop and entry and entry != stop:
        reward = abs(first_target - entry)
        risk = abs(entry - stop)
        result["risk_reward"] = round(reward / risk, 1) if risk > 0 else None

    try:
        call_dt = _parse_date(call_date)
        from_ts = int(call_dt.timestamp())
        to_ts = int(datetime.now().timestamp())

        candles = dp.get_candles(symbol, "D", from_ts, to_ts)
        if not candles or candles.get("s") == "no_data":
            result["status"] = "no_data"
            return result

        highs = candles.get("h", [])
        lows = candles.get("l", [])
        closes = candles.get("c", [])
        timestamps = candles.get("t", [])

        if not closes:
            result["status"] = "no_data"
            return result

        result["current_price"] = closes[-1] if closes else None
        result["high_after"] = max(highs) if highs else None
        result["low_after"] = min(lows) if lows else None
        result["days_held"] = len(closes)

        best_gain = ((max(highs) - entry) / entry * 100) if highs else 0
        worst_loss = ((min(lows) - entry) / entry * 100) if lows else 0
        result["best_gain_pct"] = round(best_gain, 1)
        result["worst_loss_pct"] = round(worst_loss, 1)

        targets_hit = sum(1 for t in targets if highs and max(highs) >= t)
        result["targets_hit"] = targets_hit

        stop_hit_first = False
        target_hit_first = False
        first_target_local = targets[0] if targets else None
        first_target_day = None

        for i, _ts_val in enumerate(timestamps):
            h = highs[i]
            l = lows[i]
            if stop and l <= stop and not target_hit_first:
                stop_hit_first = True
                break
            if first_target_local and h >= first_target_local:
                target_hit_first = True
                first_target_day = i + 1
                break

        result["stopped_out"] = stop_hit_first

        # Speed score: how many days to hit first target (lower = faster)
        if first_target_day is not None:
            result["speed_score"] = first_target_day

        if stop_hit_first:
            result["status"] = "stopped"
            result["pnl_pct"] = round((stop - entry) / entry * 100, 1) if stop else None
        elif targets_hit > 0:
            result["status"] = "winner"
            hit_target = targets[min(targets_hit - 1, len(targets) - 1)]
            result["pnl_pct"] = round((hit_target - entry) / entry * 100, 1)
        else:
            current = closes[-1] if closes else entry
            pnl = (current - entry) / entry * 100
            result["pnl_pct"] = round(pnl, 1)
            result["status"] = "open" if abs(pnl) < 50 else ("winner" if pnl > 0 else "loser")

    except Exception as e:
        logger.warning("Failed to evaluate pick %s: %s", symbol, e)
        result["status"] = "error"

    return _sanitize_dict(result)


def _compute_stats(evaluated: list[dict]) -> dict:
    """Compute summary statistics from a list of already-evaluated picks."""
    with_entry = [p for p in evaluated if p.get("entry") and p.get("status") != "no_entry"]

    winners = [p for p in with_entry if p["status"] == "winner"]
    stopped = [p for p in with_entry if p["status"] == "stopped"]
    open_picks = [p for p in with_entry if p["status"] == "open"]

    total_with_data = len([p for p in with_entry if p["status"] != "no_data"])
    win_rate = (len(winners) / total_with_data * 100) if total_with_data > 0 else 0

    avg_win = 0.0
    if winners:
        avg_win = sum(p["pnl_pct"] for p in winners if p["pnl_pct"]) / len(winners)

    avg_loss = 0.0
    if stopped:
        avg_loss = sum(p["pnl_pct"] for p in stopped if p["pnl_pct"]) / len(stopped)

    all_pnl = [p["pnl_pct"] for p in with_entry if p["pnl_pct"] is not None]
    avg_pnl = sum(all_pnl) / len(all_pnl) if all_pnl else 0
    best_pick = max(with_entry, key=lambda p: p.get("best_gain_pct") or 0) if with_entry else None
    worst_pick = min(with_entry, key=lambda p: p.get("worst_loss_pct") or 0) if with_entry else None

    all_rr = [p["risk_reward"] for p in with_entry if p.get("risk_reward") is not None]
    avg_rr = round(sum(all_rr) / len(all_rr), 1) if all_rr else None
    total_pnl = round(sum(all_pnl), 1) if all_pnl else 0
    all_days = [p["days_held"] for p in with_entry if p.get("days_held") is not None]
    avg_days = round(sum(all_days) / len(all_days)) if all_days else None
    speed_scores = [p["speed_score"] for p in winners if p.get("speed_score") is not None]
    avg_speed = round(sum(speed_scores) / len(speed_scores), 1) if speed_scores else None

    gross_wins = sum(p["pnl_pct"] for p in with_entry if (p.get("pnl_pct") or 0) > 0)
    gross_losses = abs(sum(p["pnl_pct"] for p in with_entry if (p.get("pnl_pct") or 0) < 0))
    profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else None

    return _sanitize_dict(
        {
            "picks": evaluated,
            "stats": {
                "total_picks": len(evaluated),
                "with_entry": len(with_entry),
                "winners": len(winners),
                "stopped": len(stopped),
                "open": len(open_picks),
                "win_rate": round(win_rate, 1),
                "avg_win_pct": round(avg_win, 1),
                "avg_loss_pct": round(avg_loss, 1),
                "avg_pnl_pct": round(avg_pnl, 1),
                "best_pick": best_pick["symbol"] if best_pick else None,
                "best_gain_pct": best_pick["best_gain_pct"] if best_pick else None,
                "worst_pick": worst_pick["symbol"] if worst_pick else None,
                "worst_loss_pct": worst_pick["worst_loss_pct"] if worst_pick else None,
                "avg_risk_reward": avg_rr,
                "total_pnl_pct": total_pnl,
                "avg_days_held": avg_days,
                "avg_speed_days": avg_speed,
                "profit_factor": profit_factor,
            },
        }
    )


def _get_evaluated_picks() -> list[dict]:
    """Get pre-computed evaluated picks from cache or DB.  Never evaluates live."""
    # 1. Try in-memory cache
    cached = _get_cached(_EVAL_CACHE_KEY)
    if cached and isinstance(cached, list):
        return cast(list[dict], cached)

    # 2. Try DB persistence (new format)
    try:
        from src.services.persistence import load_scan

        data = load_scan("picks_evaluated")
        if data and isinstance(data, list):
            _set_cache(_EVAL_CACHE_KEY, data)
            logger.info("Loaded %d pre-evaluated picks from DB", len(data))
            return data
    except Exception:
        logger.warning("Failed to load picks evaluation from DB")

    # 3. Try legacy cache format (backwards compat with old "picks_tracker" key)
    try:
        from src.services.persistence import load_scan

        legacy = load_scan("picks_tracker")
        if legacy and isinstance(legacy, dict):
            # Old format: {cache_key: result_dict}
            for _k, v in legacy.items():
                if isinstance(v, dict) and "picks" in v:
                    picks_list = v["picks"]
                    if isinstance(picks_list, list) and picks_list:
                        _set_cache(_EVAL_CACHE_KEY, picks_list)
                        logger.info("Loaded %d picks from legacy cache format", len(picks_list))
                        return picks_list
    except Exception:
        logger.warning("Failed to load legacy picks cache")

    return []


def evaluate_all_picks(pick_type: Optional[str] = None, source_filter: Optional[str] = None) -> dict:
    """Serve pre-computed evaluation results.  Never calls market APIs.

    The heavy evaluation work is done by ``refresh_picks_evaluation()`` which
    runs in the background scheduler.  This function is a fast cache read +
    in-memory filter + stats computation.
    """
    evaluated = _get_evaluated_picks()

    if not evaluated:
        return {"picks": [], "stats": {}, "pending": True}

    # Apply filters in memory (trivial on pre-computed data)
    if pick_type:
        evaluated = [p for p in evaluated if p.get("type") == pick_type]
    if source_filter:
        evaluated = [p for p in evaluated if (p.get("source") or "").lower().startswith(source_filter.lower())]

    return _compute_stats(evaluated)


def refresh_picks_evaluation() -> int:
    """Background job: evaluate ALL picks against market data and cache results.

    Called by the background scheduler on a fixed interval.  Loads every pick
    from the DB, fetches candle data, computes win/loss status, then stores
    the evaluated list in the in-memory cache **and** the database so it
    survives server restarts.

    Returns the number of picks evaluated.
    """
    picks = load_picks()
    if not picks:
        logger.info("Picks evaluation: no picks to evaluate")
        return 0

    logger.info("Picks evaluation: starting evaluation of %d picks", len(picks))
    evaluated: list[dict] = []
    for pick in picks:
        evaluated.append(_evaluate_pick(pick))

    _set_cache(_EVAL_CACHE_KEY, evaluated)

    # Persist to DB so picks survive restarts
    try:
        from src.services.persistence import save_scan

        save_scan("picks_evaluated", evaluated)
    except Exception:
        logger.exception("Picks evaluation: failed to persist results")

    logger.info("Picks evaluation complete: %d picks evaluated", len(evaluated))
    return len(evaluated)


def get_unique_symbols() -> list[str]:
    """Return deduplicated list of symbols from picks for watchlist seeding."""
    picks = load_picks()
    seen = set()
    symbols = []
    for p in picks:
        s = p["symbol"]
        if s not in seen:
            seen.add(s)
            symbols.append(s)
    return symbols
