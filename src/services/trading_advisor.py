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
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional

from src.services import data_provider as dp
from src.services import technical_analysis as ta
from src.services.market_data import (
    fetch_batch, fetch_stock_info, ALL_UNIVERSE,
    _get_cached, _set_cache, format_market_cap,
)

logger = logging.getLogger(__name__)

CANDLE_LOOKBACK_DAYS = 420
SCAN_CACHE_TTL = 1800  # 30 min

_scan_lock = threading.Lock()
_scan_cache: dict = {
    "all_picks": [],
    "packages": {},
    "market_mood": {"bullish": 0, "neutral": 0, "bearish": 0},
    "scanned": 0,
    "total": 0,
    "complete": False,
    "updated_at": 0,
}
_scan_running = False


# ---------------------------------------------------------------------------
# Single-stock analysis
# ---------------------------------------------------------------------------

def _analyze_stock(symbol: str, candles: dict, fund_info: dict) -> Optional[dict]:
    """Compute all indicators and build an action card for one stock."""
    closes = candles.get("c", [])
    if len(closes) < 50:
        return None

    highs = candles.get("h", closes)
    lows = candles.get("l", closes)
    volumes = candles.get("v", [0] * len(closes))
    timestamps = candles.get("t", [])

    sma50 = ta.sma(closes, 50)
    sma200 = ta.sma(closes, 200)
    rsi_vals = ta.rsi(closes)
    macd_data = ta.macd(closes)
    boll = ta.bollinger_bands(closes)
    stoch = ta.stochastic(highs, lows, closes)
    atr_vals = ta.atr(highs, lows, closes)
    obv_vals = ta.obv(closes, volumes)

    comp = ta.composite_score(
        rsi_vals, macd_data, closes, sma50, sma200,
        boll["pct_b"], stoch, obv_vals,
    )

    current = closes[-1]
    last_atr = ta._last_valid(atr_vals)
    boll_lower = ta._last_valid(boll["lower"])
    boll_upper = ta._last_valid(boll["upper"])
    cur_rsi = ta._last_valid(rsi_vals)
    cur_stoch_k = ta._last_valid(stoch["k"])
    s50 = ta._last_valid(sma50)
    s200 = ta._last_valid(sma200)

    entry = current
    if boll_lower and current > boll_lower:
        entry = round((current + boll_lower) / 2, 2)

    target = round(boll_upper, 2) if boll_upper else round(current * 1.08, 2)
    stop = round(entry - 2 * last_atr, 2) if last_atr else round(entry * 0.95, 2)
    if stop >= entry:
        stop = round(entry * 0.95, 2)
    rr = round((target - entry) / (entry - stop), 2) if entry > stop else 0

    macd_hist = macd_data["histogram"]
    recent_hist = [h for h in macd_hist[-5:] if h is not None]
    macd_bullish_cross = (
        len(recent_hist) >= 2
        and any(h <= 0 for h in recent_hist[:-1])
        and recent_hist[-1] > 0
    )

    avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0
    vol_above_avg = volumes[-1] > avg_vol_20 * 1.2 if avg_vol_20 > 0 else False

    boll_pct_b = ta._last_valid(boll["pct_b"])
    boll_bandwidth = None
    if boll_upper and boll_lower:
        mid = ta._last_valid(boll["middle"])
        if mid and mid > 0:
            boll_bandwidth = (boll_upper - boll_lower) / mid

    sparkline = closes[-30:] if len(closes) >= 30 else closes

    signals_text = [s["detail"] for s in comp["signals"] if s["score"] != 0]

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
        "signals_text": signals_text,
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
        p for p in picks
        if p["macd_bullish_cross"]
        and p["above_sma50"]
        and (p["rsi"] is not None and 45 <= p["rsi"] <= 75)
    ]
    if len(pool) < 3:
        pool = [
            p for p in picks
            if p["macd_hist_positive"] and p["above_sma50"]
            and (p["rsi"] is not None and p["rsi"] < 75)
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
        p for p in picks
        if p["golden_cross"]
        and p["macd_hist_positive"]
        and (p["rsi"] is not None and 35 <= p["rsi"] <= 65)
    ]
    if len(pool) < 3:
        pool = [
            p for p in picks
            if p["above_sma50"]
            and (p["rsi"] is not None and 30 <= p["rsi"] <= 65)
        ]
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
        p for p in picks
        if p["rsi"] is not None and p["rsi"] < 40
        and (p["boll_pct_b"] is not None and p["boll_pct_b"] < 0.3)
    ]
    if len(pool) < 3:
        pool = [
            p for p in picks
            if p["rsi"] is not None and p["rsi"] < 45
        ]
    pool.sort(key=lambda x: x["rsi"] if x["rsi"] is not None else 100)
    return {
        "id": "oversold",
        "name": "Oversold Bargains",
        "subtitle": "Potential entry points for patient buyers — prices near support",
        "timeframe": "Weeks to Months",
        "risk_level": "Medium-Low",
        "picks": pool[:8],
    }


