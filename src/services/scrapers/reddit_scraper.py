"""
Reddit scraper: fetches trade ideas from r/wallstreetbets, r/stocks, r/options,
r/stockmarket using the **public JSON API** (no auth needed).

Approach:
- Append `.json` to any Reddit listing URL
- Set a proper User-Agent (Reddit requires this)
- Parse post titles + selftexts for ticker mentions ($AAPL, AAPL, etc.)
- Heuristics to identify bullish/bearish sentiment and extract price levels
"""

import logging
import re
import time
from datetime import datetime, UTC
from typing import Optional

import requests

from .base import BaseScraper, UnifiedPick, is_valid_ticker, PROXIES

logger = logging.getLogger(__name__)

# Subreddits to scan, in priority order
SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "options",
    "stockmarket",
    "investing",
]

# Flairs that indicate trade ideas/DD
RELEVANT_FLAIRS = {
    "dd",
    "due diligence",
    "discussion",
    "yolo",
    "daily discussion",
    "technical analysis",
    "fundamentals",
    "stock",
    "trades",
    "options",
    "swing",
    "chart",
    "analysis",
    "catalyst",
}

HEADERS = {
    "User-Agent": "InvestAI-PicksScraper/1.0 (educational stock-research bot)",
}

# Regex to find tickers: $AAPL, $TSLA, or standalone 1-5 letter uppercase words
TICKER_PATTERN = re.compile(
    r"(?:"
    r"\$([A-Z]{1,5})"  # $AAPL style
    r"|"
    r"\b([A-Z]{2,5})\b"  # Standalone uppercase 2-5 letters
    r")",
)

