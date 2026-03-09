"""
TradingView Ideas scraper: fetches published trade ideas from TradingView's
hidden public API endpoint.

Approach:
- TradingView publishes ideas at https://www.tradingview.com/ideas/
- There's an undocumented JSON endpoint that powers the ideas page
- We fetch ideas filtered by market (stocks) and extract the structured data
- TradingView ideas often have explicit entry, targets, and stop-loss levels
"""

import logging
import re
import time
from datetime import datetime
from typing import Optional

import requests

from .base import BaseScraper, UnifiedPick, is_valid_ticker, PROXIES

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.tradingview.com/ideas/",
    "Origin": "https://www.tradingview.com",
}

# TradingView hidden API for ideas listing
# This endpoint returns JSON with idea data including symbols, descriptions, etc.
TV_IDEAS_URL = "https://www.tradingview.com/ideas-widget/"

# Alternative: scrape the ideas page HTML and extract structured data
TV_IDEAS_PAGE = "https://www.tradingview.com/ideas/stocks/"

# TradingView recommendations/signals endpoint (technical analysis)
TV_SCAN_URL = "https://scanner.tradingview.com/america/scan"

# Price-level extraction patterns for idea descriptions
ENTRY_PATTERN = re.compile(
    r"(?:entry|buy\s*(?:zone|area|at|around|near)?|long\s*(?:at|above)?)\s*"
    r"[:=]?\s*\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)

TARGET_PATTERN = re.compile(
    r"(?:target|TP|take\s*profit|price\s*target|PT)\s*"
    r"(?:\d\s*)?[:=]?\s*\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)

STOP_PATTERN = re.compile(
    r"(?:stop\s*loss|SL|stop|invalidation)\s*[:=]?\s*\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)


class TradingViewScraper(BaseScraper):
    """
    Scrapes TradingView for stock trade ideas using their technical scanner API
    and ideas page. Combines:
    1. Scanner API: real-time technical signals (buy/sell/neutral)
    2. Ideas page: community-published trade ideas with levels
    """

    name = "tradingview"

    def __init__(
        self,
        max_ideas: int = 50,
        min_volume: int = 500_000,
    ):
        self.max_ideas = max_ideas
        self.min_volume = min_volume

    def fetch_picks(self) -> list[UnifiedPick]:
        picks: list[UnifiedPick] = []

        # Source 1: Technical scanner signals
        scanner_picks = self._fetch_scanner_signals()
        picks.extend(scanner_picks)

        time.sleep(1)

        # Source 2: Community ideas
        ideas_picks = self._fetch_ideas()
        picks.extend(ideas_picks)

        # Deduplicate by symbol+date
        seen: set[str] = set()
        deduped: list[UnifiedPick] = []
        for p in picks:
            key = f"{p.symbol}:{p.date}"
            if key not in seen:
                seen.add(key)
                deduped.append(p)

        return deduped

    def _fetch_scanner_signals(self) -> list[UnifiedPick]:
        """
        Use TradingView's scanner API to get stocks with strong buy signals.
        This is a public API used by the TradingView screener.
        """
        payload = {
            "columns": [
                "name",
                "close",
                "change",
                "change_abs",
                "Recommend.All",
                "Recommend.MA",
                "Recommend.Other",
                "volume",
                "market_cap_basic",
                "description",
                "type",
                "subtype",
                "exchange",
            ],
            "filter": [
                {"left": "type", "operation": "equal", "right": "stock"},
                {"left": "subtype", "operation": "in_range", "right": ["common", ""]},
                {"left": "exchange", "operation": "in_range", "right": ["NYSE", "NASDAQ", "AMEX"]},
                {"left": "Recommend.All", "operation": "greater", "right": 0.3},
                {"left": "volume", "operation": "greater", "right": self.min_volume},
                {"left": "market_cap_basic", "operation": "greater", "right": 100_000_000},
            ],
            "options": {"lang": "en"},
            "range": [0, self.max_ideas],
            "sort": {"sortBy": "Recommend.All", "sortOrder": "desc"},
        }

        try:
            resp = requests.post(
                TV_SCAN_URL,
                json=payload,
                headers=HEADERS,
                proxies=PROXIES,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("[tradingview] scanner API failed")
            return []

        picks: list[UnifiedPick] = []
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for row in data.get("data", []):
            try:
                vals = row.get("d", [])
                if len(vals) < 13:
                    continue

                symbol = vals[0]  # e.g. "AAPL"
                close = vals[1]
                change_pct = vals[2]
                recommend_all = vals[4]  # -1 to 1 (strong sell to strong buy)
                recommend_ma = vals[5]
                recommend_other = vals[6]
                volume = vals[7]
                description = vals[9] or ""
                exchange = vals[12] or ""

                # Clean symbol (remove exchange prefix if present)
                if ":" in str(symbol):
                    symbol = str(symbol).split(":")[-1]

                if not is_valid_ticker(symbol):
                    continue

                # Determine signal type
                if recommend_all >= 0.5:
                    signal = "Strong Buy"
                    pick_type = "breakout"
                elif recommend_all >= 0.3:
                    signal = "Buy"
                    pick_type = "swing"
                else:
                    continue  # Skip weak signals

                # Generate approximate targets and stops from current price
                entry = round(close, 2) if close else None
                targets = []
                stop = None
                if entry:
                    # Moderate targets: 5%, 10%, 15% above entry
                    targets = [
                        round(entry * 1.05, 2),
                        round(entry * 1.10, 2),
                    ]
                    # Stop loss: 5% below entry
                    stop = round(entry * 0.95, 2)

                confidence = round(min(max(recommend_all, 0), 1), 2)

                note = (
                    f"{signal} ({recommend_all:.2f}) | "
                    f"MA: {recommend_ma:.2f} | Other: {recommend_other:.2f} | "
                    f"{description[:60]}"
                )

                picks.append(
                    UnifiedPick(
                        date=today,
                        symbol=symbol,
                        pick_type=pick_type,
                        entry=entry,
                        targets=targets,
                        stop=stop,
                        source="tradingview/scanner",
                        notes=note,
                        url=f"https://www.tradingview.com/symbols/{exchange}-{symbol}/technicals/",
                        confidence=confidence,
                    )
                )

            except Exception:
                logger.debug("[tradingview] failed to parse scanner row", exc_info=True)
                continue

        return picks

    def _fetch_ideas(self) -> list[UnifiedPick]:
        """
        Fetch published trade ideas from TradingView.
        Uses the HTML page and extracts the embedded JSON data.
        """
        try:
            resp = requests.get(
                TV_IDEAS_PAGE,
                headers={**HEADERS, "Accept": "text/html"},
                proxies=PROXIES,
                timeout=30,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception:
            logger.exception("[tradingview] ideas page fetch failed")
            return []

        # Try to extract ideas from the page's embedded data
        # TradingView embeds idea JSON in script tags
        picks: list[UnifiedPick] = []

        # Pattern: look for idea cards with symbol, title, and description
        # TradingView ideas URLs follow: /chart/SYMBOL/IDEAID/
        idea_pattern = re.compile(
            r"/chart/([A-Z]{1,5})/[^/]+/",
        )

        # Extract idea blocks from HTML
        # Look for structured data in <script type="application/ld+json">
        ld_json_pattern = re.compile(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            re.DOTALL,
        )

        import json

        for match in ld_json_pattern.finditer(html):
            try:
                ld_data = json.loads(match.group(1))
                if isinstance(ld_data, list):
                    for item in ld_data:
                        pick = self._parse_ld_idea(item)
                        if pick:
                            picks.append(pick)
                elif isinstance(ld_data, dict):
                    pick = self._parse_ld_idea(ld_data)
                    if pick:
                        picks.append(pick)
            except (json.JSONDecodeError, Exception):
                continue

        # Fallback: extract symbols from idea links in the HTML
        if not picks:
            symbols_found: set[str] = set()
            for m in idea_pattern.finditer(html):
                sym = m.group(1)
                if is_valid_ticker(sym) and sym not in symbols_found:
                    symbols_found.add(sym)

            today = datetime.utcnow().strftime("%Y-%m-%d")
            for sym in list(symbols_found)[: self.max_ideas]:
                picks.append(
                    UnifiedPick(
                        date=today,
                        symbol=sym,
                        pick_type="swing",
                        source="tradingview/ideas",
                        notes="Trending idea on TradingView",
                        url=f"https://www.tradingview.com/symbols/{sym}/ideas/",
                        confidence=0.4,
                    )
                )

        return picks

    def _parse_ld_idea(self, data: dict) -> Optional[UnifiedPick]:
        """Parse a structured data (JSON-LD) idea entry."""
        if data.get("@type") not in ("Article", "CreativeWork", "TechArticle", None):
            # Allow None @type as TradingView might not set it
            pass

        headline = data.get("headline", "") or data.get("name", "")
        description = data.get("description", "") or data.get("articleBody", "")
        date_published = data.get("datePublished", "")
        author = ""
        if isinstance(data.get("author"), dict):
            author = data["author"].get("name", "")
        url = data.get("url", "")

        # Extract symbol from headline or URL
        combined = f"{headline} {description} {url}"
        symbols = []
        for m in re.finditer(r"\b([A-Z]{1,5})\b", combined):
            s = m.group(1)
            if is_valid_ticker(s) and s not in symbols:
                symbols.append(s)

        if not symbols:
            return None

        symbol = symbols[0]

        # Extract date
        if date_published:
            try:
                dt = datetime.fromisoformat(date_published.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                date_str = datetime.utcnow().strftime("%Y-%m-%d")
        else:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Extract price levels from description
        full_text = f"{headline}\n{description}"
        entry = self._extract_price(ENTRY_PATTERN, full_text)
        targets = self._extract_all_targets(full_text)
        stop = self._extract_price(STOP_PATTERN, full_text)

        # Determine type from content
        pick_type = "swing"
        lower = full_text.lower()
        if "breakout" in lower or "breaking" in lower:
            pick_type = "breakout"
        elif "option" in lower or "call" in lower or "put" in lower:
            pick_type = "options"
        elif "short" in lower or "bear" in lower:
            pick_type = "short"

        # Higher confidence if has price levels
        has_levels = sum(1 for x in [entry, targets, stop] if x)
        confidence = 0.4 + (has_levels * 0.15)

        return UnifiedPick(
            date=date_str,
            symbol=symbol,
            pick_type=pick_type,
            entry=entry,
            targets=targets,
            stop=stop,
            source="tradingview/ideas",
            notes=headline[:120] if headline else "",
            url=url,
            author=author,
            confidence=round(confidence, 2),
        )

    @staticmethod
    def _extract_price(pattern: re.Pattern, text: str) -> Optional[float]:
        m = pattern.search(text)
        if m:
            try:
                return float(m.group(1))
            except (ValueError, IndexError):
                pass
        return None

    @staticmethod
    def _extract_all_targets(text: str) -> list[float]:
        matches = TARGET_PATTERN.findall(text)
        targets = []
        for m in matches:
            try:
                val = float(m)
                if val > 0 and val not in targets:
                    targets.append(val)
            except ValueError:
                pass
        return sorted(targets)