# ---------------------------------------------------------------------------
# Background scanner
# ---------------------------------------------------------------------------

def _run_background_scan():
    """Scan universe in batches, progressively updating the cache."""
    global _scan_running

    try:
        fundamentals = fetch_batch(ALL_UNIVERSE, cached_only=True)
        fund_map = {d["symbol"]: d for d in fundamentals if d.get("price", 0) > 0}
        symbols = list(fund_map.keys())
        total = len(symbols)

        with _scan_lock:
            _scan_cache["total"] = total
            _scan_cache["scanned"] = 0
            _scan_cache["complete"] = False
            _scan_cache["updated_at"] = time.time()

        if not symbols:
            with _scan_lock:
                _scan_cache["complete"] = True
            return

        to_ts = int(time.time())
        from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400
        all_picks: list[dict] = []

        BATCH = 8
        for batch_start in range(0, len(symbols), BATCH):
            batch_syms = symbols[batch_start:batch_start + BATCH]

            def _fetch(sym):
                try:
                    return sym, dp.get_candles(sym, "D", from_ts, to_ts)
                except Exception:
                    return sym, None

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(_fetch, s): s for s in batch_syms}
                for fut in as_completed(futures):
                    sym, candles = fut.result()
                    if candles and candles.get("c"):
                        pick = _analyze_stock(sym, candles, fund_map.get(sym, {}))
                        if pick:
                            all_picks.append(pick)

            all_picks.sort(key=lambda x: x["score"], reverse=True)

            momentum = _build_momentum_package(all_picks)
            swing = _build_swing_package(all_picks)
            oversold = _build_oversold_package(all_picks)

            bull = sum(1 for p in all_picks if p["verdict"] in ("Strong Buy", "Buy"))
            bear = sum(1 for p in all_picks if p["verdict"] in ("Sell", "Strong Sell"))
            neut = len(all_picks) - bull - bear
            total_so_far = len(all_picks) or 1

            with _scan_lock:
                _scan_cache["all_picks"] = list(all_picks)
                _scan_cache["packages"] = {
                    "momentum": momentum,
                    "swing": swing,
                    "oversold": oversold,
                }
                _scan_cache["market_mood"] = {
                    "bullish": round(bull / total_so_far * 100),
                    "neutral": round(neut / total_so_far * 100),
                    "bearish": round(bear / total_so_far * 100),
                }
                _scan_cache["scanned"] = min(batch_start + BATCH, total)
                _scan_cache["updated_at"] = time.time()

        with _scan_lock:
            _scan_cache["complete"] = True
            _scan_cache["updated_at"] = time.time()

        logger.info(
            "Trading advisor scan complete: %d picks, momentum=%d swing=%d oversold=%d",
            len(all_picks),
            len(_scan_cache["packages"].get("momentum", {}).get("picks", [])),
            len(_scan_cache["packages"].get("swing", {}).get("picks", [])),
            len(_scan_cache["packages"].get("oversold", {}).get("picks", [])),
        )
    except Exception:
        logger.exception("Trading advisor background scan failed")
        with _scan_lock:
            _scan_cache["complete"] = True
    finally:
        _scan_running = False


