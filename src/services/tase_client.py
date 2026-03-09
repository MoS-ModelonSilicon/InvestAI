"""Direct Yahoo Finance API client for Tel Aviv Stock Exchange (.TA) symbols.

Bypasses the yfinance library which can be unreliable on cloud servers.
Uses the public Yahoo Finance v8 chart API and v1 search API directly.
"""

import logging
import os
import threading
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
_PROXIES = (
    {
        "http": "http://proxy-dmz.intel.com:911",
        "https": "http://proxy-dmz.intel.com:912",
    }
    if _USE_PROXY
    else None
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_TIMEOUT = 12

# ── TASE symbol → Hebrew name + sector (for when Yahoo profile is sparse) ──
TASE_STOCK_INFO: dict[str, dict[str, str]] = {
    "LUMI.TA": {"name": "Bank Leumi", "name_he": "בנק לאומי", "sector": "Financial Services", "industry": "Banks"},
    "POLI.TA": {"name": "Bank Hapoalim", "name_he": "בנק הפועלים", "sector": "Financial Services", "industry": "Banks"},
    "DSCT.TA": {
        "name": "Israel Discount Bank",
        "name_he": "בנק דיסקונט",
        "sector": "Financial Services",
        "industry": "Banks",
    },
    "MZTF.TA": {
        "name": "Mizrahi Tefahot Bank",
        "name_he": "בנק מזרחי טפחות",
        "sector": "Financial Services",
        "industry": "Banks",
    },
    "FIBI.TA": {
        "name": "First International Bank",
        "name_he": "הבנק הבינלאומי",
        "sector": "Financial Services",
        "industry": "Banks",
    },
    "BEZQ.TA": {"name": "Bezeq", "name_he": "בזק", "sector": "Communication Services", "industry": "Telecom"},
    "CEL.TA": {"name": "Cellcom Israel", "name_he": "סלקום", "sector": "Communication Services", "industry": "Telecom"},
    "PTNR.TA": {
        "name": "Partner Communications",
        "name_he": "פרטנר",
        "sector": "Communication Services",
        "industry": "Telecom",
    },
    "AZRG.TA": {
        "name": "Azrieli Group",
        "name_he": "קבוצת עזריאלי",
        "sector": "Real Estate",
        "industry": "Real Estate",
    },
    "MGDL.TA": {
        "name": "Migdal Insurance",
        "name_he": "מגדל ביטוח",
        "sector": "Financial Services",
        "industry": "Insurance",
    },
    "HAREL.TA": {
        "name": "Harel Insurance",
        "name_he": "הראל ביטוח",
        "sector": "Financial Services",
        "industry": "Insurance",
    },
    "DLEKG.TA": {"name": "Delek Group", "name_he": "קבוצת דלק", "sector": "Energy", "industry": "Oil & Gas"},
    "ORL.TA": {"name": "Bazan Group", "name_he": "בזן", "sector": "Energy", "industry": "Oil Refining"},
    "STRS.TA": {
        "name": "Strauss Group",
        "name_he": "שטראוס",
        "sector": "Consumer Defensive",
        "industry": "Food Products",
    },
    "ELCO.TA": {"name": "Elco Holdings", "name_he": "אלקו", "sector": "Industrials", "industry": "Conglomerates"},
    "AMOT.TA": {"name": "Amot Investments", "name_he": "אמות", "sector": "Real Estate", "industry": "Real Estate"},
    "TEVA.TA": {
        "name": "Teva Pharmaceutical (TASE)",
        "name_he": "טבע",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
    },
    "ICL.TA": {"name": "ICL Group (TASE)", "name_he": "כיל", "sector": "Basic Materials", "industry": "Chemicals"},
    "NICE.TA": {"name": "Nice Ltd (TASE)", "name_he": "נייס", "sector": "Technology", "industry": "Software"},
    "ESLT.TA": {
        "name": "Elbit Systems (TASE)",
        "name_he": "אלביט מערכות",
        "sector": "Industrials",
        "industry": "Defense",
    },
    "PHOE.TA": {
        "name": "The Phoenix Holdings",
        "name_he": "הפניקס",
        "sector": "Financial Services",
        "industry": "Insurance",
    },
    "MNRT.TA": {
        "name": "Menora Mivtachim",
        "name_he": "מנורה מבטחים",
        "sector": "Financial Services",
        "industry": "Insurance",
    },
    "CLAL.TA": {
        "name": "Clal Insurance",
        "name_he": "כלל ביטוח",
        "sector": "Financial Services",
        "industry": "Insurance",
    },
    "MELISRON.TA": {"name": "Melisron", "name_he": "מליסרון", "sector": "Real Estate", "industry": "Real Estate"},
    "GAZP.TA": {"name": "Gazit Globe", "name_he": "גזית גלוב", "sector": "Real Estate", "industry": "Real Estate"},
    "ALHE.TA": {
        "name": "Alon Hetz Properties",
        "name_he": "אלון חץ",
        "sector": "Real Estate",
        "industry": "Real Estate",
    },
    "ISRA.TA": {"name": "Isramco", "name_he": "ישראמקו", "sector": "Energy", "industry": "Oil & Gas"},
    "OPC.TA": {"name": "OPC Energy", "name_he": "או.פי.סי אנרגיה", "sector": "Utilities", "industry": "Energy"},
    "ENLT.TA": {
        "name": "Enlight Renewable Energy",
        "name_he": "אנלייט",
        "sector": "Utilities",
        "industry": "Renewable Energy",
    },
    "SHPG.TA": {"name": "Shufersal", "name_he": "שופרסל", "sector": "Consumer Defensive", "industry": "Grocery Stores"},
    "RMLI.TA": {
        "name": "Rami Levy Chain Stores",
        "name_he": "רמי לוי",
        "sector": "Consumer Defensive",
        "industry": "Grocery Stores",
    },
    "FOX.TA": {"name": "Fox-Wizel", "name_he": "פוקס", "sector": "Consumer Cyclical", "industry": "Apparel Retail"},
    "FATA.TA": {"name": "Fattal Hotels", "name_he": "מלונות פתאל", "sector": "Consumer Cyclical", "industry": "Hotels"},
    "SPEN.TA": {
        "name": "Shikun & Binui",
        "name_he": "שיכון ובינוי",
        "sector": "Industrials",
        "industry": "Construction",
    },
    "ITMR.TA": {"name": "Ituran", "name_he": "איתוראן", "sector": "Technology", "industry": "Electronics"},
    "SPNS.TA": {"name": "Sapiens International", "name_he": "ספיינס", "sector": "Technology", "industry": "Software"},
    "NVPT.TA": {"name": "Navitas Petroleum", "name_he": "נביטס", "sector": "Energy", "industry": "Oil & Gas"},
    "KMDA.TA": {"name": "Kamada", "name_he": "קמהדע", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "ARPT.TA": {"name": "Airport City", "name_he": "אירפורט סיטי", "sector": "Real Estate", "industry": "Real Estate"},
    "ILDC.TA": {
        "name": "Israel Land Development",
        "name_he": "הכשרת הישוב",
        "sector": "Real Estate",
        "industry": "Real Estate",
    },
    "DANE.TA": {"name": "Dan Hotels", "name_he": "דן מלונות", "sector": "Consumer Cyclical", "industry": "Hotels"},
}

# All known TASE symbols (for batch operations)
TASE_SYMBOLS = list(TASE_STOCK_INFO.keys())

# ── Cache: TASE data cached for 20 min (aligns with main market_data cache) ──
_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 1200  # 20 min


def _get_cached(key: str) -> Optional[dict]:
    with _cache_lock:
        entry = _cache.get(key)
    if entry:
        ts, data = entry
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def _set_cached(key: str, data: dict) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), data)


