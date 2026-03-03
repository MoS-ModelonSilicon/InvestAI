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
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from src.services.market_data import (
    fetch_batch, fetch_stock_info, STOCK_UNIVERSE, format_market_cap,
)

logger = logging.getLogger(__name__)

EXCLUDED_SECTORS = {"Financial Services", "Real Estate"}

PE_MAX = 15
DE_MAX = 100          # Yahoo reports D/E as percentage
CURRENT_RATIO_MIN = 1.5
DILUTION_THRESHOLD = 3.0  # placeholder for future use

CRITERIA = [
    ("pe",             "P/E ≤ 15"),
    ("debt_to_equity", "D/E ≤ 1.0"),
    ("current_ratio",  "Current Ratio ≥ 1.5"),
    ("profit_margin",  "Positive Margin"),
    ("roe",            "Positive ROE"),
    ("fcf",            "Positive FCF"),
]


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
    """Composite quality score 0-100 based on fundamentals."""
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
    """
    Graham's intrinsic value formula: V = EPS × (8.5 + 2g)
    where g = expected growth rate (%).
    MOS = (V - Price) / V × 100
    """
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
    return "Fail"


def _needs_metrics(d: dict) -> bool:
    """Check if cached data is missing key financial metrics."""
    return (d.get("pe_ratio") is None
            and d.get("debt_to_equity") is None
            and d.get("return_on_equity") is None)


def _fetch_stocks_with_metrics() -> list[dict]:
    """
    Get stock data with full metrics.
    Uses cache first, then re-fetches with full=True for stocks
    that were cached without metrics (from the quick warmer).
    """
    cached = fetch_batch(STOCK_UNIVERSE, cached_only=True)

    complete = []
    needs_refetch = []

    for d in cached:
        if d.get("asset_type") == "ETF":
            continue
        if _needs_metrics(d):
            needs_refetch.append(d["symbol"])
        else:
            complete.append(d)

    if needs_refetch:
        logger.info("Value scanner: re-fetching %d stocks with full metrics", len(needs_refetch))
        import src.services.market_data as md

        for sym in needs_refetch:
            with md._cache_lock:
                md._cache.pop(f"info:{sym}", None)

        def _fetch_full(sym):
            try:
                return fetch_stock_info(sym, full=True)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(_fetch_full, sym): sym for sym in needs_refetch}
            for future in as_completed(futures):
                result = future.result()
                if result and result.get("price", 0) > 0:
                    complete.append(result)

    return complete


def scan_value_stocks(
    sector: Optional[str] = None,
    signal_filter: Optional[str] = None,
    sort_by: str = "score",
) -> dict:
    """
    Run the Graham-Buffett screen on all stocks.
    Returns candidates and rejected stocks with reasons.
    """
    all_data = _fetch_stocks_with_metrics()

    candidates = []
    rejected = []
    scanned = 0

    for d in all_data:
        if d.get("asset_type") == "ETF":
            continue

        stock_sector = d.get("sector", "N/A")
        if stock_sector in EXCLUDED_SECTORS:
            rejected.append({
                "symbol": d["symbol"],
                "name": d.get("name", d["symbol"]),
                "sector": stock_sector,
                "reasons": [f"Excluded sector: {stock_sector}"],
            })
            scanned += 1
            continue

        if sector and stock_sector.lower() != sector.lower():
            continue

        scanned += 1
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

        if signal in ("Strong Buy", "Buy", "Watch"):
            if signal_filter is None or signal == signal_filter:
                candidates.append(item)
        else:
            fail_reasons = [c["detail"] for c in checks if not c["passed"]]
            rejected.append({
                "symbol": d["symbol"],
                "name": d.get("name", d["symbol"]),
                "sector": stock_sector,
                "reasons": fail_reasons,
            })

    sort_keys = {
        "score": lambda x: x["quality"],
        "mos": lambda x: x["mos"] if x["mos"] is not None else -999,
        "pe": lambda x: x["pe_ratio"] if x["pe_ratio"] is not None else 999,
        "roe": lambda x: x["roe"] if x["roe"] is not None else -999,
        "fcf_yield": lambda x: x["fcf_yield"] if x["fcf_yield"] is not None else -999,
    }
    key_fn = sort_keys.get(sort_by, sort_keys["score"])
    reverse = sort_by != "pe"
    candidates.sort(key=key_fn, reverse=reverse)

    return {
        "candidates": candidates,
        "rejected": rejected,
        "stats": {
            "scanned": scanned,
            "candidates": len(candidates),
            "rejected": len(rejected),
        },
    }
