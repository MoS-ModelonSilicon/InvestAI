from fastapi import APIRouter, HTTPException

from src.services.smart_advisor import run_full_analysis, analyze_single_stock
from src.services.company_dna import get_company_dna
from src.services.market_data import _get_cached

router = APIRouter(prefix="/api/advisor", tags=["smart-advisor"])


@router.get("/debug")
def advisor_debug():
    """Show which advisor combos are cached (for diagnosing scheduler issues)."""
    PERIODS = ["1y", "6m", "3m", "1m"]
    RISKS = ["balanced", "conservative", "aggressive"]
    status: dict = {"scans": {}, "combos": {}}
    for p in PERIODS:
        val = _get_cached(f"advisor:scan:{p}")
        status["scans"][p] = len(val) if isinstance(val, list) else None
    for p in PERIODS:
        for r in RISKS:
            key = f"advisor:full:10000:{r}:{p}"
            val = _get_cached(key)
            has_rankings = bool(val.get("rankings")) if isinstance(val, dict) else False
            status["combos"][f"{r}/{p}"] = {
                "cached": isinstance(val, dict),
                "has_rankings": has_rankings,
            }
    return status


@router.get("/analyze")
def advisor_analyze(amount: float = 10000, risk: str = "balanced", period: str = "1y"):
    """Run full advisor analysis: scan, score, build portfolios, backtest."""
    if risk not in ("conservative", "balanced", "aggressive"):
        risk = "balanced"
    if period not in ("1m", "3m", "6m", "1y"):
        period = "1y"
    amount = max(100, min(amount, 10_000_000))

    result = run_full_analysis(amount, risk, period, compute_if_missing=False)
    if not result or not result.get("rankings"):
        raise HTTPException(
            503, "Advisor analysis unavailable -- market data may still be loading. Try again in a minute."
        )
    return result


@router.get("/stock/{symbol}")
def advisor_stock(symbol: str):
    """Deep technical + fundamental analysis for a single stock."""
    result = analyze_single_stock(symbol.upper())
    if not result:
        raise HTTPException(404, f"Could not analyze {symbol} -- insufficient price data")
    return result


@router.get("/company-dna/{symbol}")
def company_dna(symbol: str):
    """Buffett/Munger-style Company DNA: management, insiders, Berkshire Score."""
    result = get_company_dna(symbol.upper())
    if not result:
        raise HTTPException(404, f"Could not fetch company data for {symbol}")
    return result
