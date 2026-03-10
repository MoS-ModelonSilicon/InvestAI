"""
AutoPilot Smart Portfolio Simulator.

Defines three investment strategy profiles (Daredevil, Strategist, Fortress)
and runs day-by-day historical backtests using real price data to demonstrate
portfolio performance against the S&P 500 benchmark.

Performance: uses batch_download_candles (single HTTP call via yf.download)
instead of per-symbol get_candles to fetch all symbols at once.  Results are
pre-computed by the background scheduler and persisted to the database so
they survive server restarts.
"""

import logging
import math
import threading
from datetime import datetime, timedelta
from typing import Any, Optional, cast

from src.services import data_provider as dp
from src.services.market_data import _get_cached, _set_cache

# ── Module-level cache for pre-computed simulations ──────────
_sim_cache: dict[str, dict] = {}
_sim_lock = threading.Lock()

# Yahoo-Finance period strings for batch download
PERIOD_TO_YF = {"1y": "1y", "6m": "6mo", "3m": "3mo", "1m": "1mo"}
AUTOPILOT_PERIODS = list(PERIOD_TO_YF.keys())
AUTOPILOT_AMOUNTS = [10000]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

PROFILES = {
    "daredevil": {
        "id": "daredevil",
        "name": "The Daredevil",
        "subtitle": "Aggressive Growth",
        "risk_level": "High",
        "risk_score": 9,
        "description": (
            "Maximum growth through momentum-driven stock picking. "
            "Heavy allocation to high-beta tech, thematic ETFs, and "
            "emerging-market plays. Wild swings, big potential."
        ),
        "strategy": "Momentum + Growth Hunting",
        "rebalance": "Monthly",
        "expected_return": "18-30%",
        "expected_drawdown": "25-45%",
        "sleeves": [
            {
                "label": "High-Beta Growth Stocks",
                "pct": 55,
                "symbols": [
                    "NVDA",
                    "TSLA",
                    "META",
                    "AMD",
                    "AVGO",
                    "MRVL",
                    "PANW",
                    "SHOP",
                    "NFLX",
                    "CRM",
                ],
            },
            {
                "label": "Thematic / Sector ETFs",
                "pct": 25,
                "symbols": ["SOXX", "SMH", "ARKK", "KWEB", "XLK"],
            },
            {
                "label": "Emerging Market High-Conviction",
                "pct": 15,
                "symbols": ["BABA", "NIO", "SE", "NU", "PDD"],
            },
            {
                "label": "Cash Buffer",
                "pct": 5,
                "symbols": [],
            },
        ],
    },
    "strategist": {
        "id": "strategist",
        "name": "The Strategist",
        "subtitle": "Balanced Multi-Factor",
        "risk_level": "Medium",
        "risk_score": 5,
        "description": (
            "A core-satellite approach blending broad-market index exposure "
            "with quality-value picks, dividend growers, bonds, and global "
            "diversification. Steady growth with controlled volatility."
        ),
        "strategy": "Core-Satellite + Multi-Factor",
        "rebalance": "Quarterly",
        "expected_return": "10-16%",
        "expected_drawdown": "12-22%",
        "sleeves": [
            {
                "label": "Core Broad Market",
                "pct": 35,
                "symbols": ["SPY", "VTI", "VOO"],
            },
            {
                "label": "Quality-Value Stocks",
                "pct": 20,
                "symbols": [
                    "AAPL",
                    "MSFT",
                    "GOOGL",
                    "JPM",
                    "UNH",
                    "BRK-B",
                    "JNJ",
                    "V",
                    "PG",
                    "HD",
                ],
            },
            {
                "label": "Dividend Growth",
                "pct": 15,
                "symbols": ["SCHD", "VIG", "KO", "PEP", "MCD"],
            },
            {
                "label": "Fixed Income",
                "pct": 15,
                "symbols": ["BND", "AGG", "TLT"],
            },
            {
                "label": "International",
                "pct": 10,
                "symbols": ["VEA", "INDA", "EWG"],
            },
            {
                "label": "Cash",
                "pct": 5,
                "symbols": [],
            },
        ],
    },
    "fortress": {
        "id": "fortress",
        "name": "The Fortress",
        "subtitle": "Conservative Shield",
        "risk_level": "Low",
        "risk_score": 2,
        "description": (
            "Capital preservation first. A risk-parity blend of bonds, "
            "dividend aristocrats, low-volatility blue chips, and a gold "
            "hedge. Sleep well at night while your money works slowly."
        ),
        "strategy": "Risk Parity + Dividend Shield",
        "rebalance": "Quarterly",
        "expected_return": "5-10%",
        "expected_drawdown": "5-12%",
        "sleeves": [
            {
                "label": "Bonds & Treasuries",
                "pct": 30,
                "symbols": ["BND", "AGG", "TLT", "TIP", "VCSH"],
            },
            {
                "label": "Dividend Aristocrats",
                "pct": 25,
                "symbols": ["JNJ", "PG", "KO", "PEP", "MCD", "SCHD", "VIG"],
            },
            {
                "label": "Low-Volatility Blue Chips",
                "pct": 20,
                "symbols": ["NEE", "DUK", "SO", "COST", "WMT", "CL"],
            },
            {
                "label": "Broad Market Index",
                "pct": 15,
                "symbols": ["VOO"],
            },
            {
                "label": "Gold & Commodities Hedge",
                "pct": 5,
                "symbols": ["GLD", "SLV"],
            },
            {
                "label": "Cash",
                "pct": 5,
                "symbols": [],
            },
        ],
    },
}