def is_tase_symbol(symbol: str) -> bool:
    """Check if a symbol is a TASE (.TA) stock."""
    return symbol.upper().endswith(".TA")


def _ils_to_usd(agorot_price: float) -> float:
    """Convert price from ILA (agorot) to approximate USD.

    TASE prices from Yahoo are in ILA (= 1/100 ILS).
    We use a rough ILS/USD rate; exact rate isn't critical for
    screener display since we show the ILS price too.
    """
    ils_price = agorot_price / 100.0
    # Approximate exchange rate — updated periodically would be better,
    # but for screener ranking this is sufficient
    return ils_price / 3.7


def get_tase_quote(symbol: str) -> Optional[dict[str, Any]]:
    """Fetch real-time quote for a TASE symbol via Yahoo Finance v8 chart API.

    Returns Finnhub-compatible quote dict: {c, pc, d, dp, h, l, o}
    Prices are in ILA (agorot) as returned by Yahoo.
    """
    cached = _get_cached(f"quote:{symbol}")
    if cached:
        return cached

    _testing = os.environ.get("TESTING") == "1"
    if _testing:
        return None

    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "5d"},
            headers=_HEADERS,
            proxies=_PROXIES,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("Yahoo chart API returned %d for %s", resp.status_code, symbol)
            return None

        data = resp.json()
        result_list = data.get("chart", {}).get("result")
        if not result_list:
            return None

        meta = result_list[0].get("meta", {})
        price = meta.get("regularMarketPrice", 0)
        if not price or price <= 0:
            return None

        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))

        # Yahoo returns TASE prices in ILA (agorot = 1/100 ILS). Convert to ILS.
        currency = meta.get("currency", "ILA")
        if currency == "ILA":
            price = round(price / 100, 2)
            prev_close = round(prev_close / 100, 2)
            currency = "ILS"

        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        high = meta.get("regularMarketDayHigh", price)
        low = meta.get("regularMarketDayLow", price)
        open_ = meta.get("regularMarketOpen", price)
        if meta.get("currency") == "ILA":
            high = round(high / 100, 2)
            low = round(low / 100, 2)
            open_ = round(open_ / 100, 2)

        quote = {
            "c": price,
            "pc": prev_close,
            "d": change,
            "dp": change_pct,
            "h": high,
            "l": low,
            "o": open_,
            "v": meta.get("regularMarketVolume", 0),
            "currency": currency,
            "exchange": meta.get("exchangeName", "TLV"),
        }
        _set_cached(f"quote:{symbol}", quote)
        return quote
    except Exception as e:
        logger.warning("TASE quote fetch failed for %s: %s", symbol, e)
        return None


