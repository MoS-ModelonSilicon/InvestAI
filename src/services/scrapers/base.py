"""
Base scraper module: defines the unified pick schema and abstract base class
for all data-source scrapers.
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Intel corporate proxy – same env-var pattern as data_provider.py
USE_INTEL_PROXY = os.getenv("USE_INTEL_PROXY", "").lower() in ("1", "true", "yes")
PROXY_URL = "http://proxy-dmz.intel.com:912"
PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if USE_INTEL_PROXY else {}


class UnifiedPick:
    """Canonical pick format expected by picks_tracker.py and discord-picks.json."""

    __slots__ = (
        "author",
        "confidence",
        "date",
        "entry",
        "notes",
        "source",
        "stop",
        "symbol",
        "targets",
        "type",
        "url",
    )

    def __init__(
        self,
        *,
        date: str,
        symbol: str,
        pick_type: str = "breakout",
        entry: Optional[float] = None,
        targets: Optional[list[float]] = None,
        stop: Optional[float] = None,
        source: str = "unknown",
        notes: str = "",
        url: str = "",
        author: str = "",
        confidence: Optional[float] = None,
    ):
        self.date = date
        self.symbol = symbol.upper().strip()
        self.type = pick_type
        self.entry = entry
        self.targets = targets or []
        self.stop = stop
        self.source = source
        self.notes = notes
        self.url = url
        self.author = author
        self.confidence = confidence  # 0-1 score for quality ranking

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "date": self.date,
            "symbol": self.symbol,
            "type": self.type,
            "entry": self.entry,
            "targets": self.targets,
            "stop": self.stop,
            "source": self.source,
            "notes": self.notes,
        }
        if self.url:
            d["url"] = self.url
        if self.author:
            d["author"] = self.author
        if self.confidence is not None:
            d["confidence"] = self.confidence
        return d


# --- Common helpers for ticker validation ---

FALSE_TICKERS = frozenset(
    {
        "I",
        "A",
        "AT",
        "AM",
        "PM",
        "DD",
        "IT",
        "ALL",
        "FOR",
        "HE",
        "HAS",
        "BE",
        "SO",
        "ARE",
        "DO",
        "GO",
        "NEW",
        "OLD",
        "BIG",
        "LOW",
        "HIGH",
        "OUT",
        "UP",
        "ONE",
        "TWO",
        "NOW",
        "PUT",
        "RUN",
        "BUY",
        "PT",
        "STOP",
        "GOOD",
        "JUST",
        "HOLD",
        "CALL",
        "PLAY",
        "LONG",
        "POST",
        "CASH",
        "BULL",
        "BEAR",
        "MOON",
        "YOLO",
        "FOMO",
        "IMO",
        "IMHO",
        "TA",
        "OTM",
        "ITM",
        "ATM",
        "DTE",
        "EOD",
        "EOW",
        "EOM",
        "MACD",
        "RSI",
        "EMA",
        "SMA",
        "VWAP",
        "LOD",
        "HOD",
        "PRICE",
        "CURRE",
        "TICKE",
        "YEING",
        "DEC",
        "EST",
        "PST",
        "GDP",
        "CPI",
        "PPI",
        "PCE",
        "FOMC",
        "FED",
        "SEC",
        "IPO",
        "USA",
        "US",
        "EU",
        "UK",
        "API",
        "CEO",
        "CFO",
        "CTO",
        "AND",
        "THE",
        "THIS",
        "THAT",
        "WITH",
        "FROM",
        "WHAT",
        "EDIT",
        "TLDR",
        "TL",
        "DR",
        "PSA",
        "FYI",
        "LFG",
        "LETS",
    }
)


def is_valid_ticker(symbol: str) -> bool:
    """Check if a string looks like a real US stock ticker."""
    s = symbol.strip().upper()
    if not s or len(s) > 5 or len(s) < 1:
        return False
    if not s.isalpha():
        return False
    return s not in FALSE_TICKERS


def today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


class BaseScraper(ABC):
    """Abstract base class for all pick scrapers."""

    name: str = "base"

    @abstractmethod
    def fetch_picks(self) -> list[UnifiedPick]:
        """Fetch picks from the data source. Returns list of UnifiedPick."""
        ...

    def fetch_safe(self) -> list[UnifiedPick]:
        """Wrapper that catches exceptions so one failing source doesn't crash pipeline."""
        try:
            picks = self.fetch_picks()
            logger.info("[%s] fetched %d picks", self.name, len(picks))
            return picks
        except Exception:
            logger.exception("[%s] scraper failed", self.name)
            return []