PERIOD_DAYS = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_daily_closes(symbol: str, from_ts: int, to_ts: int) -> Optional[dict]:
    """Return {dates: [str], closes: [float]} for a symbol."""
    candles = dp.get_candles(symbol, "D", from_ts, to_ts)
    if not candles or not candles.get("c") or not candles.get("t"):
        return None
    dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in candles["t"]]
    return {"dates": dates, "closes": candles["c"]}


def _align_to_dates(target_dates: list[str], sym_dates: list[str], sym_closes: list[float]) -> list[Optional[float]]:
    """Map symbol prices onto the target date grid via lookup dict."""
    lookup = dict(zip(sym_dates, sym_closes))
    result = []
    last_known = None
    for d in target_dates:
        if d in lookup:
            last_known = lookup[d]
        result.append(last_known)
    return result


def _batch_fetch_closes(symbols: list[str], period: str) -> dict[str, dict]:
    """Fetch daily closes for ALL symbols in a single HTTP call.

    Returns {symbol: {dates: [...], closes: [...]}}.
    Falls back to per-symbol get_candles on failure.
    """
    yf_period = PERIOD_TO_YF.get(period, "1y")
    result: dict[str, dict] = {}
    try:
        batch = dp.batch_download_candles(symbols, period=yf_period)
        if batch:
            for sym, candles in batch.items():
                if candles and candles.get("c") and candles.get("t"):
                    dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in candles["t"]]
                    result[sym] = {"dates": dates, "closes": candles["c"]}
    except Exception:
        pass  # fall through to per-symbol below

    # Fill any symbols that batch missed
    from datetime import timedelta as _td

    days = PERIOD_DAYS.get(period, 365)
    now = datetime.now()
    from_ts = int((now - _td(days=days)).timestamp())
    to_ts = int(now.timestamp())
    for sym in symbols:
        if sym not in result:
            sd = _fetch_daily_closes(sym, from_ts, to_ts)
            if sd:
                result[sym] = sd
    return result


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------


