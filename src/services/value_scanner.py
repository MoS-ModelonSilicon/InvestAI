"""
Graham-Buffett Value Investing Scanner.

Screens the stock universe against classic value criteria:
  - P/E <= 15
  - D/E <= 1.0 (100%)
  - Current Ratio >= 1.5
  - Positive profit margin
  - Positive ROE
  - Positive free cash flow

Calculates a composite quality score (0-100) and an estimated
margin of safety using Graham's intrinsic-value formula.

Scanning runs in the background so the API returns instantly with
partial results and a progress indicator.
"""

import logging
import threading
import time
from typing import Optional

from src.services.market_data import (
    fetch_batch, fetch_stock_info, STOCK_UNIVERSE, format_market_cap, _LOW_MEMORY,
)

logger = logging.getLogger(__name__)
_MAX_WORKERS = 2 if _LOW_MEMORY else 4

EXCLUDED_SECTORS = {"Financial Services", "Real Estate"}

PE_MAX = 15
DE_MAX = 100          # Yahoo reports D/E as percentage
CURRENT_RATIO_MIN = 1.5

CRITERIA = [
    ("pe",             "P/E ≤ 15"),
    ("debt_to_equity", "D/E ≤ 1.0"),
    ("current_ratio",  "Current Ratio ≥ 1.5"),
    ("profit_margin",  "Positive Margin"),
    ("roe",            "Positive ROE"),
    ("fcf",            "Positive FCF"),
]

# ---------------------------------------------------------------------------
# Background scan state
# ---------------------------------------------------------------------------
_scan_lock = threading.Lock()
_scan_cache: dict = {
    "candidates": [],
    "rejected": [],
    "scanned": 0,
    "total": 0,
    "complete": False,
    "updated_at": 0,
}
_scan_running = False
SCAN_CACHE_TTL = 300  # 5 minutes


def _needs_metrics(d: dict) -> bool:
    return (d.get("pe_ratio") is None
            and d.get("debt_to_equity") is None
            and d.get("return_on_equity") is None)


def _check_criteria(d: dict) -> list[dict]:
    """Return a list of {key, label, passed, detail} for each criterion."""
    results = []

    pe = d.get("pe_ratio")
    if pe is not None and 0 < pe <= PE_MAX:
        results.append({"key": "pe", "label": "P/E ≤ 15", "passed": True,
                        "detail": f"P/E {pe:.1f}"})
    else:
        reason = f"P/E {pe:.1f} > 15" if pe and pe > 0 else "P/E unavailable or negative"
        results.append({"key": "pe", "label": "P/E ≤ 15", "passed": False,
                        "detail": reason})

    dte = d.get("debt_to_equity")
    if dte is not None and dte <= DE_MAX:
        results.append({"key": "debt_to_equity", "label": "D/E ≤ 1.0", "passed": True,
                        "detail": f"D/E {dte/100:.2f}"})
    else:
        reason = f"D/E {dte/100:.2f} > 1.0" if dte is not None else "D/E data missing"
        results.append({"key": "debt_to_equity", "label": "D/E ≤ 1.0", "passed": False,
                        "detail": reason})

    cr = d.get("current_ratio")
    if cr is not None and cr >= CURRENT_RATIO_MIN:
        results.append({"key": "current_ratio", "label": "Current Ratio ≥ 1.5",
                        "passed": True, "detail": f"CR {cr:.2f}"})
    else:
        reason = f"CR {cr:.2f} < 1.5" if cr is not None else "Current Ratio data missing"
        results.append({"key": "current_ratio", "label": "Current Ratio ≥ 1.5",
                        "passed": False, "detail": reason})

    pm = d.get("profit_margin")
    if pm is not None and pm > 0:
        results.append({"key": "profit_margin", "label": "Positive Margin",
                        "passed": True, "detail": f"Margin {pm:.1f}%"})
    else:
        reason = f"Margin {pm:.1f}%" if pm is not None else "Margin data missing"
        results.append({"key": "profit_margin", "label": "Positive Margin",
                        "passed": False, "detail": reason})

    roe = d.get("return_on_equity")
    if roe is not None and roe > 0:
        results.append({"key": "roe", "label": "Positive ROE", "passed": True,
                        "detail": f"ROE {roe:.1f}%"})
    else:
        reason = f"ROE {roe:.1f}%" if roe is not None else "ROE data missing"
        results.append({"key": "roe", "label": "Positive ROE", "passed": False,
                        "detail": reason})

    fcf = d.get("free_cash_flow")
    if fcf is not None and fcf > 0:
        results.append({"key": "fcf", "label": "Positive FCF", "passed": True,
                        "detail": f"FCF ${fcf/1e9:.2f}B" if abs(fcf) >= 1e9 else f"FCF ${fcf/1e6:.0f}M"})
    else:
        reason = "Negative FCF" if fcf is not None and fcf <= 0 else "FCF data missing"
        results.append({"key": "fcf", "label": "Positive FCF", "passed": False,
                        "detail": reason})

    return results


