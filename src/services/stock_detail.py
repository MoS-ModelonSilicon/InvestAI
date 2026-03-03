import time
from datetime import datetime
from typing import Optional

from src.services import data_provider as dp
from src.services.market_data import fetch_stock_info, _get_cached, _set_cache


def get_stock_detail(symbol: str) -> Optional[dict]:
    """Full detail for a single stock, pulling from cache or Finnhub."""
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

    period_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = period_map.get(period, 365)
    resolution_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "1d": "D", "1wk": "W", "1mo": "M"}
    res = resolution_map.get(interval, "D")

    to_ts = int(time.time())
    from_ts = to_ts - days * 86400

    try:
        candles = dp.get_candles(symbol, res, from_ts, to_ts)
        if not candles or not candles.get("c"):
            return {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []}

        result = {
            "dates": [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in candles["t"]],
            "open": [round(v, 2) for v in candles["o"]],
            "high": [round(v, 2) for v in candles["h"]],
            "low": [round(v, 2) for v in candles["l"]],
            "close": [round(v, 2) for v in candles["c"]],
            "volume": [int(v) for v in candles["v"]],
        }
        _set_cache(cache_key, result)
        return result
    except Exception:
        return {"dates": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
