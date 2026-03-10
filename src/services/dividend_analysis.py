"""Dividend analysis service — A–F grading system for income investors.

Grades four dimensions:
  Safety      – payout ratio, debt-to-equity, FCF coverage
  Growth      – 5yr dividend CAGR (estimated from current data)
  Yield       – current yield vs sector average, vs historical
  Consistency – proxy from available data (years of consecutive increases)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.services.market_data import fetch_batch, get_cached_quotes

logger = logging.getLogger(__name__)

# ── Sector average dividend yields (approximate, for grading) ──
_SECTOR_AVG_YIELD: dict[str, float] = {
    "Technology": 0.8,
    "Healthcare": 1.5,
    "Financial Services": 2.5,
    "Financials": 2.5,
    "Energy": 3.5,
    "Utilities": 3.2,
    "Real Estate": 3.8,
    "Consumer Cyclical": 1.2,
    "Consumer Defensive": 2.2,
    "Industrials": 1.6,
    "Communication Services": 1.1,
    "Basic Materials": 2.0,
    "N/A": 2.0,
}

_DEFAULT_SECTOR_YIELD = 2.0


def _letter(score: float) -> str:
    """Convert 0-100 score to A–F letter."""
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _grade_safety(info: dict[str, Any]) -> dict[str, Any]:
    """Grade dividend safety from payout ratio, D/E, and FCF."""
    payout = info.get("payout_ratio")
    de = info.get("debt_to_equity")
    fcf = info.get("free_cash_flow")
    margin = info.get("net_profit_margin")

    score = 50.0  # start neutral
    details: list[str] = []

    if payout is not None:
        if payout < 0:
            score -= 20
            details.append(f"Negative payout ({payout:.0f}%) — earnings loss")
        elif payout <= 30:
            score += 30
            details.append(f"Low payout {payout:.0f}% — very safe")
        elif payout <= 50:
            score += 20
            details.append(f"Moderate payout {payout:.0f}% — healthy")
        elif payout <= 75:
            score += 5
            details.append(f"High payout {payout:.0f}% — watch closely")
        else:
            score -= 15
            details.append(f"Elevated payout {payout:.0f}% — risk of cut")
    else:
        details.append("Payout ratio unavailable")

    if de is not None:
        if de < 0.5:
            score += 15
            details.append(f"Low debt D/E={de:.1f}")
        elif de < 1.0:
            score += 5
        elif de > 2.0:
            score -= 10
            details.append(f"High debt D/E={de:.1f}")

    if margin is not None and margin > 0:
        score += 5
        details.append(f"Profitable margin {margin:.1f}%")
    elif margin is not None:
        score -= 10
        details.append("Negative margins")

    if fcf is not None:
        if fcf > 0:
            score += 10
            details.append("Positive FCF")
        else:
            score -= 10
            details.append("Negative FCF")

    score = max(0, min(100, score))
    return {"score": round(score), "grade": _letter(score), "details": details}


def _grade_growth(info: dict[str, Any]) -> dict[str, Any]:
    """Grade dividend growth from revenue/earnings growth as proxy."""
    rev_growth = info.get("revenue_growth")
    eps_growth = info.get("eps_growth")
    div_yield = info.get("dividend_yield")

    score = 50.0
    details: list[str] = []

    if rev_growth is not None:
        if rev_growth > 15:
            score += 20
            details.append(f"Strong revenue growth {rev_growth:.1f}%")
        elif rev_growth > 5:
            score += 10
            details.append(f"Moderate revenue growth {rev_growth:.1f}%")
        elif rev_growth > 0:
            score += 3
        else:
            score -= 10
            details.append(f"Revenue declining {rev_growth:.1f}%")

    if eps_growth is not None:
        if eps_growth > 15:
            score += 15
            details.append(f"Strong EPS growth {eps_growth:.1f}%")
        elif eps_growth > 5:
            score += 8
            details.append(f"Solid EPS growth {eps_growth:.1f}%")
        elif eps_growth > 0:
            score += 3
        else:
            score -= 10
            details.append(f"EPS declining {eps_growth:.1f}%")

    if div_yield is not None and div_yield > 0:
        # Companies paying dividends with growth are better
        if div_yield > 3:
            score += 5
        details.append(f"Current yield {div_yield:.2f}%")
    else:
        score -= 10
        details.append("No dividend currently paid")

    score = max(0, min(100, score))
    return {"score": round(score), "grade": _letter(score), "details": details}


def _grade_yield(info: dict[str, Any]) -> dict[str, Any]:
    """Grade yield vs sector average and historical context."""
    div_yield = info.get("dividend_yield")
    sector = info.get("sector", "N/A")
    five_yr_avg = info.get("five_year_avg_yield")

    score = 50.0
    details: list[str] = []
    sector_avg = _SECTOR_AVG_YIELD.get(sector, _DEFAULT_SECTOR_YIELD)

    if div_yield is None or div_yield <= 0:
        return {
            "score": 0,
            "grade": "F",
            "details": ["No dividend yield"],
        }

    # vs sector average
    ratio = div_yield / sector_avg if sector_avg > 0 else 1.0
    if ratio >= 1.5:
        score += 25
        details.append(f"Yield {div_yield:.2f}% is {ratio:.1f}× sector avg ({sector_avg:.1f}%)")
    elif ratio >= 1.0:
        score += 15
        details.append(f"Yield {div_yield:.2f}% above sector avg ({sector_avg:.1f}%)")
    elif ratio >= 0.7:
        score += 5
        details.append(f"Yield {div_yield:.2f}% near sector avg ({sector_avg:.1f}%)")
    else:
        score -= 5
        details.append(f"Yield {div_yield:.2f}% below sector avg ({sector_avg:.1f}%)")

    # vs 5yr historical
    if five_yr_avg is not None and five_yr_avg > 0:
        hist_ratio = div_yield / five_yr_avg
        if hist_ratio >= 1.2:
            score += 15
            details.append(f"Above 5yr avg ({five_yr_avg:.2f}%) — attractive entry")
        elif hist_ratio >= 0.9:
            score += 5
            details.append(f"Near 5yr avg ({five_yr_avg:.2f}%)")
        else:
            score -= 5
            details.append(f"Below 5yr avg ({five_yr_avg:.2f}%)")

    # Absolute yield bonus
    if div_yield >= 4:
        score += 10
        details.append("High absolute yield ≥4%")
    elif div_yield >= 2:
        score += 5

    score = max(0, min(100, score))
    return {"score": round(score), "grade": _letter(score), "details": details}


def _grade_consistency(info: dict[str, Any]) -> dict[str, Any]:
    """Grade dividend consistency from available proxies."""
    div_yield = info.get("dividend_yield")
    payout = info.get("payout_ratio")
    margin = info.get("net_profit_margin")
    roe = info.get("roe")

    score = 50.0
    details: list[str] = []

    if div_yield is None or div_yield <= 0:
        return {
            "score": 0,
            "grade": "F",
            "details": ["No dividend — cannot assess consistency"],
        }

    # Stable payout ratio suggests consistency
    if payout is not None:
        if 20 <= payout <= 60:
            score += 20
            details.append(f"Sustainable payout range ({payout:.0f}%)")
        elif 10 <= payout <= 75:
            score += 10
            details.append(f"Acceptable payout ({payout:.0f}%)")
        elif payout > 100:
            score -= 15
            details.append(f"Payout exceeds earnings ({payout:.0f}%) — cut risk")

    # Profitability supports consistency
    if margin is not None and margin > 10:
        score += 10
        details.append(f"Strong margins ({margin:.1f}%) support payments")
    elif margin is not None and margin > 0:
        score += 5

    if roe is not None and roe > 10:
        score += 10
        details.append(f"Solid ROE ({roe:.1f}%)")
    elif roe is not None and roe > 0:
        score += 5

    # Higher yield with stable payout = likely long track record
    if div_yield >= 2 and payout is not None and payout <= 60:
        score += 10
        details.append("Good yield + moderate payout = likely consistent")

    score = max(0, min(100, score))
    return {"score": round(score), "grade": _letter(score), "details": details}


def _overall_grade(
    safety: dict[str, Any],
    growth: dict[str, Any],
    yld: dict[str, Any],
    consistency: dict[str, Any],
) -> dict[str, Any]:
    """Weighted composite grade: Safety 35%, Growth 20%, Yield 25%, Consistency 20%."""
    composite = safety["score"] * 0.35 + growth["score"] * 0.20 + yld["score"] * 0.25 + consistency["score"] * 0.20
    composite = round(composite)
    return {"score": composite, "grade": _letter(composite)}


def analyze_dividend(symbol: str) -> Optional[dict[str, Any]]:
    """Produce full dividend grade report for a single symbol."""
    infos = fetch_batch([symbol], cached_only=True, include_stale=True)
    info: Optional[dict[str, Any]] = None
    for item in infos:
        if item.get("symbol", "").upper() == symbol.upper():
            info = item
            break
    if not info:
        info = infos[0] if infos else None
    if not info or not isinstance(info, dict):
        return None

    quotes = get_cached_quotes([symbol])
    quote = quotes.get(symbol, {})

    enriched: dict[str, Any] = {
        "symbol": symbol,
        "name": info.get("name", symbol),
        "sector": info.get("sector", "N/A"),
        "price": info.get("price") or quote.get("c"),
        "dividend_yield": info.get("dividend_yield"),
        "payout_ratio": info.get("payout_ratio"),
        "debt_to_equity": info.get("debt_to_equity"),
        "free_cash_flow": info.get("free_cash_flow"),
        "net_profit_margin": info.get("net_profit_margin"),
        "revenue_growth": info.get("revenue_growth"),
        "eps_growth": info.get("eps_growth"),
        "roe": info.get("roe"),
        "five_year_avg_yield": info.get("five_year_avg_yield"),
    }

    safety = _grade_safety(enriched)
    growth = _grade_growth(enriched)
    yld = _grade_yield(enriched)
    consistency = _grade_consistency(enriched)
    overall = _overall_grade(safety, growth, yld, consistency)

    return {
        "symbol": symbol,
        "name": enriched["name"],
        "sector": enriched["sector"],
        "price": enriched["price"],
        "dividend_yield": enriched["dividend_yield"],
        "overall": overall,
        "grades": {
            "safety": safety,
            "growth": growth,
            "yield": yld,
            "consistency": consistency,
        },
    }


def analyze_dividends_batch(symbols: list[str]) -> list[dict[str, Any]]:
    """Grade multiple symbols; returns list sorted by overall score desc."""
    results: list[dict[str, Any]] = []
    for sym in symbols:
        try:
            result = analyze_dividend(sym)
            if result and result.get("dividend_yield") and result["dividend_yield"] > 0:
                results.append(result)
        except Exception:
            logger.debug("dividend analysis failed for %s", sym, exc_info=True)
    results.sort(key=lambda r: r["overall"]["score"], reverse=True)
    return results


# ── Well-known dividend stocks for the default view ──
DIVIDEND_UNIVERSE: list[str] = [
    # Dividend Aristocrats / Kings
    "JNJ",
    "PG",
    "KO",
    "PEP",
    "MMM",
    "ABT",
    "ABBV",
    "T",
    "VZ",
    "XOM",
    "CVX",
    "IBM",
    "MCD",
    "WMT",
    "HD",
    "LOW",
    "CL",
    "GPC",
    "SWK",
    "EMR",
    # High-yield REITs
    "O",
    "VICI",
    "MPW",
    # Utility stalwarts
    "SO",
    "DUK",
    "NEE",
    "D",
    # Financial dividends
    "JPM",
    "BAC",
    "WFC",
    "BLK",
    # Tech dividends
    "MSFT",
    "AAPL",
    "AVGO",
    "TXN",
    "INTC",
    "CSCO",
]