def _compute_quality_score(d: dict) -> int:
    score = 0

    roe = d.get("return_on_equity")
    if roe is not None:
        if roe >= 20:
            score += 20
        elif roe >= 15:
            score += 16
        elif roe >= 10:
            score += 12
        elif roe > 0:
            score += 6

    dte = d.get("debt_to_equity")
    if dte is not None:
        if dte <= 30:
            score += 20
        elif dte <= 50:
            score += 16
        elif dte <= 100:
            score += 10
        elif dte <= 150:
            score += 4

    pm = d.get("profit_margin")
    if pm is not None:
        if pm >= 20:
            score += 15
        elif pm >= 10:
            score += 12
        elif pm >= 5:
            score += 8
        elif pm > 0:
            score += 4

    rg = d.get("revenue_growth")
    if rg is not None:
        if rg >= 15:
            score += 15
        elif rg >= 5:
            score += 12
        elif rg >= 0:
            score += 6

    fcf = d.get("free_cash_flow")
    mcap = d.get("market_cap", 0)
    if fcf is not None and fcf > 0:
        score += 10
        if mcap > 0:
            fcf_yield = (fcf / mcap) * 100
            if fcf_yield >= 8:
                score += 5
            elif fcf_yield >= 5:
                score += 3

    div = d.get("dividend_yield")
    if div is not None and div > 0:
        score += 5

    beta = d.get("beta")
    if beta is not None and 0 < beta <= 1.2:
        score += 5

    cr = d.get("current_ratio")
    if cr is not None and cr >= 1.5:
        score += 5

    return min(100, score)


def _compute_margin_of_safety(d: dict) -> Optional[float]:
    """Graham's intrinsic value formula: V = EPS * (8.5 + 2g)"""
    eps = d.get("trailing_eps")
    price = d.get("price", 0)
    if not eps or eps <= 0 or not price:
        return None

    g = d.get("earnings_growth")
    if g is None or g < -20 or g > 100:
        g = 5.0

    intrinsic = eps * (8.5 + 2 * g)
    if intrinsic <= 0:
        return None

    mos = round((intrinsic - price) / intrinsic * 100, 1)
    return mos


def _compute_fcf_yield(d: dict) -> Optional[float]:
    fcf = d.get("free_cash_flow")
    mcap = d.get("market_cap", 0)
    if fcf is not None and mcap > 0:
        return round((fcf / mcap) * 100, 2)
    return None


def _assign_signal(passed_count: int, total: int, quality: int, mos: Optional[float]) -> str:
    if passed_count == total and quality >= 70 and mos is not None and mos >= 30:
        return "Strong Buy"
    if passed_count == total and quality >= 50:
        return "Buy"
    if passed_count >= total - 1 and quality >= 40:
        return "Watch"
    if passed_count >= total - 2 and quality >= 30:
        return "Consider"
    return "Fail"