def _ensure_scan_running():
    global _scan_running
    with _scan_lock:
        if _scan_running:
            return
        age = time.time() - _scan_cache["updated_at"]
        if _scan_cache["complete"] and age < SCAN_CACHE_TTL:
            return
        _scan_running = True
        _scan_cache["complete"] = False
        _scan_cache["scanned"] = 0

    t = threading.Thread(target=_run_background_scan, daemon=True)
    t.start()


def start_trading_advisor():
    """Launch the auto-scanning daemon. Called at app startup."""
    from src.services.market_data import _warm_done

    def _loop():
        logger.info("Trading advisor: waiting for cache warmer...")
        _warm_done.wait()
        logger.info("Trading advisor: cache warm, starting first scan")
        while True:
            _ensure_scan_running()
            for _ in range(600):
                with _scan_lock:
                    if _scan_cache["complete"]:
                        break
                time.sleep(1)
            logger.info(
                "Trading advisor: scan ready (%d picks). Next refresh in %ds",
                len(_scan_cache["all_picks"]), SCAN_CACHE_TTL,
            )
            time.sleep(SCAN_CACHE_TTL)

    t = threading.Thread(target=_loop, daemon=True, name="trading-advisor")
    t.start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_dashboard() -> dict:
    """Return current scan results for the dashboard."""
    _ensure_scan_running()

    with _scan_lock:
        return {
            "packages": _scan_cache["packages"],
            "all_picks": _scan_cache["all_picks"][:30],
            "market_mood": _scan_cache["market_mood"],
            "progress": {
                "scanned": _scan_cache["scanned"],
                "total": _scan_cache["total"],
                "complete": _scan_cache["complete"],
            },
        }


def get_single_analysis(symbol: str) -> Optional[dict]:
    """Deep analysis for a single stock with full indicator arrays."""
    to_ts = int(time.time())
    from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400

    candles = dp.get_candles(symbol, "D", from_ts, to_ts)
    if not candles or not candles.get("c") or len(candles["c"]) < 50:
        return None

    closes = candles["c"]
    highs = candles.get("h", closes)
    lows = candles.get("l", closes)
    volumes = candles.get("v", [0] * len(closes))
    timestamps = candles.get("t", [])
    dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in timestamps]

    info = fetch_stock_info(symbol) or {}

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

    comp = ta.composite_score(
        rsi_vals, macd_data, closes, sma50, sma200,
        boll["pct_b"], stoch, obv_vals,
    )

    current = closes[-1]
    last_atr = ta._last_valid(atr_vals)
    boll_lower = ta._last_valid(boll["lower"])
    boll_upper = ta._last_valid(boll["upper"])

    entry = current
    if boll_lower and current > boll_lower:
        entry = round((current + boll_lower) / 2, 2)
    target = round(boll_upper, 2) if boll_upper else round(current * 1.08, 2)
    stop = round(entry - 2 * last_atr, 2) if last_atr else round(entry * 0.95, 2)
    if stop >= entry:
        stop = round(entry * 0.95, 2)
    rr = round((target - entry) / (entry - stop), 2) if entry > stop else 0

    reasoning_parts = [s["detail"] for s in comp["signals"] if s["score"] != 0]
    reasoning = ". ".join(reasoning_parts[:5]) + "." if reasoning_parts else "Insufficient data."

    return {
        "symbol": symbol,
        "name": info.get("name", symbol),
        "sector": info.get("sector", "N/A"),
        "dates": dates,
        "price": {"close": closes, "high": highs, "low": lows, "volume": volumes},
        "indicators": {
            "sma_50": sma50, "sma_200": sma200,
            "ema_12": ema12, "ema_26": ema26,
            "rsi": rsi_vals,
            "macd": macd_data,
            "bollinger": boll,
            "stochastic": stoch,
            "obv": obv_vals,
            "atr": atr_vals,
        },
        "action": {
            "verdict": comp["verdict"],
            "score": comp["score"],
            "confidence": comp["confidence"],
            "entry": round(entry, 2),
            "target": round(target, 2),
            "stop_loss": round(stop, 2),
            "risk_reward": rr,
            "timeframe": "Short-term" if comp["raw_score"] > 1 else "Medium-term",
            "reasoning": reasoning,
            "signals": comp["signals"],
        },
    }