def get_tase_profile(symbol: str) -> Optional[dict[str, Any]]:
    """Get company profile for TASE symbol.

    Combines Yahoo chart metadata with our static TASE_STOCK_INFO.
    Returns Finnhub-compatible profile dict.
    """
    static = TASE_STOCK_INFO.get(symbol, {})
    name = static.get("name", symbol.replace(".TA", ""))

    # Try to get extra data from Yahoo
    cached = _get_cached(f"profile:{symbol}")
    if cached:
        return cached

    profile = {
        "name": name,
        "name_he": static.get("name_he", ""),
        "finnhubIndustry": static.get("sector", "N/A"),
        "industry": static.get("industry", "N/A"),
        "ticker": symbol,
        "exchange": "TLV",
        "country": "IL",
        "marketCapitalization": 0,  # in millions, filled from Yahoo if available
    }

    _testing = os.environ.get("TESTING") == "1"
    if _testing:
        _set_cached(f"profile:{symbol}", profile)
        return profile

    # Try Yahoo Finance search API for extra metadata
    try:
        resp = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": symbol, "quotesCount": "1", "newsCount": "0"},
            headers=_HEADERS,
            proxies=_PROXIES,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            quotes = resp.json().get("quotes", [])
            if quotes:
                q = quotes[0]
                if q.get("longname"):
                    profile["name"] = q["longname"]
                if q.get("sector"):
                    profile["finnhubIndustry"] = q["sector"]
                if q.get("industry"):
                    profile["industry"] = q["industry"]
    except Exception:
        pass  # static data is sufficient

    _set_cached(f"profile:{symbol}", profile)
    return profile