def _evaluate_stock(d: dict) -> tuple[Optional[dict], Optional[dict]]:
    """
    Evaluate a single stock. Returns (candidate_or_None, rejected_or_None).
    """
    if d.get("asset_type") == "ETF":
        return None, None

    stock_sector = d.get("sector", "N/A")
    if stock_sector in EXCLUDED_SECTORS:
        return None, {
            "symbol": d["symbol"],
            "name": d.get("name", d["symbol"]),
            "sector": stock_sector,
            "reasons": [f"Excluded sector: {stock_sector}"],
        }

    checks = _check_criteria(d)
    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    quality = _compute_quality_score(d)
    mos = _compute_margin_of_safety(d)
    fcf_yield = _compute_fcf_yield(d)
    signal = _assign_signal(passed_count, total_count, quality, mos)

    item = {
        "symbol": d["symbol"],
        "name": d.get("name", d["symbol"]),
        "sector": stock_sector,
        "price": round(d.get("price", 0), 2),
        "market_cap": d.get("market_cap", 0),
        "market_cap_fmt": format_market_cap(d.get("market_cap", 0)),
        "pe_ratio": round(d["pe_ratio"], 1) if d.get("pe_ratio") else None,
        "roe": round(d["return_on_equity"], 1) if d.get("return_on_equity") else None,
        "debt_to_equity": round(d["debt_to_equity"] / 100, 2) if d.get("debt_to_equity") is not None else None,
        "current_ratio": round(d["current_ratio"], 2) if d.get("current_ratio") else None,
        "profit_margin": round(d["profit_margin"], 1) if d.get("profit_margin") else None,
        "fcf_yield": fcf_yield,
        "dividend_yield": d.get("dividend_yield"),
        "revenue_growth": d.get("revenue_growth"),
        "quality": quality,
        "mos": mos,
        "signal": signal,
        "criteria": checks,
        "passed_count": passed_count,
        "total_count": total_count,
    }

    if signal in ("Strong Buy", "Buy", "Watch", "Consider"):
        return item, None
    else:
        fail_reasons = [c["detail"] for c in checks if not c["passed"]]
        return None, {
            "symbol": d["symbol"],
            "name": d.get("name", d["symbol"]),
            "sector": stock_sector,
            "reasons": fail_reasons,
        }


