import logging
from typing import Any, cast

from src.services import data_provider as dp
from src.services.market_data import _get_cached, _set_cache

logger = logging.getLogger(__name__)


def get_ticker_news(symbol: str) -> list[dict[str, Any]]:
    cache_key = f"news:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        if isinstance(cached, list):
            return cast(list[dict[str, Any]], cached)
        return []

    try:
        raw = dp.get_company_news(symbol, days_back=7)
        logger.info("News for %s: got %d raw items", symbol, len(raw))
        articles = []
        for item in raw[:10]:
            title = item.get("headline", "")
            if not title:
                continue

            articles.append(
                {
                    "title": title,
                    "publisher": item.get("source", ""),
                    "link": item.get("url", ""),
                    "published": item.get("datetime", 0),
                    "thumbnail": item.get("image", ""),
                    "summary": item.get("summary", ""),
                    "related": [item.get("related", "")] if item.get("related") else [],
                }
            )

        logger.info("News for %s: parsed %d articles", symbol, len(articles))
        _set_cache(cache_key, articles)
        return articles
    except Exception as e:
        logger.error("News fetch error for %s: %s", symbol, e)
        return []


def get_market_news(symbols: list[str] | None = None) -> list[dict[str, Any]]:
    if not symbols:
        symbols = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]

    all_news = []
    seen_titles = set()
    for sym in symbols[:8]:
        articles = get_ticker_news(sym)
        for a in articles:
            if a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                a["symbol"] = sym
                all_news.append(a)

    all_news.sort(key=lambda x: x.get("published", 0), reverse=True)
    return all_news[:30]


# ── Scheduler-friendly pre-fetch ─────────────────────────────

_DEFAULT_NEWS_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]


def refresh_news_cache():
    """Pre-fetch news for the default 8 symbols so /api/news is instant.

    Called by the background scheduler every ~15 min.  Each symbol that
    already has a fresh cache entry is skipped by get_ticker_news().
    """
    logger.info("refresh_news_cache: pre-fetching news for %d symbols", len(_DEFAULT_NEWS_SYMBOLS))
    for sym in _DEFAULT_NEWS_SYMBOLS:
        try:
            get_ticker_news(sym)
        except Exception:
            logger.exception("refresh_news_cache: failed for %s", sym)
    logger.info("refresh_news_cache: done")