def get_profiles() -> list[dict]:
    """Return summary info for all three profiles."""
    out = []
    for p in PROFILES.values():
        sleeves_raw: list[dict] = p["sleeves"]  # type: ignore[assignment]
        sleeves_summary = [{"label": s["label"], "pct": s["pct"], "symbols": s["symbols"]} for s in sleeves_raw]
        out.append(
            {
                "id": p["id"],
                "name": p["name"],
                "subtitle": p["subtitle"],
                "risk_level": p["risk_level"],
                "risk_score": p["risk_score"],
                "description": p["description"],
                "strategy": p["strategy"],
                "rebalance": p["rebalance"],
                "expected_return": p["expected_return"],
                "expected_drawdown": p["expected_drawdown"],
                "sleeves": sleeves_summary,
            }
        )
    return out


def simulate(profile_id: str, amount: float = 10000, period: str = "1y") -> dict:
    """
    Run a day-by-day historical backtest for the given profile.

    Returns daily portfolio values, benchmark values, holdings breakdown,
    and performance statistics.
    """
    # Normalize amount to int when it's a whole number so cache keys match
    # between the API (float 10000.0) and scheduler (int 10000).
    amt_key = int(amount) if amount == int(amount) else amount
    cache_key = f"autopilot:{profile_id}:{amt_key}:{period}"

    # Fast path: module-level sim cache (populated by scheduler/persistence)
    with _sim_lock:
        if cache_key in _sim_cache:
            return _sim_cache[cache_key]

    # Medium path: market_data in-memory cache
    cached = _get_cached(cache_key)
    if isinstance(cached, dict):
        return cast(dict[str, Any], cached)

    # DB fallback: load persisted simulation result (survives restarts)
    try:
        from src.services.persistence import load_scan

        db_data = load_scan(cache_key)
        if db_data and isinstance(db_data, dict) and db_data.get("stats"):
            logger.info("Restored autopilot sim from DB: %s", cache_key)
            # Warm all caches so subsequent calls are instant
            with _sim_lock:
                _sim_cache[cache_key] = db_data
            _set_cache(cache_key, db_data)
            return db_data
    except Exception:
        logger.debug("DB fallback failed for %s", cache_key)

    profile = PROFILES.get(profile_id)
    if not profile:
        return {"error": f"Unknown profile: {profile_id}"}

    days = PERIOD_DAYS.get(period, 365)
    now = datetime.now()
    start = now - timedelta(days=days)
    from_ts = int(start.timestamp())
    to_ts = int(now.timestamp())

    # Fetch benchmark (SPY)
    bench_data = _fetch_daily_closes("SPY", from_ts, to_ts)
    if not bench_data or len(bench_data["dates"]) < 2:
        return {"error": "Could not fetch benchmark data"}

    trading_dates = bench_data["dates"]
    bench_closes = bench_data["closes"]
    bench_start_price = bench_closes[0]

    # Build portfolio: allocate capital across sleeves and symbols
    holdings: list[dict[str, Any]] = []
    # Collect all unique symbols
    all_symbols = []
    for sleeve in cast(list[dict[str, Any]], profile["sleeves"]):
        all_symbols.extend(sleeve.get("symbols", []))
    all_symbols = list(dict.fromkeys(["SPY", *all_symbols]))  # dedupe, SPY first

    # Batch-fetch all symbols in a single HTTP call
    fetched = _batch_fetch_closes(all_symbols, period)

    # Benchmark
    bench_data = fetched.get("SPY")
    if not bench_data or len(bench_data.get("dates", [])) < 2:
        return {"error": "Could not fetch benchmark data"}

    trading_dates = bench_data["dates"]
    bench_closes = bench_data["closes"]
    bench_start_price = bench_closes[0]

    # Build portfolio
    holdings = []
    all_symbol_prices = {}

    for sleeve in cast(list[dict[str, Any]], profile["sleeves"]):
        if not sleeve["symbols"]:
            continue
        sleeve_capital = amount * (sleeve["pct"] / 100.0)
        per_symbol = sleeve_capital / len(sleeve["symbols"])

        for sym in sleeve["symbols"]:
            sym_data = fetched.get(sym)
            if not sym_data or not sym_data["closes"]:
                continue

            aligned = _align_to_dates(trading_dates, sym_data["dates"], sym_data["closes"])

            first_price = None
            for p in aligned:
                if p is not None:
                    first_price = p
                    break
            if first_price is None or first_price <= 0:
                continue

            shares = per_symbol / first_price
            all_symbol_prices[sym] = aligned
            holdings.append(
                {
                    "symbol": sym,
                    "sleeve": sleeve["label"],
                    "allocation_pct": round(per_symbol / amount * 100, 2),
                    "shares": round(shares, 4),
                    "buy_price": round(first_price, 2),
                    "invested": round(per_symbol, 2),
                }
            )

    if not holdings:
        return {"error": "No holdings could be constructed — market data unavailable"}

    # Compute cash allocation
    invested_total = sum(h["invested"] for h in holdings)
    cash = amount - invested_total

    # Day-by-day portfolio value
    daily_values = []
    daily_returns = []
    prev_value = amount

    for i, _date_str in enumerate(trading_dates):
        day_total = cash
        for h in holdings:
            prices = all_symbol_prices.get(h["symbol"])
            if prices and prices[i] is not None:
                day_total += h["shares"] * prices[i]
            else:
                day_total += h["invested"]

        daily_values.append(round(day_total, 2))
        day_ret = ((day_total - prev_value) / prev_value * 100) if prev_value > 0 else 0
        daily_returns.append(round(day_ret, 4))
        prev_value = day_total

    # Benchmark daily values (normalized to same starting amount)
    bench_values = [round(amount * (p / bench_start_price), 2) for p in bench_closes]

    # Enrich holdings with current prices and gain/loss
    enriched_holdings = []
    for h in holdings:
        prices = all_symbol_prices.get(h["symbol"])
        current_price = None
        if prices:
            for p in reversed(prices):
                if p is not None:
                    current_price = p
                    break
        current_price = current_price or h["buy_price"]
        current_value = h["shares"] * current_price
        gl = current_value - h["invested"]
        gl_pct = (gl / h["invested"] * 100) if h["invested"] > 0 else 0

        enriched_holdings.append(
            {
                **h,
                "current_price": round(current_price, 2),
                "current_value": round(current_value, 2),
                "gain_loss": round(gl, 2),
                "gain_loss_pct": round(gl_pct, 2),
            }
        )

    enriched_holdings.sort(key=lambda x: x["current_value"], reverse=True)

    # Statistics
    final_value = daily_values[-1] if daily_values else amount
    total_return_pct = (final_value - amount) / amount * 100
    bench_final = bench_values[-1] if bench_values else amount
    bench_return_pct = (bench_final - amount) / amount * 100
    alpha = total_return_pct - bench_return_pct

    # Daily return stats (skip day 0 which is always ~0)
    rets = daily_returns[1:] if len(daily_returns) > 1 else daily_returns
    positive_days = sum(1 for r in rets if r > 0)
    win_rate = (positive_days / len(rets) * 100) if rets else 0
    best_day = max(rets) if rets else 0
    worst_day = min(rets) if rets else 0

    # Max drawdown
    peak = daily_values[0] if daily_values else amount
    max_dd = 0
    for v in daily_values:
        if v > peak:
            peak = v
        dd = ((peak - v) / peak * 100) if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Annualized Sharpe ratio (risk-free rate ~ 4.5%)
    if len(rets) > 1:
        avg_daily = sum(rets) / len(rets)
        std_daily = math.sqrt(sum((r - avg_daily) ** 2 for r in rets) / (len(rets) - 1))
        annual_return = avg_daily * 252
        annual_vol = std_daily * math.sqrt(252)
        sharpe = ((annual_return - 4.5) / annual_vol) if annual_vol > 0 else 0
    else:
        sharpe = 0

    stats = {
        "total_return": round(final_value - amount, 2),
        "total_return_pct": round(total_return_pct, 2),
        "bench_return_pct": round(bench_return_pct, 2),
        "alpha": round(alpha, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "win_rate": round(win_rate, 1),
        "best_day": round(best_day, 2),
        "worst_day": round(worst_day, 2),
        "final_value": round(final_value, 2),
        "starting_amount": amount,
        "trading_days": len(trading_dates),
    }

    # Sleeve-level allocation summary
    sleeve_summary = {}
    for h in enriched_holdings:
        sl = h["sleeve"]
        if sl not in sleeve_summary:
            sleeve_summary[sl] = {"label": sl, "invested": 0, "current_value": 0}
        sleeve_summary[sl]["invested"] += h["invested"]
        sleeve_summary[sl]["current_value"] += h["current_value"]

    for sl_data in sleeve_summary.values():
        sl_data["invested"] = round(sl_data["invested"], 2)
        sl_data["current_value"] = round(sl_data["current_value"], 2)
        sl_data["gain_loss"] = round(sl_data["current_value"] - sl_data["invested"], 2)
        sl_data["pct"] = round(sl_data["current_value"] / final_value * 100, 1) if final_value > 0 else 0

    result = {
        "profile": {
            "id": profile["id"],
            "name": profile["name"],
            "subtitle": profile["subtitle"],
            "strategy": profile["strategy"],
            "risk_level": profile["risk_level"],
        },
        "chart": {
            "dates": trading_dates,
            "portfolio": daily_values,
            "benchmark": bench_values,
        },
        "stats": stats,
        "holdings": enriched_holdings,
        "sleeves": list(sleeve_summary.values()),
        "cash": round(cash, 2),
    }

    _set_cache(cache_key, result)
    with _sim_lock:
        _sim_cache[cache_key] = result
    try:
        from src.services.persistence import save_scan

        save_scan(cache_key, result)
    except Exception:
        pass
    return result


def get_cached_status() -> dict[str, bool]:
    """Return which profile/period combos are cached and ready.

    Used by the frontend to show instant results vs 'needs computation' state.
    """
    from src.services.persistence import load_scan

    status: dict[str, bool] = {}
    for profile_id in PROFILES:
        for period in AUTOPILOT_PERIODS:
            for amount in AUTOPILOT_AMOUNTS:
                key = f"autopilot:{profile_id}:{amount}:{period}"
                # Check in-memory first (fastest)
                with _sim_lock:
                    if key in _sim_cache:
                        status[f"{profile_id}:{period}"] = True
                        continue
                cached = _get_cached(key)
                if isinstance(cached, dict):
                    status[f"{profile_id}:{period}"] = True
                    continue
                # Check DB
                try:
                    db = load_scan(key)
                    status[f"{profile_id}:{period}"] = bool(db and isinstance(db, dict) and db.get("stats"))
                except Exception:
                    status[f"{profile_id}:{period}"] = False
    return status


def run_full_warmup() -> None:
    """Pre-compute simulations for all profile/period/amount combos.

    Called by background_scheduler to ensure instant API responses.
    """
    ok = 0
    failed = 0
    from_db = 0
    for profile_id in PROFILES:
        for period in AUTOPILOT_PERIODS:
            for amount in AUTOPILOT_AMOUNTS:
                key = f"autopilot:{profile_id}:{amount}:{period}"
                try:
                    result = simulate(profile_id, amount=amount, period=period)
                    if isinstance(result, dict) and result.get("stats"):
                        ok += 1
                        # Check if it came from DB (already logged inside simulate)
                    elif isinstance(result, dict) and result.get("error"):
                        failed += 1
                        logger.warning("Warmup %s: %s", key, result["error"])
                    else:
                        failed += 1
                except Exception:
                    failed += 1
                    logger.exception("Warmup failed for %s/%s/%s", profile_id, period, amount)
    logger.info("Autopilot warmup: %d OK, %d failed (of %d total)", ok, failed, ok + failed)