# ---------------------------------------------------------------------------
# Background scan
# ---------------------------------------------------------------------------
def _run_background_scan():
    """Fetch stocks with metrics in batches and update the scan cache progressively."""
    global _scan_running
    import src.services.market_data as md

    try:
        cached = fetch_batch(STOCK_UNIVERSE, cached_only=True)
        cached_map = {d["symbol"]: d for d in cached}
        etf_symbols = {d["symbol"] for d in cached if d.get("asset_type") == "ETF"}
        universe = [s for s in STOCK_UNIVERSE if s not in etf_symbols]

        with_metrics = []
        needs_fetch = []

        for sym in universe:
            d = cached_map.get(sym)
            if d is None:
                needs_fetch.append(sym)
            elif _needs_metrics(d):
                needs_fetch.append(sym)
            else:
                with_metrics.append(d)

        total = len(universe)

        # Phase 1: Evaluate stocks that already have metrics (instant)
        candidates = []
        rejected = []
        for d in with_metrics:
            cand, rej = _evaluate_stock(d)
            if cand:
                candidates.append(cand)
            if rej:
                rejected.append(rej)

        candidates.sort(key=lambda x: x["quality"], reverse=True)

        with _scan_lock:
            _scan_cache["candidates"] = list(candidates)
            _scan_cache["rejected"] = list(rejected)
            _scan_cache["scanned"] = len(with_metrics)
            _scan_cache["total"] = total
            _scan_cache["complete"] = len(needs_fetch) == 0
            _scan_cache["updated_at"] = time.time()

        if not needs_fetch:
            return

        # Phase 2: Fetch remaining stocks in small batches
        BATCH_SIZE = 8
        _vs_batch_num = 0
        for batch_start in range(0, len(needs_fetch), BATCH_SIZE):
            batch = needs_fetch[batch_start:batch_start + BATCH_SIZE]
            _vs_batch_num += 1

            for sym in batch:
                if sym in cached_map:
                    with md._cache_lock:
                        md._cache.pop(f"info:{sym}", None)

            batch_results = []
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def _fetch(sym):
                try:
                    return fetch_stock_info(sym, full=True)
                except Exception:
                    return None

            with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
                futures = {pool.submit(_fetch, s): s for s in batch}
                for fut in as_completed(futures):
                    r = fut.result()
                    if r and r.get("price", 0) > 0:
                        batch_results.append(r)

            batch_cands = []
            batch_rej = []
            for d in batch_results:
                cand, rej = _evaluate_stock(d)
                if cand:
                    batch_cands.append(cand)
                if rej:
                    batch_rej.append(rej)

            with _scan_lock:
                _scan_cache["candidates"].extend(batch_cands)
                _scan_cache["rejected"].extend(batch_rej)
                _scan_cache["scanned"] += len(batch)
                _scan_cache["candidates"].sort(key=lambda x: x["quality"], reverse=True)
                _scan_cache["updated_at"] = time.time()

            # Persist intermediate results to DB periodically so they
            # survive Render free-tier restarts before the scan completes
            if _vs_batch_num <= 2 or _vs_batch_num % 5 == 0:
                try:
                    from src.services.persistence import save_scan
                    with _scan_lock:
                        snapshot = dict(_scan_cache)
                    save_scan("value_scan", snapshot)
                except Exception:
                    logger.warning("Value scanner: failed to persist intermediate results")

        with _scan_lock:
            _scan_cache["complete"] = True
            _scan_cache["updated_at"] = time.time()

        logger.info("Value scanner: background scan complete - %d candidates, %d rejected",
                     len(_scan_cache["candidates"]), len(_scan_cache["rejected"]))

        # Persist results to DB so they survive restarts
        try:
            from src.services.persistence import save_scan
            with _scan_lock:
                snapshot = dict(_scan_cache)
            save_scan("value_scan", snapshot)
        except Exception:
            logger.exception("Value scanner: failed to persist results")
    except Exception:
        logger.exception("Value scanner background scan failed")
        with _scan_lock:
            _scan_cache["complete"] = True
    finally:
        _scan_running = False


def _ensure_scan_running():
    """Safety-net fallback: start a scan if cache is completely empty.

    Only fires before the scheduler has run its first scan.  Once the
    scheduler is producing results this is essentially a no-op.
    """
    global _scan_running
    with _scan_lock:
        if _scan_running:
            return
        # If we already have results, let the scheduler handle refreshes
        if _scan_cache["candidates"]:
            return
        # No results at all — kick off a scan so the user isn't stuck
        _scan_running = True
        _scan_cache["complete"] = False
        _scan_cache["scanned"] = 0

    t = threading.Thread(target=_run_background_scan, daemon=True)
    t.start()


def run_full_scan():
    """Entry point called by the background scheduler.

    Runs a complete scan synchronously (blocking).  Safe to call from
    any thread — guards against concurrent scans internally.
    """
    global _scan_running
    with _scan_lock:
        if _scan_running:
            logger.info("Value scanner: scan already in progress, skipping")
            return
        _scan_running = True
        _scan_cache["complete"] = False
        _scan_cache["scanned"] = 0

    _run_background_scan()


