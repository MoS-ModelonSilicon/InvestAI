"""
Smart Advisor -- AI Stock Simulator & Advisor.

Scans the full stock universe, scores each stock with a blend of technical
and fundamental analysis, ranks winners, builds optimized portfolio packages,
provides buy/sell timing, backtests, and generates a plain-English report.
"""

import logging
import math
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

PERIOD_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}

# We need ~200 trading days for SMA 200 to be valid, so always fetch at
# least 14 months of daily candles.
CANDLE_LOOKBACK_DAYS = 420


# ---------------------------------------------------------------------------
# Step 1: Fetch + compute technical indicators for a single stock
# ---------------------------------------------------------------------------

def _analyze_single(symbol: str, candle_data: Optional[dict]) -> Optional[dict]:
    """Run full technical analysis on one symbol's candle data."""
    if not candle_data or not candle_data.get("c") or len(candle_data["c"]) < 50:
        return None

    closes = candle_data["c"]
    highs = candle_data.get("h", closes)
    lows = candle_data.get("l", closes)
    volumes = candle_data.get("v", [0] * len(closes))
    timestamps = candle_data.get("t", [])

    dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in timestamps] if timestamps else []

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

    last_atr = ta._last_valid(atr_vals)
    last_boll_lower = ta._last_valid(boll["lower"])
    last_boll_upper = ta._last_valid(boll["upper"])
    current_price = closes[-1]

    entry = current_price
    if last_boll_lower and current_price > last_boll_lower:
        entry = round((current_price + last_boll_lower) / 2, 2)
    target = round(last_boll_upper, 2) if last_boll_upper else round(current_price * 1.08, 2)
    stop_loss = round(entry - 2 * last_atr, 2) if last_atr else round(entry * 0.95, 2)
    if stop_loss >= entry:
        stop_loss = round(entry * 0.95, 2)

    rr = round((target - entry) / (entry - stop_loss), 2) if entry > stop_loss else 0

    return {
        "symbol": symbol,
        "dates": dates,
        "current_price": current_price,
        "technical_score": comp["score"],
        "verdict": comp["verdict"],
        "confidence": comp["confidence"],
        "raw_score": comp["raw_score"],
        "signals": comp["signals"],
        "entry_price": round(entry, 2),
        "target_price": round(target, 2),
        "stop_loss": round(stop_loss, 2),
        "risk_reward": rr,
        "rsi": ta._last_valid(rsi_vals),
        "macd_signal": _macd_label(macd_data),
        "sma_trend": _sma_label(closes, sma50, sma200),
        "indicators": {
            "sma_50": sma50, "sma_200": sma200,
            "ema_12": ema12, "ema_26": ema26,
            "rsi": rsi_vals,
            "macd": macd_data,
            "bollinger": boll,
            "stochastic": stoch,
            "atr": atr_vals,
            "obv": obv_vals,
        },
        "price_data": {
            "dates": dates, "close": closes, "high": highs,
            "low": lows, "volume": volumes,
        },
    }


def _macd_label(macd_data: dict) -> str:
    h = ta._last_valid(macd_data["histogram"])
    if h is None:
        return "N/A"
    return "Bullish" if h > 0 else "Bearish"


def _sma_label(closes, sma50, sma200) -> str:
    p = closes[-1] if closes else None
    s50 = ta._last_valid(sma50)
    s200 = ta._last_valid(sma200)
    if p is None or s50 is None:
        return "N/A"
    if s200 is None:
        return "Above SMA 50" if p > s50 else "Below SMA 50"
    if p > s50 > s200:
        return "Above SMA 50 & 200"
    if p > s50:
        return "Above SMA 50, below 200"
    if p < s50 < s200:
        return "Below SMA 50 & 200"
    return "Below SMA 50"


# ---------------------------------------------------------------------------
# Step 2: Fundamental scoring (reuses cached market_data)
# ---------------------------------------------------------------------------

