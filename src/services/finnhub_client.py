"""Thin wrapper around the Finnhub REST API (free tier, 60 calls/min)."""

import logging
import os
import threading
import time
from typing import Any, cast
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("FINNHUB_API_KEY", "")
BASE_URL = "https://finnhub.io/api/v1"

if not API_KEY:
    logger.info("FINNHUB_API_KEY not set — Finnhub disabled, using Yahoo only")

_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
PROXIES = (
    {
        "http": "http://proxy-dmz.intel.com:911",
        "https": "http://proxy-dmz.intel.com:912",
    }
    if _USE_PROXY
    else None
)

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


def _get(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
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
            result = resp.json()
            if isinstance(result, dict):
                return cast(dict[str, Any], result)
            return None
        except Exception as e:
            logger.warning("Finnhub %s error: %s", endpoint, e)
            return None
    return None


def _get_list(endpoint: str, params: dict[str, Any] | None = None) -> list[Any]:
    """Like _get but for endpoints that return a JSON array."""
    if not API_KEY:
        return []
    p = params or {}
    p["token"] = API_KEY
    for attempt in range(2):
        _rate_limit()
        try:
            resp = requests.get(f"{BASE_URL}{endpoint}", params=p, timeout=15, proxies=PROXIES)
            if resp.status_code in (403, 429):
                if resp.status_code == 429:
                    time.sleep(10 * (attempt + 1))
                    continue
                return []
            resp.raise_for_status()
            result = resp.json()
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning("Finnhub %s error: %s", endpoint, e)
            return []
    return []


def get_quote(symbol: str) -> dict[str, Any] | None:
    """Real-time quote: c=current, d=change, dp=change%, h=high, l=low, o=open, pc=prevClose."""
    data = _get("/quote", {"symbol": symbol})
    if data and data.get("c", 0) > 0:
        return data
    return None


def get_profile(symbol: str) -> dict[str, Any] | None:
    """Company profile: name, finnhubIndustry, marketCapitalization (in millions), logo, etc."""
    data = _get("/stock/profile2", {"symbol": symbol})
    if data and data.get("name"):
        return data
    return None


def get_metrics(symbol: str) -> dict[str, Any] | None:
    """Basic financials: PE, beta, 52wk high/low, dividend yield, margins, etc."""
    data = _get("/stock/metric", {"symbol": symbol, "metric": "all"})
    if data and data.get("metric"):
        metric_val = data["metric"]
        return cast(dict[str, Any], metric_val) if isinstance(metric_val, dict) else None
    return None


def get_candles(symbol: str, resolution: str, from_ts: int, to_ts: int) -> dict[str, Any] | None:
    """OHLCV candles. resolution: 1, 5, 15, 30, 60, D, W, M."""
    data = _get(
        "/stock/candle",
        {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts,
        },
    )
    if data and data.get("s") == "ok":
        return data
    return None


def get_company_news(symbol: str, days_back: int = 7) -> list[dict[str, Any]]:
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return cast(list[dict[str, Any]], _get_list("/company-news", {"symbol": symbol, "from": from_date, "to": to_date}))


def get_earnings_calendar(from_date: str, to_date: str) -> list[dict[str, Any]]:
    data = _get("/calendar/earnings", {"from": from_date, "to": to_date})
    if data and "earningsCalendar" in data:
        val = data["earningsCalendar"]
        return cast(list[dict[str, Any]], val) if isinstance(val, list) else []
    return []


def get_executives(symbol: str) -> list[dict[str, Any]]:
    """Company executives: name, title, compensation, age, since."""
    data = _get("/stock/executive", {"symbol": symbol})
    if data and "executive" in data:
        val = data["executive"]
        return cast(list[dict[str, Any]], val) if isinstance(val, list) else []
    return []


def get_insider_transactions(symbol: str) -> list[dict[str, Any]]:
    """Insider buy/sell transactions with name, share count, transaction type."""
    data = _get("/stock/insider-transactions", {"symbol": symbol})
    if data and "data" in data:
        val = data["data"]
        return cast(list[dict[str, Any]], val) if isinstance(val, list) else []
    return []


def get_insider_sentiment(symbol: str) -> dict[str, Any] | None:
    """Monthly insider sentiment (MSPR: Monthly Share Purchase Ratio)."""
    data = _get("/stock/insider-sentiment", {"symbol": symbol})
    if data and "data" in data:
        return data
    return None


def get_recommendation_trends(symbol: str) -> list[dict[str, Any]]:
    """Analyst recommendation trends: strongBuy, buy, hold, sell, strongSell."""
    return cast(list[dict[str, Any]], _get_list("/stock/recommendation", {"symbol": symbol}))


def get_peers(symbol: str) -> list[str]:
    """List of peer/comparable company tickers."""
    return cast(list[str], _get_list("/stock/peers", {"symbol": symbol}))


def get_price_target(symbol: str) -> dict[str, Any] | None:
    """Analyst price target consensus: high, low, mean, median."""
    data = _get("/stock/price-target", {"symbol": symbol})
    if data and data.get("targetMean"):
        return data
    return None


def search_symbols(query: str, exchange: str = "") -> list[dict[str, Any]]:
    """Symbol lookup: search by name or ticker across exchanges.

    Returns list of {description, displaySymbol, symbol, type} dicts.
    Optional exchange filter, e.g. 'TA' for Tel Aviv.
    """
    params: dict[str, Any] = {"q": query}
    if exchange:
        params["exchange"] = exchange
    data = _get("/search", params)
    if data and "result" in data:
        val = data["result"]
        return cast(list[dict[str, Any]], val) if isinstance(val, list) else []
    return []
