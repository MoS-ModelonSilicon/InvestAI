"""
Unified data provider: tries Yahoo Finance first, falls back to Finnhub.

Yahoo provides richer data and international support but gets blocked on cloud
servers. Finnhub works everywhere but has rate limits and US-only on free tier.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
_PROXIES = {
    "http": "http://proxy-dmz.intel.com:911",
    "https": "http://proxy-dmz.intel.com:912",
} if _USE_PROXY else None

_yahoo_disabled = False


def _yf_ticker(symbol: str):
    """Get a yfinance Ticker — proxy picked up from HTTPS_PROXY env var by curl_cffi."""
    import yfinance as yf
    return yf.Ticker(symbol)


def _try_yahoo_quote(symbol: str) -> Optional[dict]:
    global _yahoo_disabled
    if _yahoo_disabled:
        return None
    try:
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
        err = str(e)
        if "401" in err or "403" in err or "Unauthorized" in err:
            logger.warning("Yahoo Finance blocked, disabling for this session")
            _yahoo_disabled = True
        return None


def _try_yahoo_profile(symbol: str) -> Optional[dict]:
    global _yahoo_disabled
    if _yahoo_disabled:
        return None
    try:
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
        if "401" in str(e) or "403" in str(e):
            _yahoo_disabled = True
        return None


def _try_yahoo_metrics(symbol: str) -> Optional[dict]:
    global _yahoo_disabled
    if _yahoo_disabled:
        return None
    try:
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
            "dividendYieldIndicatedAnnual": (info.get("dividendYield") or 0) * 100 if info.get("dividendYield") else None,
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
        if "401" in str(e) or "403" in str(e):
            _yahoo_disabled = True
        return None


def _try_yahoo_candles(symbol: str, resolution: str, from_ts: int, to_ts: int) -> Optional[dict]:
    global _yahoo_disabled
    if _yahoo_disabled:
        return None
    try:
        t = _yf_ticker(symbol)
        interval_map = {"1": "1m", "5": "5m", "15": "15m", "60": "1h", "D": "1d", "W": "1wk", "M": "1mo"}
        yf_interval = interval_map.get(resolution, "1d")
        period_secs = to_ts - from_ts
        period_days = period_secs // 86400

        if yf_interval in ("1m",) and period_days > 7:
            period_days = 7
            from_ts = to_ts - 7 * 86400

        start = datetime.fromtimestamp(from_ts).strftime("%Y-%m-%d")
        end = datetime.fromtimestamp(to_ts).strftime("%Y-%m-%d")
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
        if "401" in str(e) or "403" in str(e):
            _yahoo_disabled = True
        return None


def _try_yahoo_news(symbol: str, days_back: int = 7) -> Optional[list]:
    global _yahoo_disabled
    if _yahoo_disabled:
        return None
    try:
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
        if "401" in str(e) or "403" in str(e):
            _yahoo_disabled = True
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
    result = _try_yahoo_candles(symbol, resolution, from_ts, to_ts)
    if result:
        return result
    return fh.get_candles(symbol, resolution, from_ts, to_ts)


def get_company_news(symbol: str, days_back: int = 7) -> list[dict]:
    result = _try_yahoo_news(symbol, days_back)
    if result:
        return result
    return fh.get_company_news(symbol, days_back)


def get_earnings_calendar(from_date: str, to_date: str) -> list[dict]:
    return fh.get_earnings_calendar(from_date, to_date)
