"""
Unified data provider: tries Yahoo Finance first, falls back to Finnhub.

Yahoo provides richer data and international support but gets blocked on cloud
servers. Finnhub works everywhere but has rate limits and US-only on free tier.
"""

import io
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

# ── Candle cache: daily candles barely change, avoid re-fetching every scan ──
_candle_cache: dict[str, tuple[float, dict]] = {}
_candle_cache_lock = threading.Lock()
CANDLE_CACHE_TTL = 1800  # 30 min for daily candles
CANDLE_CACHE_MAX = 500

logger = logging.getLogger(__name__)

# ── Suppress noisy yfinance / peewee / urllib3 loggers ──────
for _mod in ("yfinance", "peewee", "urllib3.connectionpool"):
    logging.getLogger(_mod).setLevel(logging.CRITICAL)

_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
_PROXIES = {
    "http": "http://proxy-dmz.intel.com:911",
    "https": "http://proxy-dmz.intel.com:912",
} if _USE_PROXY else None

if _USE_PROXY:
    os.environ.setdefault("HTTP_PROXY", "http://proxy-dmz.intel.com:911")
    os.environ.setdefault("HTTPS_PROXY", "http://proxy-dmz.intel.com:912")

# Allow explicit disable via env: set DISABLE_YAHOO=1 for cloud deployments
_yahoo_disabled = os.environ.get("DISABLE_YAHOO", "").lower() in ("1", "true", "yes")
_yahoo_lock = threading.Lock()
_yahoo_tested = False  # True once we've probed Yahoo at least once


def _disable_yahoo(reason: str = ""):
    """Thread-safe one-way switch to disable Yahoo for this process."""
    global _yahoo_disabled
    if not _yahoo_disabled:
        with _yahoo_lock:
            if not _yahoo_disabled:
                _yahoo_disabled = True
                logger.warning("Yahoo Finance disabled%s — Finnhub only",
                               f": {reason}" if reason else "")


@contextmanager
def _suppress_stderr():
    """Temporarily redirect stderr to swallow yfinance's noisy HTTP error prints."""
    old = sys.stderr
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stderr = old


def _yf_ticker(symbol: str):
    """Get a yfinance Ticker -- lazy-imported to save memory when DISABLE_YAHOO=1."""
    import yfinance as yf
    return yf.Ticker(symbol)


def _yahoo_probe() -> bool:
    """Quick one-shot test: can we reach Yahoo Finance? Sets _yahoo_disabled on failure."""
    global _yahoo_tested
    if _yahoo_tested:
        return not _yahoo_disabled
    with _yahoo_lock:
        if _yahoo_tested:
            return not _yahoo_disabled
        _yahoo_tested = True
    try:
        with _suppress_stderr():
            t = _yf_ticker("AAPL")
            price = float(t.fast_info.get("lastPrice", 0) or 0)
        if price > 0:
            logger.info("Yahoo Finance reachable (AAPL=%.2f)", price)
            return True
        _disable_yahoo("probe returned no price")
        return False
    except Exception as e:
        _disable_yahoo(f"probe failed: {e}")
        return False


def _try_yahoo_quote(symbol: str) -> Optional[dict]:
    if _yahoo_disabled or not _yahoo_probe():
        return None
    try:
        with _suppress_stderr():
            t = _yf_ticker(symbol)
            info = t.fast_info
        price = float(info.get("lastPrice", 0) or info.get("last_price", 0))
        prev = float(info.get("previousClose", 0) or info.get("previous_close", 0))
        if price <= 0:
            return None
        change = round(price - prev, 2) if prev else 0
        change_pct = round((change / prev) * 100, 2) if prev else 0
        return {
            "c": price,
            "pc": prev,
            "d": change,
            "dp": change_pct,
            "h": float(info.get("dayHigh", 0) or info.get("day_high", 0) or price),
            "l": float(info.get("dayLow", 0) or info.get("day_low", 0) or price),
            "o": float(info.get("open", 0) or price),
        }
    except Exception as e:
        _disable_yahoo(str(e)[:120])
        return None


