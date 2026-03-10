"""NLP sentiment analysis for news articles.

Uses a financial-domain lexicon (Loughran-McDonald inspired) to score
article titles and summaries as positive / negative / neutral.  No
external NLP libraries required — pure Python keyword matching with
bigram/trigram awareness for financial phrases.
"""

import logging
import re
import time
from typing import Any

from src.services.market_data import _get_cached, _set_cache
from src.services.news import get_ticker_news

logger = logging.getLogger(__name__)

# ── Financial Sentiment Lexicon ──────────────────────────────
# Phrases checked FIRST (order: longest match wins), then single words.

_POSITIVE_PHRASES: list[str] = [
    "all time high",
    "all-time high",
    "beat expectations",
    "beats estimates",
    "beats expectations",
    "better than expected",
    "blowout earnings",
    "bought the dip",
    "breakout above",
    "bullish momentum",
    "buy the dip",
    "dividend increase",
    "dividend hike",
    "double upgrade",
    "earnings beat",
    "earnings surprise",
    "exceeds expectations",
    "guidance raise",
    "market rally",
    "new high",
    "outperform rating",
    "positive outlook",
    "price target raised",
    "profit growth",
    "raises guidance",
    "record earnings",
    "record high",
    "record revenue",
    "revenue beat",
    "revenue growth",
    "share buyback",
    "short squeeze",
    "stock split",
    "strong buy",
    "strong demand",
    "strong earnings",
    "strong growth",
    "strong quarter",
    "top pick",
    "upgraded to buy",
    "upgrades to buy",
    "upside potential",
    "upside surprise",
]

_NEGATIVE_PHRASES: list[str] = [
    "all time low",
    "all-time low",
    "bankruptcy filing",
    "bear market",
    "class action",
    "cut guidance",
    "cuts guidance",
    "data breach",
    "death cross",
    "debt crisis",
    "downgraded to sell",
    "downgrades to sell",
    "earnings miss",
    "earnings warning",
    "fraud allegations",
    "guidance cut",
    "hostile takeover",
    "layoffs announced",
    "lowers guidance",
    "margin compression",
    "mass layoff",
    "missed estimates",
    "misses estimates",
    "negative outlook",
    "price target cut",
    "price target lowered",
    "profit warning",
    "recall issued",
    "revenue decline",
    "revenue miss",
    "sec investigation",
    "sell rating",
    "shareholder lawsuit",
    "supply chain disruption",
    "trade war",
    "under investigation",
    "weak demand",
    "weak earnings",
    "weak guidance",
    "worse than expected",
]

_POSITIVE_WORDS: set[str] = {
    "accelerate",
    "advance",
    "approval",
    "attractive",
    "beat",
    "beats",
    "boom",
    "breakthrough",
    "bullish",
    "buy",
    "climb",
    "crush",
    "dividend",
    "efficient",
    "exceed",
    "exceeds",
    "expand",
    "expansion",
    "gain",
    "gains",
    "grow",
    "growing",
    "growth",
    "high",
    "improve",
    "improved",
    "innovation",
    "jump",
    "jumps",
    "launch",
    "momentum",
    "opportunity",
    "optimism",
    "outperform",
    "outperforms",
    "profit",
    "profitable",
    "promising",
    "rally",
    "rebound",
    "record",
    "recovery",
    "resilient",
    "revenue",
    "rise",
    "rises",
    "robust",
    "soar",
    "soars",
    "spike",
    "strength",
    "strong",
    "success",
    "surge",
    "surges",
    "surpass",
    "top",
    "upgrade",
    "upgraded",
    "upside",
    "upturn",
    "win",
    "winning",
}

_NEGATIVE_WORDS: set[str] = {
    "bankrupt",
    "bankruptcy",
    "bearish",
    "blow",
    "bust",
    "cancel",
    "collapse",
    "concern",
    "crash",
    "crisis",
    "cut",
    "cuts",
    "danger",
    "debt",
    "decline",
    "declining",
    "default",
    "deficit",
    "delay",
    "disappointing",
    "downgrade",
    "downgraded",
    "downturn",
    "drop",
    "drops",
    "dump",
    "fall",
    "falling",
    "fears",
    "fraud",
    "headwind",
    "inflation",
    "investigation",
    "lawsuit",
    "layoff",
    "layoffs",
    "liquidation",
    "litigation",
    "lose",
    "loss",
    "losses",
    "miss",
    "missed",
    "negative",
    "penalty",
    "plummet",
    "plunge",
    "plunges",
    "pressure",
    "problem",
    "probe",
    "pullback",
    "recall",
    "recession",
    "restructuring",
    "risk",
    "scandal",
    "sell",
    "selloff",
    "sell-off",
    "shortage",
    "shrink",
    "shutdown",
    "sink",
    "slump",
    "struggle",
    "subpoena",
    "tariff",
    "threat",
    "trouble",
    "tumble",
    "underperform",
    "volatile",
    "volatility",
    "warning",
    "weak",
    "weakness",
    "worries",
    "worse",
    "worst",
    "write-off",
    "writedown",
}

