from fastapi import APIRouter, HTTPException

from src.services.trading_advisor import get_dashboard, get_single_analysis

router = APIRouter(prefix="/api/trading", tags=["trading-advisor"])


@router.get("")
def trading_dashboard():
    """Return current scan results: packages, picks, market mood, progress."""
    return get_dashboard()


@router.get("/{symbol}")
def trading_stock_analysis(symbol: str):
    """Deep technical analysis for a single stock with full indicator arrays."""
    result = get_single_analysis(symbol.upper())
    if not result:
        raise HTTPException(404, f"Could not analyze {symbol} — insufficient price data")
    return result