def _try_yahoo_profile(symbol: str) -> Optional[dict]:
    if _yahoo_disabled or not _yahoo_probe():
        return None
    try:
        with _suppress_stderr():
            t = _yf_ticker(symbol)
            info = t.info
        if not info or not info.get("shortName"):
            return None
        mcap = info.get("marketCap", 0) or 0
        return {
            "name": info.get("shortName", symbol),
            "finnhubIndustry": info.get("sector", "N/A"),
            "marketCapitalization": mcap / 1_000_000 if mcap else 0,
            "ticker": symbol,
            "exchange": info.get("exchange", ""),
        }
    except Exception as e:
        _disable_yahoo(str(e)[:120])
        return None


def _try_yahoo_metrics(symbol: str) -> Optional[dict]:
    if _yahoo_disabled or not _yahoo_probe():
        return None
    try:
        with _suppress_stderr():
            t = _yf_ticker(symbol)
            info = t.info
        if not info:
            return None
        return {
            "peTTM": info.get("trailingPE"),
            "peAnnual": info.get("forwardPE"),
            "beta": info.get("beta"),
            "52WeekHigh": info.get("fiftyTwoWeekHigh"),
            "52WeekLow": info.get("fiftyTwoWeekLow"),
            "dividendYieldIndicatedAnnual": info.get("dividendYield"),
            "netProfitMarginTTM": info.get("profitMargins") and info["profitMargins"] * 100,
            "revenueGrowthTTMYoy": info.get("revenueGrowth") and info["revenueGrowth"] * 100,
            "epsGrowthTTMYoy": info.get("earningsGrowth") and info["earningsGrowth"] * 100,
            "totalDebt/totalEquityQuarterly": info.get("debtToEquity"),
            "roeTTM": info.get("returnOnEquity") and info["returnOnEquity"] * 100,
            "freeCashFlowTTM": info.get("freeCashflow"),
            "currentRatio": info.get("currentRatio"),
            "priceToBook": info.get("priceToBook"),
            "trailingEps": info.get("trailingEps"),
            "bookValue": info.get("bookValue"),
            "targetMeanPrice": info.get("targetMeanPrice"),
            "targetHighPrice": info.get("targetHighPrice"),
            "targetLowPrice": info.get("targetLowPrice"),
        }
    except Exception as e:
        _disable_yahoo(str(e)[:120])
        return None


def _try_yahoo_candles(symbol: str, resolution: str, from_ts: int, to_ts: int) -> Optional[dict]:
    if _yahoo_disabled or not _yahoo_probe():
        return None
    try:
        interval_map = {"1": "1m", "5": "5m", "15": "15m", "60": "1h", "D": "1d", "W": "1wk", "M": "1mo"}
        yf_interval = interval_map.get(resolution, "1d")
        period_secs = to_ts - from_ts
        period_days = period_secs // 86400

        if yf_interval in ("1m",) and period_days > 7:
            period_days = 7
            from_ts = to_ts - 7 * 86400

        start = datetime.fromtimestamp(from_ts).strftime("%Y-%m-%d")
        end = datetime.fromtimestamp(to_ts).strftime("%Y-%m-%d")
        with _suppress_stderr():
            t = _yf_ticker(symbol)
            df = t.history(start=start, end=end, interval=yf_interval)

        if df is None or df.empty:
            return None

        return {
            "s": "ok",
            "c": [round(v, 2) for v in df["Close"].tolist()],
            "o": [round(v, 2) for v in df["Open"].tolist()],
            "h": [round(v, 2) for v in df["High"].tolist()],
            "l": [round(v, 2) for v in df["Low"].tolist()],
            "v": [int(v) for v in df["Volume"].tolist()],
            "t": [int(ts.timestamp()) for ts in df.index],
        }
    except Exception as e:
        _disable_yahoo(str(e)[:120])
        return None


