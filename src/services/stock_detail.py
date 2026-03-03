from typing import Optional
import yfinance as yf
from src.services.market_data import fetch_stock_info, _get_cached, _set_cache


def get_stock_detail(symbol: str) -> Optional[dict]:
    """Full detail for a single stock, pulling from cache or yfinance."""
    info = fetch_stock_info(symbol)
    if not info:
        return None
    return info


def get_price_history(symbol: str, period: str = "1y", interval: str = "1d") -> dict:
    """Return OHLCV history for charting."""
    cache_key = f"history:{symbol}:{period}:{interval}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []}

        result = {
            "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
            "open": [round(v, 2) for v in hist["Open"].tolist()],
            "high": [round(v, 2) for v in hist["High"].tolist()],
            "low": [round(v, 2) for v in hist["Low"].tolist()],
            "close": [round(v, 2) for v in hist["Close"].tolist()],
            "volume": [int(v) for v in hist["Volume"].tolist()],
        }
        _set_cache(cache_key, result)
        return result
    except Exception:
        return {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