# Price pattern: "PT $150", "target $150", "entry at $25", "stop at $20"
PRICE_PATTERN = re.compile(
    r"(?:price\s*target|PT|target|entry|buy\s*(?:at|around|near)?|stop(?:\s*loss)?)\s*"
    r"(?:is\s*|at\s*|of\s*|around\s*|near\s*|:?\s*)"
    r"\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)

ENTRY_PATTERN = re.compile(
    r"(?:entry|buy\s*(?:at|around|near)?|bought\s*(?:at)?|avg|average|cost\s*basis)\s*"
    r"(?:is\s*|at\s*|of\s*|around\s*|near\s*|:?\s*)"
    r"\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)

TARGET_PATTERN = re.compile(
    r"(?:price\s*target|PT|target|TP|take\s*profit)\s*"
    r"(?:\d\s*[:=]\s*)?"
    r"(?:is\s*|at\s*|of\s*|around\s*|near\s*|:?\s*)"
    r"\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)

STOP_PATTERN = re.compile(
    r"(?:stop(?:\s*loss)?|SL|cut\s*loss)\s*"
    r"(?:is\s*|at\s*|of\s*|around\s*|near\s*|:?\s*)"
    r"\$?([\d]+(?:\.[\d]{1,2})?)",
    re.IGNORECASE,
)

# Minimum upvotes to consider a post (filters noise)
MIN_UPVOTES = 10
# Max posts to fetch per subreddit per scrape
MAX_POSTS_PER_SUB = 50


def _extract_tickers(text: str) -> list[str]:
    """Extract unique valid tickers from text."""
    matches = TICKER_PATTERN.findall(text)
    tickers = []
    seen = set()
    for dollar_match, bare_match in matches:
        t = (dollar_match or bare_match).strip().upper()
        if t and t not in seen and is_valid_ticker(t):
            seen.add(t)
            tickers.append(t)
    return tickers


def _extract_price(pattern: re.Pattern, text: str) -> Optional[float]:
    """Extract first price matching a regex pattern."""
    m = pattern.search(text)
    if m:
        try:
            return float(m.group(1))
        except (ValueError, IndexError):
            pass
    return None


def _extract_all_targets(text: str) -> list[float]:
    """Extract all target prices from text."""
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


def _guess_pick_type(title: str, selftext: str, flair: str) -> str:
    """Heuristic to classify the pick type."""
    combined = (title + " " + selftext + " " + flair).lower()
    if any(w in combined for w in ("option", "call", "put", "strike", "expir", "dte", "contract")):
        return "options"
    if any(w in combined for w in ("swing", "multi-day", "hold for", "week", "month")):
        return "swing"
    if any(w in combined for w in ("breakout", "breaking out", "resistance", "all time high")):
        return "breakout"
    if any(w in combined for w in ("short", "puts", "bearish", "drop")):
        return "short"
    return "swing"  # default


class RedditScraper(BaseScraper):
    """
    Scrapes Reddit stock subreddits for trade ideas using the public JSON API.
    No authentication required - just needs a proper User-Agent header.
    """

    name = "reddit"

    def __init__(
        self,
        subreddits: Optional[list[str]] = None,
        min_upvotes: int = MIN_UPVOTES,
        max_per_sub: int = MAX_POSTS_PER_SUB,
        sort: str = "hot",  # hot, new, top, rising
        time_filter: str = "week",  # hour, day, week, month, year, all
    ):
        self.subreddits = subreddits or SUBREDDITS
        self.min_upvotes = min_upvotes
        self.max_per_sub = max_per_sub
        self.sort = sort
        self.time_filter = time_filter

    def fetch_picks(self) -> list[UnifiedPick]:
        all_picks: list[UnifiedPick] = []
        seen_keys: set[str] = set()

        for sub in self.subreddits:
            try:
                picks = self._scrape_subreddit(sub)
                for p in picks:
                    key = f"{p.symbol}:{p.date}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_picks.append(p)
                # Be nice to Reddit: pause between subreddits
                time.sleep(2)
            except Exception:
                logger.exception("[reddit] failed on r/%s", sub)

        return all_picks

    def _scrape_subreddit(self, subreddit: str) -> list[UnifiedPick]:
        """Fetch posts from a single subreddit and extract picks."""
        params: dict[str, str | int]
        if self.sort in ("top", "controversial"):
            url = f"https://www.reddit.com/r/{subreddit}/{self.sort}.json"
            params = {"limit": self.max_per_sub, "t": self.time_filter}
        else:
            url = f"https://www.reddit.com/r/{subreddit}/{self.sort}.json"
            params = {"limit": self.max_per_sub}

        resp = requests.get(url, headers=HEADERS, params=params, proxies=PROXIES, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        posts = data.get("data", {}).get("children", [])
        picks: list[UnifiedPick] = []

        for post_wrap in posts:
            post = post_wrap.get("data", {})
            pick_list = self._parse_post(post, subreddit)
            picks.extend(pick_list)

        return picks

    def _parse_post(self, post: dict, subreddit: str) -> list[UnifiedPick]:
        """Parse a single Reddit post into zero or more picks."""
        # Filter by upvotes
        score = post.get("score", 0)
        if score < self.min_upvotes:
            return []

        title = post.get("title", "")
        selftext = post.get("selftext", "")
        flair = post.get("link_flair_text", "") or ""
        permalink = post.get("permalink", "")
        author = post.get("author", "")
        created_utc = post.get("created_utc", 0)

        # Convert timestamp to date
        if created_utc:
            dt = datetime.fromtimestamp(created_utc, tz=UTC)
            date_str = dt.strftime("%Y-%m-%d")
        else:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Combine text for analysis
        full_text = f"{title}\n{selftext}"

        # Extract tickers
        tickers = _extract_tickers(full_text)
        if not tickers:
            return []

        # Extract price levels
        entry = _extract_price(ENTRY_PATTERN, full_text)
        targets = _extract_all_targets(full_text)
        stop = _extract_price(STOP_PATTERN, full_text)
        pick_type = _guess_pick_type(title, selftext, flair)

        # Build note from title (truncated)
        note = title[:120] if title else ""

        post_url = f"https://reddit.com{permalink}" if permalink else ""

        # Confidence heuristic based on data quality + upvotes
        has_entry = entry is not None
        has_targets = len(targets) > 0
        has_stop = stop is not None
        data_quality = (0.3 if has_entry else 0) + (0.3 if has_targets else 0) + (0.2 if has_stop else 0)
        upvote_score = min(score / 500, 0.2)  # cap at 0.2 for 500+ upvotes
        confidence = round(data_quality + upvote_score, 2)

        picks = []
        # If multiple tickers mentioned, create picks for each
        # but only assign price levels to the first (most mentioned) ticker
        for i, ticker in enumerate(tickers[:3]):  # max 3 tickers per post
            pick = UnifiedPick(
                date=date_str,
                symbol=ticker,
                pick_type=pick_type,
                entry=entry if i == 0 else None,
                targets=targets if i == 0 else [],
                stop=stop if i == 0 else None,
                source=f"reddit/r/{subreddit}",
                notes=note,
                url=post_url,
                author=author,
                confidence=confidence if i == 0 else confidence * 0.5,
            )
            picks.append(pick)

        return picks