def _fundamental_score(info: dict) -> int:
    """Score 0-100 from cached fundamental data."""
    score = 0

    pe = info.get("pe_ratio")
    if pe is not None and 0 < pe < 15:
        score += 15
    elif pe is not None and pe < 25:
        score += 10
    elif pe is not None and pe < 35:
        score += 5

    rg = info.get("revenue_growth")
    if rg is not None:
        if rg >= 20:
            score += 15
        elif rg >= 10:
            score += 10
        elif rg >= 0:
            score += 5

    pm = info.get("profit_margin")
    if pm is not None:
        if pm >= 20:
            score += 15
        elif pm >= 10:
            score += 10
        elif pm > 0:
            score += 5

    div = info.get("dividend_yield")
    if div is not None and div > 2:
        score += 10
    elif div is not None and div > 0.5:
        score += 5

    rec = (info.get("recommendation") or "").lower().replace("_", " ")
    if rec in ("strong buy", "strongbuy"):
        score += 15
    elif rec == "buy":
        score += 10
    elif rec == "hold":
        score += 5

    roe = info.get("return_on_equity")
    if roe is not None and roe > 15:
        score += 10
    elif roe is not None and roe > 5:
        score += 5

    beta = info.get("beta")
    if beta is not None and 0.5 <= beta <= 1.3:
        score += 5

    yc = info.get("year_change")
    if yc is not None and yc > 20:
        score += 10
    elif yc is not None and yc > 5:
        score += 5

    return min(100, score)


def _momentum_score(info: dict) -> int:
    """Score 0-100 from price momentum."""
    score = 50
    yc = info.get("year_change")
    if yc is not None:
        if yc > 50:
            score += 40
        elif yc > 20:
            score += 25
        elif yc > 5:
            score += 10
        elif yc < -20:
            score -= 30
        elif yc < -5:
            score -= 15
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Step 3: Full scan + scoring
# ---------------------------------------------------------------------------