# Kept for backward compat but no longer needed — scheduler handles repeats
def start_auto_scanner():
    """Legacy entry point.  Now a no-op; use background_scheduler instead."""
    logger.info("start_auto_scanner() called — scanning is handled by background_scheduler")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def scan_value_stocks(
    sector: Optional[str] = None,
    signal_filter: Optional[str] = None,
    sort_by: str = "score",
    page: int = 1,
    per_page: int = 15,
) -> dict:
    """
    Return current scan results with pagination and progress.
    Kicks off a background scan if needed.
    """
    _ensure_scan_running()

    with _scan_lock:
        all_candidates = list(_scan_cache["candidates"])
        all_rejected = list(_scan_cache["rejected"])
        scanned = _scan_cache["scanned"]
        total = _scan_cache["total"]
        complete = _scan_cache["complete"]
        updated_at = _scan_cache["updated_at"]

    if sector:
        all_candidates = [c for c in all_candidates if c["sector"].lower() == sector.lower()]
        all_rejected = [r for r in all_rejected if r.get("sector", "").lower() == sector.lower()]

    if signal_filter:
        all_candidates = [c for c in all_candidates if c["signal"] == signal_filter]

    sort_keys = {
        "score": lambda x: x["quality"],
        "mos": lambda x: x["mos"] if x["mos"] is not None else -999,
        "pe": lambda x: x["pe_ratio"] if x["pe_ratio"] is not None else 999,
        "roe": lambda x: x["roe"] if x["roe"] is not None else -999,
        "fcf_yield": lambda x: x["fcf_yield"] if x["fcf_yield"] is not None else -999,
    }
    key_fn = sort_keys.get(sort_by, sort_keys["score"])
    reverse = sort_by != "pe"
    all_candidates.sort(key=key_fn, reverse=reverse)

    total_candidates = len(all_candidates)
    total_pages = max(1, (total_candidates + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_candidates = all_candidates[start:start + per_page]

    return {
        "candidates": page_candidates,
        "rejected": all_rejected,
        "stats": {
            "scanned": scanned,
            "candidates": total_candidates,
            "rejected": len(all_rejected),
        },
        "progress": {
            "scanned": scanned,
            "total": total,
            "complete": complete,
            "updated_at": int(updated_at) if updated_at else None,
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_candidates,
        },
    }


# ---------------------------------------------------------------------------
# Action Plan Builder
# ---------------------------------------------------------------------------

# Weight multipliers per signal (higher = bigger allocation)
_SIGNAL_WEIGHTS = {
    "Strong Buy": 4.0,
    "Buy": 2.5,
    "Watch": 1.0,
    "Consider": 0.5,
}

# Strategy recommendations per signal
_SIGNAL_STRATEGIES = {
    "Strong Buy": {
        "action": "Buy now",
        "strategy": "Lump-sum entry — stock passes all Graham-Buffett criteria with high quality and strong margin of safety.",
        "position_limit": "Up to 8% of portfolio",
        "risk": "Low relative risk — strong fundamentals across all criteria.",
    },
    "Buy": {
        "action": "Buy / Start DCA",
        "strategy": "Solid value candidate. Consider dollar-cost averaging over 2–4 weeks to reduce timing risk.",
        "position_limit": "Up to 5% of portfolio",
        "risk": "Moderate — passes all criteria but margin of safety or quality could be stronger.",
    },
    "Watch": {
        "action": "Add to watchlist",
        "strategy": "Close to a buy. One criterion didn't pass. Set a price alert and wait for a better entry.",
        "position_limit": "Up to 3% if you decide to enter",
        "risk": "Higher — one weak spot. Monitor quarterly earnings for improvement.",
    },
    "Consider": {
        "action": "Research more",
        "strategy": "Has potential but multiple criteria need improvement. Dig deeper before committing capital.",
        "position_limit": "Max 2% — speculative allocation only",
        "risk": "Elevated — several fundamentals are below threshold. Not a classic value play yet.",
    },
}


def build_action_plan(
    amount: float = 10000,
    sector: Optional[str] = None,
    signal_filter: Optional[str] = None,
) -> dict:
    """
    Build a portfolio action plan from current scan candidates.
    Groups stocks by signal, assigns allocation weights based on
    quality score and signal strength, calculates dollar amounts.
    """
    _ensure_scan_running()

    with _scan_lock:
        all_candidates = list(_scan_cache["candidates"])
        complete = _scan_cache["complete"]
        scanned = _scan_cache["scanned"]
        total = _scan_cache["total"]

    # Apply filters
    if sector:
        all_candidates = [c for c in all_candidates if c["sector"].lower() == sector.lower()]
    if signal_filter:
        all_candidates = [c for c in all_candidates if c["signal"] == signal_filter]

    # Sort by quality within each signal
    all_candidates.sort(key=lambda x: x["quality"], reverse=True)

    # Build signal groups
    groups = {}
    for sig in ("Strong Buy", "Buy", "Watch", "Consider"):
        members = [c for c in all_candidates if c["signal"] == sig]
        if members:
            groups[sig] = members

    if not groups:
        return {
            "plan": [],
            "summary": {
                "total_investment": amount,
                "allocated": 0,
                "stocks_count": 0,
                "signal_breakdown": {},
            },
            "ready": complete,
        }

    # Calculate raw weights: signal_weight * (quality / 100)
    weighted_stocks = []
    for sig, members in groups.items():
        sig_w = _SIGNAL_WEIGHTS.get(sig, 1.0)
        for c in members:
            raw_weight = sig_w * (c["quality"] / 100.0)
            weighted_stocks.append({**c, "_raw_weight": raw_weight})

    total_raw = sum(s["_raw_weight"] for s in weighted_stocks)
    if total_raw <= 0:
        total_raw = 1  # avoid division by zero

    # Normalize weights and compute dollar allocations
    for s in weighted_stocks:
        s["allocation_pct"] = round((s["_raw_weight"] / total_raw) * 100, 1)
        s["allocation_dollars"] = round((s["_raw_weight"] / total_raw) * amount, 2)
        if s["price"] and s["price"] > 0:
            s["suggested_shares"] = round(s["allocation_dollars"] / s["price"], 2)
        else:
            s["suggested_shares"] = 0

    # Build grouped plan
    plan = []
    signal_breakdown = {}
    for sig in ("Strong Buy", "Buy", "Watch", "Consider"):
        members = [s for s in weighted_stocks if s["signal"] == sig]
        if not members:
            continue
        strategy_info = _SIGNAL_STRATEGIES[sig]
        group_alloc_pct = round(sum(m["allocation_pct"] for m in members), 1)
        group_alloc_dollars = round(sum(m["allocation_dollars"] for m in members), 2)
        signal_breakdown[sig] = {
            "count": len(members),
            "allocation_pct": group_alloc_pct,
            "allocation_dollars": group_alloc_dollars,
        }

        stocks_in_group = []
        for m in members:
            # Generate per-stock reasoning
            strengths = [cr["detail"] for cr in m.get("criteria", []) if cr["passed"]]
            weaknesses = [cr["detail"] for cr in m.get("criteria", []) if not cr["passed"]]

            stocks_in_group.append({
                "symbol": m["symbol"],
                "name": m["name"],
                "sector": m["sector"],
                "price": m["price"],
                "quality": m["quality"],
                "mos": m["mos"],
                "pe_ratio": m["pe_ratio"],
                "allocation_pct": m["allocation_pct"],
                "allocation_dollars": m["allocation_dollars"],
                "suggested_shares": m["suggested_shares"],
                "strengths": strengths[:3],
                "weaknesses": weaknesses[:3],
            })

        plan.append({
            "signal": sig,
            "action": strategy_info["action"],
            "strategy": strategy_info["strategy"],
            "position_limit": strategy_info["position_limit"],
            "risk_note": strategy_info["risk"],
            "group_allocation_pct": group_alloc_pct,
            "group_allocation_dollars": group_alloc_dollars,
            "stocks": stocks_in_group,
        })

    return {
        "plan": plan,
        "summary": {
            "total_investment": amount,
            "allocated": round(sum(s["allocation_dollars"] for s in weighted_stocks), 2),
            "stocks_count": len(weighted_stocks),
            "signal_breakdown": signal_breakdown,
        },
        "ready": complete,
    }
