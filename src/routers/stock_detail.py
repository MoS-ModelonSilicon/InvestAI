from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException

from src.services.stock_detail import get_stock_detail, get_price_history
from src.services.news import get_ticker_news
from src.services.screener import _build_risk_analysis, _build_analyst_view, _compute_signal

router = APIRouter(prefix="/api/stock", tags=["stock-detail"])

_pool = ThreadPoolExecutor(max_workers=3)


def _compute_sma(closes: list, window: int = 50) -> list:
    """Compute Simple Moving Average server-side."""
    sma: list[float | None] = []
    for i in range(len(closes)):
        if i < window - 1:
            sma.append(None)
        else:
            avg = sum(closes[i - window + 1: i + 1]) / window
            sma.append(round(avg, 2))
    return sma


@router.get("/{symbol}/full")
def stock_full(symbol: str, period: str = "1y", interval: str = "1d"):
    """Combined endpoint: info + history (with SMA) + news in one round-trip."""
    sym = symbol.upper()
    info_future = _pool.submit(get_stock_detail, sym)
    history_future = _pool.submit(get_price_history, sym, period, interval)
    news_future = _pool.submit(get_ticker_news, sym)

    info = info_future.result(timeout=15)
    if not info:
        raise HTTPException(404, f"No data found for {symbol}")

    sig = _compute_signal(info)
    risk = _build_risk_analysis(info)
    analyst = _build_analyst_view(info)
    info["signal"] = sig["signal"]
    info["signal_reason"] = sig["reason"]
    info["risk_analysis"] = risk
    info["analyst_targets"] = analyst

    history = history_future.result(timeout=15)
    if history and history.get("close"):
        history["sma50"] = _compute_sma(history["close"], 50)

    news = news_future.result(timeout=15)

    return {"info": info, "history": history, "news": news or []}


@router.get("/{symbol}/history")
def stock_history(symbol: str, period: str = "1y", interval: str = "1d"):
    history = get_price_history(symbol.upper(), period, interval)
    # Add SMA 50 server-side
    if history and history.get("close"):
        history["sma50"] = _compute_sma(history["close"], 50)
    return history


@router.get("/{symbol}/news")
def stock_news(symbol: str):
    return get_ticker_news(symbol.upper())


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