def scan_and_score(period: str = "1y") -> list[dict]:
    """Scan all stocks, compute TA + fundamental scores, return ranked list."""
    cache_key = f"advisor:scan:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    fundamentals = fetch_batch(ALL_UNIVERSE, cached_only=True)
    fund_map = {d["symbol"]: d for d in fundamentals if d.get("price", 0) > 0}

    fund_sorted = sorted(
        fund_map.values(),
        key=lambda d: _fundamental_score(d),
        reverse=True,
    )
    top_symbols = [d["symbol"] for d in fund_sorted[:80]]

    to_ts = int(time.time())
    from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400

    def _fetch_candles(sym):
        try:
            return sym, dp.get_candles(sym, "D", from_ts, to_ts)
        except Exception:
            return sym, None

    candle_map = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_candles, s): s for s in top_symbols}
        for fut in as_completed(futures):
            sym, data = fut.result()
            if data and data.get("c"):
                candle_map[sym] = data

    results = []
    for sym in top_symbols:
        candle_data = candle_map.get(sym)
        analysis = _analyze_single(sym, candle_data)
        if not analysis:
            continue

        info = fund_map.get(sym, {})
        f_score = _fundamental_score(info)
        m_score = _momentum_score(info)
        t_score = analysis["technical_score"]

        combined = round(t_score * 0.40 + f_score * 0.40 + m_score * 0.20)

        results.append({
            "rank": 0,
            "symbol": sym,
            "name": info.get("name", sym),
            "sector": info.get("sector", "N/A"),
            "price": analysis["current_price"],
            "score": combined,
            "technical_score": t_score,
            "fundamental_score": f_score,
            "momentum_score": m_score,
            "signal": analysis["verdict"],
            "confidence": analysis["confidence"],
            "rsi": analysis["rsi"],
            "macd_signal": analysis["macd_signal"],
            "sma_trend": analysis["sma_trend"],
            "entry_price": analysis["entry_price"],
            "target_price": analysis["target_price"],
            "stop_loss": analysis["stop_loss"],
            "risk_reward": analysis["risk_reward"],
            "beta": info.get("beta"),
            "dividend_yield": info.get("dividend_yield"),
            "pe_ratio": info.get("pe_ratio"),
            "market_cap": info.get("market_cap"),
            "market_cap_fmt": format_market_cap(info.get("market_cap", 0)),
            "signals": analysis["signals"],
            "reasoning": _build_reasoning(analysis, info),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    _set_cache(cache_key, results)
    return results


def _build_reasoning(analysis: dict, info: dict) -> str:
    """Generate plain-English reasoning for a pick."""
    parts = []
    for sig in analysis.get("signals", []):
        if sig["score"] != 0:
            parts.append(sig["detail"])

    pe = info.get("pe_ratio")
    if pe is not None:
        if pe < 15:
            parts.append(f"Attractively valued with P/E of {pe:.1f}")
        elif pe > 40:
            parts.append(f"Premium valuation with P/E of {pe:.1f}")

    rg = info.get("revenue_growth")
    if rg is not None and rg > 15:
        parts.append(f"Strong revenue growth at {rg:.0f}%")

    return ". ".join(parts[:5]) + "." if parts else "Insufficient data for analysis."


# ---------------------------------------------------------------------------
# Step 4: Build portfolio packages
# ---------------------------------------------------------------------------

def build_portfolios(rankings: list[dict], amount: float = 10000) -> dict:
    """Build 3 portfolio tiers from the ranked stock list."""
    buyable = [r for r in rankings if r["signal"] in ("Strong Buy", "Buy")]
    if len(buyable) < 5:
        buyable = rankings[:20]

    conservative_pool = [
        r for r in buyable
        if (r.get("beta") or 1.0) < 1.3 and (r.get("dividend_yield") or 0) >= 0
    ][:12]
    if len(conservative_pool) < 4:
        conservative_pool = buyable[:8]

    balanced_pool = buyable[:15]

    aggressive_pool = sorted(
        buyable,
        key=lambda x: x["technical_score"],
        reverse=True,
    )[:12]

    def _build_one(pool: list[dict], name: str, risk: str, max_holdings: int = 10) -> dict:
        if not pool:
            return {"name": name, "risk": risk, "holdings": [], "allocation": []}

        seen_sectors = {}
        selected = []
        for r in pool:
            sec = r["sector"]
            if seen_sectors.get(sec, 0) >= 3:
                continue
            seen_sectors[sec] = seen_sectors.get(sec, 0) + 1
            selected.append(r)
            if len(selected) >= max_holdings:
                break

        if not selected:
            selected = pool[:max_holdings]

        total_score = sum(s["score"] for s in selected) or 1
        holdings = []
        for s in selected:
            pct = round(s["score"] / total_score * 100, 1)
            invested = round(amount * pct / 100, 2)
            shares = round(invested / s["price"], 4) if s["price"] > 0 else 0
            holdings.append({
                "symbol": s["symbol"],
                "name": s["name"],
                "sector": s["sector"],
                "allocation_pct": pct,
                "shares": shares,
                "buy_price": s["price"],
                "invested": invested,
                "entry_price": s["entry_price"],
                "target_price": s["target_price"],
                "stop_loss": s["stop_loss"],
                "risk_reward": s["risk_reward"],
                "score": s["score"],
                "signal": s["signal"],
            })

        return {"name": name, "risk": risk, "holdings": holdings}

    return {
        "conservative": _build_one(conservative_pool, "Shield Portfolio", "Low", 8),
        "balanced": _build_one(balanced_pool, "Balanced Growth", "Medium", 10),
        "aggressive": _build_one(aggressive_pool, "Alpha Hunter", "High", 10),
    }


# ---------------------------------------------------------------------------
# Step 5: Backtest a portfolio
# ---------------------------------------------------------------------------

def backtest_portfolio(holdings: list[dict], period: str = "1y") -> dict:
    """Day-by-day backtest of a portfolio against S&P 500.

    Simulates buying each holding at the START of the period using
    historical prices, then tracks portfolio value forward.
    """
    days = PERIOD_DAYS.get(period, 365)
    to_ts = int(time.time())
    from_ts = to_ts - days * 86400

    bench_candles = dp.get_candles("SPY", "D", from_ts, to_ts)
    if not bench_candles or not bench_candles.get("c") or len(bench_candles["c"]) < 5:
        return {"error": "Could not fetch benchmark data"}

    bench_closes = bench_candles["c"]
    bench_dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in bench_candles["t"]]
    bench_start = bench_closes[0]

    total_invested = sum(h["invested"] for h in holdings)
    if total_invested <= 0:
        return {"error": "No capital allocated"}

    symbol_aligned: dict[str, list] = {}
    for h in holdings:
        sym = h["symbol"]
        if sym in symbol_aligned:
            continue
        candles = dp.get_candles(sym, "D", from_ts, to_ts)
        if candles and candles.get("c"):
            lookup = dict(zip(
                [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in candles["t"]],
                candles["c"],
            ))
            aligned = []
            last_known = None
            for d in bench_dates:
                if d in lookup:
                    last_known = lookup[d]
                aligned.append(last_known)
            symbol_aligned[sym] = aligned

    bt_holdings = []
    cash = 0.0
    for h in holdings:
        prices = symbol_aligned.get(h["symbol"])
        if not prices:
            cash += h["invested"]
            continue
        start_price = None
        for p in prices:
            if p is not None:
                start_price = p
                break
        if start_price is None or start_price <= 0:
            cash += h["invested"]
            continue
        shares = h["invested"] / start_price
        bt_holdings.append({"symbol": h["symbol"], "shares": shares, "invested": h["invested"]})

    portfolio_values = []
    for i, date_str in enumerate(bench_dates):
        day_val = cash
        for bh in bt_holdings:
            prices = symbol_aligned.get(bh["symbol"])
            if prices and prices[i] is not None:
                day_val += bh["shares"] * prices[i]
            else:
                day_val += bh["invested"]
        portfolio_values.append(round(day_val, 2))

    bench_values = [round(total_invested * (p / bench_start), 2) for p in bench_closes]

    final = portfolio_values[-1] if portfolio_values else total_invested
    total_return_pct = round((final - total_invested) / total_invested * 100, 2)
    bench_final = bench_values[-1] if bench_values else total_invested
    bench_return_pct = round((bench_final - total_invested) / total_invested * 100, 2)

    peak = portfolio_values[0] if portfolio_values else total_invested
    max_dd = 0
    for v in portfolio_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    daily_returns = []
    for i in range(1, len(portfolio_values)):
        prev = portfolio_values[i - 1]
        if prev > 0:
            daily_returns.append((portfolio_values[i] - prev) / prev * 100)

    if len(daily_returns) > 1:
        avg_r = sum(daily_returns) / len(daily_returns)
        std_r = math.sqrt(sum((r - avg_r) ** 2 for r in daily_returns) / (len(daily_returns) - 1))
        annual_r = avg_r * 252
        annual_v = std_r * math.sqrt(252)
        sharpe = round((annual_r - 4.5) / annual_v, 2) if annual_v > 0 else 0
    else:
        sharpe = 0

    return {
        "dates": bench_dates,
        "portfolio": portfolio_values,
        "benchmark": bench_values,
        "stats": {
            "total_return_pct": total_return_pct,
            "bench_return_pct": bench_return_pct,
            "alpha": round(total_return_pct - bench_return_pct, 2),
            "sharpe": sharpe,
            "max_drawdown": round(max_dd, 2),
            "final_value": final,
            "invested": total_invested,
        },
    }


# ---------------------------------------------------------------------------
# Step 6: Generate advisor report
# ---------------------------------------------------------------------------

def generate_report(rankings: list[dict], portfolios: dict) -> dict:
    """Build the plain-English advisor report."""
    total = len(rankings)
    bullish = sum(1 for r in rankings if r["signal"] in ("Strong Buy", "Buy"))
    bearish = sum(1 for r in rankings if r["signal"] in ("Sell", "Strong Sell"))
    neutral = total - bullish - bearish

    bull_pct = round(bullish / total * 100) if total else 0
    bear_pct = round(bearish / total * 100) if total else 0

    if bull_pct >= 60:
        regime = "Bullish Trend"
    elif bear_pct >= 60:
        regime = "Bearish Trend"
    elif bull_pct >= 40:
        regime = "Cautiously Bullish"
    else:
        regime = "Mixed / Choppy"

    summary = (
        f"Based on scanning {total} stocks, {bull_pct}% show bullish signals, "
        f"{bear_pct}% bearish, and {100 - bull_pct - bear_pct}% neutral. "
        f"Market regime: {regime}."
    )

    top_actions = []
    for r in rankings[:5]:
        if r["signal"] in ("Strong Buy", "Buy"):
            top_actions.append(
                f"Consider buying {r['symbol']} ({r['name']}) near ${r['entry_price']:.2f} "
                f"with target ${r['target_price']:.2f} and stop-loss at ${r['stop_loss']:.2f} "
                f"(R/R {r['risk_reward']:.1f}x)"
            )
        elif r["signal"] == "Neutral":
            top_actions.append(
                f"Watch {r['symbol']} ({r['name']}) -- score {r['score']}, "
                f"entry zone near ${r['entry_price']:.2f}, target ${r['target_price']:.2f}"
            )

    overbought = [
        r for r in rankings
        if r.get("rsi") and r["rsi"] > 70
    ][:3]
    for r in overbought:
        top_actions.append(
            f"Take profits on {r['symbol']} -- RSI overbought at {r['rsi']:.0f}"
        )

    risk_warnings = []
    sectors = {}
    for r in rankings[:20]:
        sec = r["sector"]
        sectors[sec] = sectors.get(sec, 0) + 1
    dominant = max(sectors, key=sectors.get) if sectors else None
    if dominant and sectors[dominant] >= 6:
        risk_warnings.append(
            f"{dominant} sector is heavily represented in top picks ({sectors[dominant]}/20) "
            f"-- consider diversification"
        )

    if bull_pct > 75:
        risk_warnings.append(
            "Market appears extended with 75%+ bullish signals -- potential for mean reversion"
        )

    if not risk_warnings:
        risk_warnings.append("No major risk concentration detected in current picks")

    return {
        "summary": summary,
        "market_regime": regime,
        "market_mood": {"bullish": bull_pct, "neutral": 100 - bull_pct - bear_pct, "bearish": bear_pct},
        "top_actions": top_actions,
        "risk_warnings": risk_warnings,
        "disclaimer": "This analysis is for educational purposes only. Not financial advice. Always do your own due diligence.",
    }


# ---------------------------------------------------------------------------
# Public API: full analysis
# ---------------------------------------------------------------------------

def run_full_analysis(amount: float = 10000, risk: str = "balanced",
                      period: str = "1y") -> dict:
    """Run the complete advisor pipeline. Cached for 15 min."""
    cache_key = f"advisor:full:{amount}:{risk}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    rankings = scan_and_score(period)
    portfolios = build_portfolios(rankings, amount)

    selected_key = risk if risk in portfolios else "balanced"
    selected_portfolio = portfolios[selected_key]

    bt = {}
    if selected_portfolio.get("holdings"):
        bt = backtest_portfolio(selected_portfolio["holdings"], period)

    report = generate_report(rankings, portfolios)

    result = {
        "rankings": rankings[:30],
        "portfolios": portfolios,
        "backtest": bt,
        "selected_risk": selected_key,
        "advisor_report": report,
    }

    _set_cache(cache_key, result)
    return result


def analyze_single_stock(symbol: str) -> Optional[dict]:
    """Deep analysis of a single stock with full indicator arrays."""
    to_ts = int(time.time())
    from_ts = to_ts - CANDLE_LOOKBACK_DAYS * 86400

    candle_data = dp.get_candles(symbol, "D", from_ts, to_ts)
    analysis = _analyze_single(symbol, candle_data)
    if not analysis:
        return None

    info = fetch_stock_info(symbol) or {}
    analysis["name"] = info.get("name", symbol)
    analysis["sector"] = info.get("sector", "N/A")
    analysis["fundamental_score"] = _fundamental_score(info)
    analysis["momentum_score"] = _momentum_score(info)
    analysis["combined_score"] = round(
        analysis["technical_score"] * 0.40
        + analysis["fundamental_score"] * 0.40
        + analysis["momentum_score"] * 0.20
    )
    analysis["reasoning"] = _build_reasoning(analysis, info)
    return analysis
