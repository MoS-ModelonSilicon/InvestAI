"""
Live scraper for funder.co.il — fetches real Israeli fund data.
Caches results for 1 hour to avoid hammering the site.
"""
import json
import logging
import re
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, list]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 3600  # 1 hour

import os
_USE_PROXY = os.environ.get("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
PROXIES = {
    "http": "http://proxy-dmz.intel.com:911",
    "https": "http://proxy-dmz.intel.com:912",
} if _USE_PROXY else None
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TIMEOUT = 20

PAGES = {
    "kaspit":  {"url": "https://www.funder.co.il/kaspit",  "var": "kaspitData",  "category": "Kaspit (Money Market)"},
    "mehakot": {"url": "https://www.funder.co.il/mehakot",  "var": "mehakotData", "category": "Index Tracking"},
    "ksherot": {"url": "https://www.funder.co.il/ksherot",  "var": "ksherotData", "category": "Kosher Funds"},
    "okvot":   {"url": "https://www.funder.co.il/okvot",    "var": "okvotData",   "category": "Actively Managed"},
}


def _extract_json_var(html: str, var_name: str) -> Optional[dict]:
    pattern = f"var {var_name} = "
    idx = html.find(pattern)
    if idx == -1:
        return None
    start = idx + len(pattern)
    depth = 0
    end = start
    for i in range(start, min(start + 200_000, len(html))):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
        if depth == 0:
            end = i + 1
            break
    try:
        return json.loads(html[start:end])
    except json.JSONDecodeError:
        return None


def _normalize_fund(raw: dict, category: str) -> dict:
    """Convert raw funder.co.il JSON to our standard format."""
    name = raw.get("fundName", "")
    is_kosher = "כשר" in name or category == "Kosher Funds"

    return {
        "fund_num": raw.get("fundNum"),
        "name": name,
        "manager": (raw.get("fundMng") or "").strip(),
        "fee": raw.get("nihol", 0),
        "entry_fee": raw.get("hosafa", 0),
        "daily_return": raw.get("1day"),
        "mtd_return": raw.get("monthBegin"),
        "ytd_return": raw.get("yearBegin"),
        "annual_return": raw.get("1year"),
        "monthly_return": raw.get("y30"),
        "size_m": raw.get("rSize", 0),
        "last_update": raw.get("lastUpdate"),
        "risk_profile": raw.get("proflieS", "0"),
        "equity_pct": raw.get("menaiot", "0"),
        "category": category,
        "kosher": is_kosher,
        "funder_url": f"https://www.funder.co.il/fund/{raw.get('fundNum', '')}",
    }


def _fetch_page(page_key: str) -> list[dict]:
    """Fetch and parse a single funder.co.il page."""
    cfg = PAGES[page_key]
    try:
        r = requests.get(cfg["url"], headers=HEADERS, proxies=PROXIES, timeout=TIMEOUT)
        r.raise_for_status()
        data = _extract_json_var(r.text, cfg["var"])
        if not data:
            logger.warning("Could not extract %s from %s", cfg["var"], cfg["url"])
            return []
        raw_funds = data.get("x", [])
        return [_normalize_fund(f, cfg["category"]) for f in raw_funds if f.get("fundName")]
    except Exception as e:
        logger.error("Error fetching %s: %s", page_key, e)
        return []


def fetch_all_funds(force_refresh: bool = False) -> list[dict]:
    """Fetch funds from all categories, using cache."""
    cache_key = "all_il_funds"
    if not force_refresh:
        with _cache_lock:
            if cache_key in _cache:
                ts, data = _cache[cache_key]
                if time.time() - ts < CACHE_TTL:
                    return data

    all_funds = []
    for page_key in PAGES:
        funds = _fetch_page(page_key)
        all_funds.extend(funds)
        logger.info("Fetched %d funds from %s", len(funds), page_key)

    if all_funds:
        with _cache_lock:
            _cache[cache_key] = (time.time(), all_funds)

    return all_funds


def get_categories() -> list[str]:
    return sorted(set(cfg["category"] for cfg in PAGES.values()))


def get_managers(funds: list[dict]) -> list[str]:
    return sorted(set(f["manager"] for f in funds if f["manager"]))