# ── Negation handling ────────────────────────────────────────
_NEGATION_WORDS: set[str] = {
    "no",
    "not",
    "never",
    "neither",
    "nobody",
    "nothing",
    "nowhere",
    "nor",
    "cannot",
    "can't",
    "don't",
    "doesn't",
    "didn't",
    "won't",
    "wouldn't",
    "shouldn't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "hasn't",
    "haven't",
    "hadn't",
    "without",
    "despite",
    "fail",
    "fails",
    "failed",
    "unlikely",
}

_INTENSIFIERS: set[str] = {
    "very",
    "extremely",
    "significantly",
    "substantially",
    "massive",
    "huge",
    "tremendous",
    "sharply",
    "dramatically",
    "strongly",
    "major",
}

_WORD_RE = re.compile(r"[a-z][a-z'-]+")


def _score_text(text: str) -> float:
    """Score a text string. Returns value in [-1.0, 1.0]."""
    if not text:
        return 0.0

    lower = text.lower()
    score = 0.0

    # Phase 1: multi-word phrase matching (stronger signal)
    for phrase in _POSITIVE_PHRASES:
        if phrase in lower:
            score += 1.5

    for phrase in _NEGATIVE_PHRASES:
        if phrase in lower:
            score -= 1.5

    # Phase 2: single-word matching with negation awareness
    words = _WORD_RE.findall(lower)
    prev_negation = False
    prev_intensifier = False

    for word in words:
        is_neg = word in _NEGATION_WORDS
        is_int = word in _INTENSIFIERS

        if is_neg:
            prev_negation = True
            continue
        if is_int:
            prev_intensifier = True
            continue

        multiplier = 1.5 if prev_intensifier else 1.0
        if prev_negation:
            multiplier *= -0.5  # Negation flips and weakens

        if word in _POSITIVE_WORDS:
            score += 0.5 * multiplier
        elif word in _NEGATIVE_WORDS:
            score -= 0.5 * multiplier

        prev_negation = False
        prev_intensifier = False

    # Normalise to [-1, 1]
    if abs(score) > 5:
        score = 5.0 if score > 0 else -5.0
    return round(score / 5.0, 3)


def analyze_article_sentiment(
    title: str,
    summary: str = "",
) -> dict[str, Any]:
    """Analyse a single article and return sentiment score + label.

    Returns
    -------
    dict with keys: score (-1..1), label (Bullish/Bearish/Neutral),
    magnitude (0..1).
    """
    # Title is weighted 2× more than summary (headlines drive sentiment)
    title_score = _score_text(title)
    summary_score = _score_text(summary[:500] if summary else "")
    combined = title_score * 0.65 + summary_score * 0.35

    magnitude = round(abs(combined), 3)
    if combined >= 0.15:
        label = "Bullish"
    elif combined <= -0.15:
        label = "Bearish"
    else:
        label = "Neutral"

    return {
        "score": round(combined, 3),
        "label": label,
        "magnitude": magnitude,
    }


def get_symbol_sentiment(symbol: str) -> dict[str, Any]:
    """Get aggregated sentiment for a symbol from its news articles.

    Uses cached news data to avoid extra API calls.
    """
    cache_key = f"sentiment:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None and isinstance(cached, dict):
        return dict(cached)

    articles = get_ticker_news(symbol)
    if not articles:
        result: dict[str, Any] = {
            "symbol": symbol,
            "overall_score": 0.0,
            "overall_label": "Neutral",
            "article_count": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "articles": [],
            "updated_at": int(time.time()),
        }
        _set_cache(cache_key, result)
        return result

    scored_articles: list[dict[str, Any]] = []
    total_score = 0.0
    bullish = 0
    bearish = 0
    neutral = 0

    for article in articles:
        title = article.get("title", "")
        summary = article.get("summary", "")
        sentiment = analyze_article_sentiment(title, summary)

        scored_articles.append(
            {
                "title": title,
                "publisher": article.get("publisher", ""),
                "published": article.get("published", 0),
                "link": article.get("link", ""),
                "sentiment_score": sentiment["score"],
                "sentiment_label": sentiment["label"],
            }
        )
        total_score += sentiment["score"]
        if sentiment["label"] == "Bullish":
            bullish += 1
        elif sentiment["label"] == "Bearish":
            bearish += 1
        else:
            neutral += 1

    count = len(scored_articles)
    avg_score = round(total_score / count, 3) if count else 0.0

    if avg_score >= 0.10:
        overall_label = "Bullish"
    elif avg_score <= -0.10:
        overall_label = "Bearish"
    else:
        overall_label = "Neutral"

    result = {
        "symbol": symbol,
        "overall_score": avg_score,
        "overall_label": overall_label,
        "article_count": count,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "articles": scored_articles,
        "updated_at": int(time.time()),
    }
    _set_cache(cache_key, result)
    return result


def get_sentiment_summary(symbol: str) -> dict[str, Any]:
    """Lightweight sentiment summary (no individual articles).

    Used by the screener snapshot builder to avoid bloating each row.
    """
    full = get_symbol_sentiment(symbol)
    return {
        "score": full["overall_score"],
        "label": full["overall_label"],
        "article_count": full["article_count"],
        "bullish_pct": (round(full["bullish_count"] / full["article_count"] * 100) if full["article_count"] else 0),
    }
