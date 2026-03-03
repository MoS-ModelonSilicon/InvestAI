from fastapi import APIRouter, HTTPException

from src.services.stock_detail import get_stock_detail, get_price_history
from src.services.news import get_ticker_news
from src.services.screener import _build_risk_analysis, _build_analyst_view, _compute_signal

router = APIRouter(prefix="/api/stock", tags=["stock-detail"])


@router.get("/{symbol}")
def stock_detail(symbol: str):
    info = get_stock_detail(symbol.upper())
    if not info:
        raise HTTPException(404, f"No data found for {symbol}")

    sig = _compute_signal(info)
    risk = _build_risk_analysis(info)
    analyst = _build_analyst_view(info)

    info["signal"] = sig["signal"]
    info["signal_reason"] = sig["reason"]
    info["risk_analysis"] = risk
    info["analyst_targets"] = analyst
    return info


@router.get("/{symbol}/history")
def stock_history(symbol: str, period: str = "1y", interval: str = "1d"):
    return get_price_history(symbol.upper(), period, interval)


@router.get("/{symbol}/news")
def stock_news(symbol: str):
    return get_ticker_news(symbol.upper())
