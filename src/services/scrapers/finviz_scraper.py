"""
Finviz screener scraper: fetches trade ideas from Finviz screener based on
pre-defined technical setups.

Approach:
- Finviz screener at https://finviz.com/screener.ashx has freely available HTML tables
- We use various screener filter URLs for breakout/swing/technical patterns
- Parse the resulting HTML table, extract ticker + current price + change + pattern
- No API key needed for basic data
"""

import logging
import re
from datetime import datetime
from typing import Optional

import requests

from .base import BaseScraper, UnifiedPick, is_valid_ticker, PROXIES

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Pre-defined screener URLs for different setups
# Each URL encodes Finviz filter parameters for specific patterns
SCREENER_CONFIGS = {
    "breakout_new_high": {
        # Stocks near 52-week high, high volume, positive momentum
        "url": "https://finviz.com/screener.ashx",
        "params": {
            "v": "111",  # Overview view
            "f": "cap_midover,sh_avgvol_o500,sh_price_o5,ta_highlow52w_nh,ta_sma20_pa,ta_sma50_pa",
            "ft": "4",  # Technical filters
            "o": "-change",  # Sort by change descending
        },
        "pick_type": "breakout",
        "note_prefix": "New 52w High + Above SMA20/50",
    },
    "oversold_bounce": {
        # Oversold stocks starting to bounce (RSI < 30 but positive change today)
        "url": "https://finviz.com/screener.ashx",
        "params": {
            "v": "111",
            "f": "cap_midover,sh_avgvol_o300,sh_price_o5,ta_rsi_os30,ta_change_u",
            "ft": "4",
            "o": "rsi",
        },
        "pick_type": "swing",
        "note_prefix": "Oversold Bounce (RSI<30, green)",
    },
    "channel_up": {
        # Stocks with channel up pattern
        "url": "https://finviz.com/screener.ashx",
        "params": {
            "v": "111",
            "f": "cap_midover,sh_avgvol_o300,sh_price_o5,ta_pattern_channelup",
            "ft": "4",
            "o": "-change",
        },
        "pick_type": "swing",
        "note_prefix": "Channel Up Pattern",
    },
    "double_bottom": {
        # Double bottom pattern - classic reversal
        "url": "https://finviz.com/screener.ashx",
        "params": {
            "v": "111",
            "f": "cap_midover,sh_avgvol_o300,sh_price_o5,ta_pattern_doublebottom",
            "ft": "4",
            "o": "-change",
        },
        "pick_type": "swing",
        "note_prefix": "Double Bottom Pattern",
    },
    "unusual_volume": {
        # Unusual volume surge (volume > 2x average)
        "url": "https://finviz.com/screener.ashx",
        "params": {
            "v": "111",
            "f": "cap_midover,sh_price_o5,sh_relvol_o2,ta_change_u3",
            "ft": "4",
            "o": "-volume",
        },
        "pick_type": "breakout",
        "note_prefix": "Unusual Volume (>2x avg) + 3%+ gain",
    },
}