def get_tase_metrics(symbol: str) -> Optional[dict[str, Any]]:
    """Get basic metrics for TASE symbol via Yahoo v8 chart API.

    Returns a Finnhub-compatible metrics dict.
    """
    cached = _get_cached(f"metrics:{symbol}")
    if cached:
        return cached

    _testing = os.environ.get("TESTING") == "1"
    if _testing:
        return {}

    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1y"},
            headers=_HEADERS,
            proxies=_PROXIES,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return {}

        data = resp.json()
        result_list = data.get("chart", {}).get("result")
        if not result_list:
            return {}

        meta = result_list[0].get("meta", {})
        currency = meta.get("currency", "ILA")
        div = 100 if currency == "ILA" else 1
        metrics = {
            "52WeekHigh": round(meta.get("fiftyTwoWeekHigh", 0) / div, 2) if meta.get("fiftyTwoWeekHigh") else None,
            "52WeekLow": round(meta.get("fiftyTwoWeekLow", 0) / div, 2) if meta.get("fiftyTwoWeekLow") else None,
        }
        _set_cached(f"metrics:{symbol}", metrics)
        return metrics
    except Exception as e:
        logger.warning("TASE metrics fetch failed for %s: %s", symbol, e)
        return {}


def get_tase_candles(symbol: str, resolution: str, from_ts: int, to_ts: int) -> Optional[dict]:
    """Get OHLCV candles for TASE symbol via Yahoo v8 chart API."""
    _testing = os.environ.get("TESTING") == "1"
    if _testing:
        return None

    interval_map = {"1": "1m", "5": "5m", "15": "15m", "60": "1h", "D": "1d", "W": "1wk", "M": "1mo"}
    yf_interval = interval_map.get(resolution, "1d")

    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={
                "interval": yf_interval,
                "period1": str(from_ts),
                "period2": str(to_ts),
            },
            headers=_HEADERS,
            proxies=_PROXIES,
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        result_list = data.get("chart", {}).get("result")
        if not result_list:
            return None

        r = result_list[0]
        timestamps = r.get("timestamp", [])
        indicators = r.get("indicators", {})
        ohlcv = indicators.get("quote", [{}])[0]

        if not timestamps or not ohlcv.get("close"):
            return None

        # Filter out None values
        valid = [
            (t, o, h, l, c, v)
            for t, o, h, l, c, v in zip(
                timestamps,
                ohlcv.get("open", []),
                ohlcv.get("high", []),
                ohlcv.get("low", []),
                ohlcv.get("close", []),
                ohlcv.get("volume", []),
            )
            if c is not None
        ]

        if not valid:
            return None

        # Convert ILA (agorot) to ILS for OHLC prices
        meta = result_list[0].get("meta", {})
        currency = meta.get("currency", "ILA")
        div = 100.0 if currency == "ILA" else 1.0

        return {
            "s": "ok",
            "t": [v[0] for v in valid],
            "o": [round((v[1] or 0) / div, 2) for v in valid],
            "h": [round((v[2] or 0) / div, 2) for v in valid],
            "l": [round((v[3] or 0) / div, 2) for v in valid],
            "c": [round((v[4] or 0) / div, 2) for v in valid],
            "v": [int(v[5] or 0) for v in valid],
        }
    except Exception as e:
        logger.warning("TASE candles fetch failed for %s: %s", symbol, e)
        return None


def search_tase(query: str) -> list[dict[str, str]]:
    """Search TASE stocks by Hebrew or English name.

    Returns list of matching {symbol, name, name_he, sector} dicts.
    Uses local TASE_STOCK_INFO for Hebrew matching (Yahoo rejects Hebrew text).
    """
    q = query.strip().lower()
    if not q:
        return []

    results = []
    for symbol, info in TASE_STOCK_INFO.items():
        name_lower = info.get("name", "").lower()
        name_he = info.get("name_he", "")
        sector = info.get("sector", "").lower()
        sym_lower = symbol.lower()

        if q in sym_lower or q in name_lower or q in name_he or q in sector:
            results.append(
                {
                    "symbol": symbol,
                    "name": info["name"],
                    "name_he": name_he,
                    "sector": info.get("sector", ""),
                    "exchange": "TLV",
                }
            )

    return results