def _try_yahoo_news(symbol: str, days_back: int = 7) -> Optional[list]:
    if _yahoo_disabled or not _yahoo_probe():
        return None
    try:
        with _suppress_stderr():
            t = _yf_ticker(symbol)
            news = t.news
        if not news:
            return None
        result = []
        for item in news[:10]:
            content = item.get("content", item) if isinstance(item, dict) else item
            title = content.get("title", "") or content.get("headline", "")
            if not title:
                continue
            pub_info = content.get("provider", {})
            result.append({
                "headline": title,
                "source": pub_info.get("displayName", "") if isinstance(pub_info, dict) else str(pub_info),
                "url": content.get("canonicalUrl", {}).get("url", "") or content.get("link", ""),
                "datetime": content.get("pubDate", 0),
                "image": content.get("thumbnail", {}).get("originalUrl", "") if isinstance(content.get("thumbnail"), dict) else "",
                "summary": content.get("summary", ""),
                "related": symbol,
            })
        return result if result else None
    except Exception as e:
        _disable_yahoo(str(e)[:120])
        return None


# ── Public API (Yahoo-first, Finnhub-fallback) ──────────────

from src.services import finnhub_client as fh


def get_quote(symbol: str) -> Optional[dict]:
    result = _try_yahoo_quote(symbol)
    if result:
        return result
    return fh.get_quote(symbol)


def get_profile(symbol: str) -> Optional[dict]:
    result = _try_yahoo_profile(symbol)
    if result:
        return result
    return fh.get_profile(symbol)


def get_metrics(symbol: str) -> Optional[dict]:
    result = _try_yahoo_metrics(symbol)
    if result:
        return result
    return fh.get_metrics(symbol)


def get_candles(symbol: str, resolution: str, from_ts: int, to_ts: int) -> Optional[dict]:
    # Check candle cache first (daily candles are stable)
    if resolution == "D":
        cache_key = f"{symbol}:{from_ts}:{to_ts}"
        with _candle_cache_lock:
            if cache_key in _candle_cache:
                ts, data = _candle_cache[cache_key]
                if time.time() - ts < CANDLE_CACHE_TTL:
                    return data

    result = _try_yahoo_candles(symbol, resolution, from_ts, to_ts)
    if not result:
        result = fh.get_candles(symbol, resolution, from_ts, to_ts)

    # Cache daily candles
    if result and resolution == "D":
        cache_key = f"{symbol}:{from_ts}:{to_ts}"
        with _candle_cache_lock:
            _candle_cache[cache_key] = (time.time(), result)
            # Evict if too large
            if len(_candle_cache) > CANDLE_CACHE_MAX:
                oldest = sorted(_candle_cache.items(), key=lambda x: x[1][0])
                for k, _ in oldest[:100]:
                    del _candle_cache[k]

    return result


def get_company_news(symbol: str, days_back: int = 7) -> list[dict]:
    result = _try_yahoo_news(symbol, days_back)
    if result:
        return result
    return fh.get_company_news(symbol, days_back)


def get_earnings_calendar(from_date: str, to_date: str) -> list[dict]:
    return fh.get_earnings_calendar(from_date, to_date)


def get_executives(symbol: str) -> list[dict]:
    return fh.get_executives(symbol)


def get_insider_transactions(symbol: str) -> list[dict]:
    return fh.get_insider_transactions(symbol)


def get_insider_sentiment(symbol: str) -> dict | None:
    return fh.get_insider_sentiment(symbol)


def get_recommendation_trends(symbol: str) -> list[dict]:
    return fh.get_recommendation_trends(symbol)


def get_peers(symbol: str) -> list[str]:
    return fh.get_peers(symbol)


def get_price_target(symbol: str) -> dict | None:
    return fh.get_price_target(symbol)