class FinvizScraper(BaseScraper):
    """
    Scrapes Finviz screener for stocks matching technical patterns.
    Uses pre-defined screener filter URLs and parses HTML tables.
    """

    name = "finviz"

    def __init__(
        self,
        screens: Optional[list[str]] = None,
        max_per_screen: int = 20,
    ):
        self.screens = screens or list(SCREENER_CONFIGS.keys())
        self.max_per_screen = max_per_screen

    def fetch_picks(self) -> list[UnifiedPick]:
        all_picks: list[UnifiedPick] = []
        seen_symbols: set[str] = set()

        for screen_name in self.screens:
            config = SCREENER_CONFIGS.get(screen_name)
            if not config:
                continue

            try:
                picks = self._scrape_screen(config)
                for p in picks:
                    if p.symbol not in seen_symbols:
                        seen_symbols.add(p.symbol)
                        all_picks.append(p)

                import time

                time.sleep(2)  # Be nice to Finviz
            except Exception:
                logger.exception("[finviz] failed on screen %s", screen_name)

        return all_picks

    def _scrape_screen(self, config: dict) -> list[UnifiedPick]:
        """Fetch and parse a single screener result page."""
        url = config["url"]
        params = config["params"]
        pick_type = config["pick_type"]
        note_prefix = config["note_prefix"]

        try:
            resp = requests.get(
                url,
                params=params,
                headers=HEADERS,
                proxies=PROXIES,
                timeout=30,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception:
            logger.exception("[finviz] HTTP request failed for %s", note_prefix)
            return []

        return self._parse_screener_html(html, pick_type, note_prefix)

    def _parse_screener_html(self, html: str, pick_type: str, note_prefix: str) -> list[UnifiedPick]:
        """Parse Finviz screener HTML table to extract stock data."""
        picks: list[UnifiedPick] = []
        today = datetime.utcnow().strftime("%Y-%m-%d")

        # Finviz renders stock data in <a class="screener-link-primary"> for tickers
        # and <td> cells for other data in the overview table (view=111)
        #
        # The table structure is:
        # No. | Ticker | Company | Sector | Industry | Country | Market Cap |
        # P/E | Price | Change | Volume

        # Find the main results table - Finviz uses class="table-light" or id="screener-views-table"
        # The actual data rows have class "screener_..." or are in specific table blocks

        # Strategy: find all ticker links and their surrounding row data
        ticker_pattern = re.compile(
            r'<a\s+[^>]*href="quote\.ashx\?t=([A-Z]+)[^"]*"[^>]*class="screener-link-primary"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )

        # Price and change pattern - look for the price and change columns
        # In Finviz overview mode (v=111), each row has: No, Ticker, Company, Sector, Industry,
        # Country, MarketCap, P/E, Price, Change, Volume
        # We'll extract per-ticker using a row-by-row approach

        # First, find all rows containing ticker links
        # Finviz wraps each stock row in <tr> with alternating bg colors
        row_pattern = re.compile(
            r"<tr[^>]*>\s*<td[^>]*>(\d+)</td>"  # Row number
            r".*?quote\.ashx\?t=([A-Z]+)"  # Ticker
            r".*?</tr>",
            re.DOTALL,
        )

        # Simpler approach: extract all ticker names, then get price data
        # from the subsequent cells
        tickers_found = ticker_pattern.findall(html)

        if not tickers_found:
            # Fallback: try a broader pattern
            tickers_found = re.findall(
                r"quote\.ashx\?t=([A-Z]{1,5})",
                html,
            )
            tickers_found = [(t, t) for t in dict.fromkeys(tickers_found)]

        # Extract price data using a more detailed parse
        # Look for table cells near ticker names
        for ticker, _display in tickers_found[: self.max_per_screen]:
            symbol = ticker.upper().strip()
            if not is_valid_ticker(symbol):
                continue

            # Try to extract price from the HTML context around the ticker
            price = self._extract_price_for_ticker(html, symbol)

            entry = price
            targets = []
            stop = None

            if entry:
                # Generate conservative targets based on pattern type
                if pick_type == "breakout":
                    targets = [
                        round(entry * 1.05, 2),
                        round(entry * 1.10, 2),
                        round(entry * 1.15, 2),
                    ]
                    stop = round(entry * 0.95, 2)
                else:
                    # Swing: tighter targets
                    targets = [
                        round(entry * 1.03, 2),
                        round(entry * 1.07, 2),
                    ]
                    stop = round(entry * 0.97, 2)

            picks.append(
                UnifiedPick(
                    date=today,
                    symbol=symbol,
                    pick_type=pick_type,
                    entry=entry,
                    targets=targets,
                    stop=stop,
                    source="finviz/screener",
                    notes=note_prefix,
                    url=f"https://finviz.com/quote.ashx?t={symbol}",
                    confidence=0.5,  # Finviz screens are decent quality signals
                )
            )

        return picks

    def _extract_price_for_ticker(self, html: str, symbol: str) -> Optional[float]:
        """Try to extract the current price for a ticker from the HTML."""
        # Look for price data near the ticker reference
        # Finviz format: ticker appears as link, then data cells follow
        # The price cell typically has class "screener-link" and contains a number
        pattern = re.compile(
            rf"quote\.ashx\?t={re.escape(symbol)}"
            r".*?"
            # Look for price-like numbers after the ticker (within ~2000 chars)
            r"<td[^>]*>\s*<(?:a|span)[^>]*>\s*(\d+\.?\d*)\s*</(?:a|span)>\s*</td>",
            re.DOTALL,
        )

        # Search in a window after the ticker
        idx = html.find(f"t={symbol}")
        if idx == -1:
            return None

        window = html[idx : idx + 2000]

        # Find all number-like values in <td><a> or <td><span> cells
        cell_values = re.findall(
            r"<td[^>]*>\s*<(?:a|span)[^>]*>\s*([\d,]+\.?\d*)\s*</(?:a|span)>\s*</td>",
            window,
        )

        for val in cell_values:
            try:
                num = float(val.replace(",", ""))
                # Reasonable stock price range
                if 1 < num < 10000:
                    return round(num, 2)
            except ValueError:
                continue

        return None
