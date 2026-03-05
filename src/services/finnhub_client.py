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

if not API_KEY:
    logger.info("FINNHUB_API_KEY not set — Finnhub disabled, using Yahoo only")

_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
PROXIES = {
    "http": "http://proxy-dmz.intel.com:911",
    "https": "http://proxy-dmz.intel.com:912",
} if _USE_PROXY else None

_call_times: list[float] = []
_rate_lock = threading.Lock()
_RATE_LIMIT = 55


def _rate_limit():
    while True:
        with _rate_lock:
            now = time.time()
            _call_times[:] = [t for t in _call_times if now - t < 60]
            if len(_call_times) < _RATE_LIMIT:
                _call_times.append(now)
                return  # slot acquired
            sleep_time = 60 - (now - _call_times[0]) + 0.1
        # Sleep OUTSIDE the lock so other threads aren't blocked
        if sleep_time > 0:
            time.sleep(sleep_time)


def _get(endpoint: str, params: dict | None = None) -> dict | list | None:
    if not API_KEY:
        return None
    p = params or {}
    p["token"] = API_KEY
    for attempt in range(2):  # max 2 attempts — avoid long blocking waits on free tier
        _rate_limit()
        try:
            resp = requests.get(f"{BASE_URL}{endpoint}", params=p, timeout=15, proxies=PROXIES)
            if resp.status_code == 403:
                return None
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                logger.warning("Finnhub rate limit hit (attempt %d), sleeping %ds", attempt + 1, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("Finnhub %s error: %s", endpoint, e)
            return None
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


def get_executives(symbol: str) -> list[dict]:
    """Company executives: name, title, compensation, age, since."""
    data = _get("/stock/executive", {"symbol": symbol})
    if data and "executive" in data:
        return data["executive"]
    return []


def get_insider_transactions(symbol: str) -> list[dict]:
    """Insider buy/sell transactions with name, share count, transaction type."""
    data = _get("/stock/insider-transactions", {"symbol": symbol})
    if data and "data" in data:
        return data["data"]
    return []


def get_insider_sentiment(symbol: str) -> dict | None:
    """Monthly insider sentiment (MSPR: Monthly Share Purchase Ratio)."""
    data = _get("/stock/insider-sentiment", {"symbol": symbol})
    if data and "data" in data:
        return data
    return None


def get_recommendation_trends(symbol: str) -> list[dict]:
    """Analyst recommendation trends: strongBuy, buy, hold, sell, strongSell."""
    data = _get("/stock/recommendation", {"symbol": symbol})
    return data if isinstance(data, list) else []


def get_peers(symbol: str) -> list[str]:
    """List of peer/comparable company tickers."""
    data = _get("/stock/peers", {"symbol": symbol})
    return data if isinstance(data, list) else []


def get_price_target(symbol: str) -> dict | None:
    """Analyst price target consensus: high, low, mean, median."""
    data = _get("/stock/price-target", {"symbol": symbol})
    if data and data.get("targetMean"):
        return data
    return None
