from fastapi import APIRouter, HTTPException

from src.services.smart_advisor import run_full_analysis, analyze_single_stock
from src.services.company_dna import get_company_dna

router = APIRouter(prefix="/api/advisor", tags=["smart-advisor"])


@router.get("/analyze")
def advisor_analyze(amount: float = 10000, risk: str = "balanced",
                    period: str = "1y"):
    """Run full advisor analysis: scan, score, build portfolios, backtest."""
    if risk not in ("conservative", "balanced", "aggressive"):
        risk = "balanced"
    if period not in ("1m", "3m", "6m", "1y"):
        period = "1y"
    amount = max(100, min(amount, 10_000_000))

    result = run_full_analysis(amount, risk, period, compute_if_missing=False)
    if not result or not result.get("rankings"):
        raise HTTPException(503, "Advisor analysis unavailable -- market data may still be loading. Try again in a minute.")
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
