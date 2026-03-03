import logging
from datetime import datetime

import yfinance as yf
from src.services.market_data import _get_cached, _set_cache

logger = logging.getLogger(__name__)


def get_ticker_news(symbol: str) -> list[dict]:
    cache_key = f"news:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        raw = ticker.news or []
        logger.info("News for %s: got %d raw items", symbol, len(raw))
        articles = []
        for item in raw[:10]:
            content = item.get("content") or item
            title = content.get("title", "") or item.get("title", "")
            if not title:
                continue

            provider = content.get("provider") or {}
            publisher = provider.get("displayName", "") or item.get("publisher", "")

            pub_date = content.get("pubDate", "") or ""
            published_ts = 0
            if pub_date:
                try:
                    dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    published_ts = int(dt.timestamp())
                except Exception:
                    published_ts = item.get("providerPublishTime", 0)
            else:
                published_ts = item.get("providerPublishTime", 0)

            canonical = content.get("canonicalUrl") or {}
            click_through = content.get("clickThroughUrl") or {}
            link = click_through.get("url", "") or canonical.get("url", "") or item.get("link", "")

            thumbnail_url = ""
            thumb_data = content.get("thumbnail") or item.get("thumbnail") or {}
            if isinstance(thumb_data, dict):
                resolutions = thumb_data.get("resolutions", [])
                if resolutions and isinstance(resolutions, list):
                    thumbnail_url = resolutions[0].get("url", "")

            articles.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "published": published_ts,
                "thumbnail": thumbnail_url,
                "summary": content.get("summary", ""),
                "related": item.get("relatedTickers", []),
            })

        logger.info("News for %s: parsed %d articles", symbol, len(articles))
        _set_cache(cache_key, articles)
        return articles
    except Exception as e:
        logger.error("News fetch error for %s: %s", symbol, e)
        return []


def get_market_news(symbols: list[str] = None) -> list[dict]:
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
