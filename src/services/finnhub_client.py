"""Thin wrapper around the Finnhub REST API (free tier, 60 calls/min)."""

import logging
import os
import threading
import time
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("FINNHUB_API_KEY", "")
BASE_URL = "https://finnhub.io/api/v1"

_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
PROXIES = {
    "http": "http://proxy-dmz.intel.com:911",
    "https": "http://proxy-dmz.intel.com:912",
} if _USE_PROXY else None

_call_times: list[float] = []
_rate_lock = threading.Lock()
_RATE_LIMIT = 55


def _rate_limit():
    with _rate_lock:
        now = time.time()
        _call_times[:] = [t for t in _call_times if now - t < 60]
        if len(_call_times) >= _RATE_LIMIT:
            sleep_time = 60 - (now - _call_times[0]) + 0.5
            if sleep_time > 0:
                time.sleep(sleep_time)
        _call_times.append(time.time())


def _get(endpoint: str, params: dict | None = None) -> dict | list | None:
    if not API_KEY:
        logger.warning("FINNHUB_API_KEY not set")
        return None
    _rate_limit()
    p = params or {}
    p["token"] = API_KEY
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", params=p, timeout=15, proxies=PROXIES)
        if resp.status_code == 403:
            return None
        if resp.status_code == 429:
            logger.warning("Finnhub rate limit hit, sleeping 5s")
            time.sleep(5)
            return _get(endpoint, params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Finnhub %s error: %s", endpoint, e)
        return None


def get_quote(symbol: str) -> dict | None:
    """Real-time quote: c=current, d=change, dp=change%, h=high, l=low, o=open, pc=prevClose."""
    data = _get("/quote", {"symbol": symbol})
    if data and data.get("c", 0) > 0:
        return data
    return None


def get_profile(symbol: str) -> dict | None:
    """Company profile: name, finnhubIndustry, marketCapitalization (in millions), logo, etc."""
    data = _get("/stock/profile2", {"symbol": symbol})
    if data and data.get("name"):
        return data
    return None


def get_metrics(symbol: str) -> dict | None:
    """Basic financials: PE, beta, 52wk high/low, dividend yield, margins, etc."""
    data = _get("/stock/metric", {"symbol": symbol, "metric": "all"})
    if data and data.get("metric"):
        return data["metric"]
    return None


def get_candles(symbol: str, resolution: str, from_ts: int, to_ts: int) -> dict | None:
    """OHLCV candles. resolution: 1, 5, 15, 30, 60, D, W, M."""
    data = _get("/stock/candle", {
        "symbol": symbol,
        "resolution": resolution,
        "from": from_ts,
        "to": to_ts,
    })
    if data and data.get("s") == "ok":
        return data
    return None


def get_company_news(symbol: str, days_back: int = 7) -> list[dict]:
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    data = _get("/company-news", {"symbol": symbol, "from": from_date, "to": to_date})
    return data if isinstance(data, list) else []


def get_earnings_calendar(from_date: str, to_date: str) -> list[dict]:
    data = _get("/calendar/earnings", {"from": from_date, "to": to_date})
    if data and "earningsCalendar" in data:
        return data["earningsCalendar"]
    return []
