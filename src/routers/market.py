import logging
import threading

from fastapi import APIRouter

from src.services.market_data import fetch_live_quotes, fetch_sparklines, get_cache_status
from src.services.persistence import load_home_snapshot, save_home_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

TICKER_SYMBOLS = [
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN",
]

FEATURED_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL",
]


@router.get("/ticker")
def get_ticker_data():
    return fetch_live_quotes(TICKER_SYMBOLS)


@router.get("/featured")
def get_featured_stocks():
    quotes = fetch_live_quotes(FEATURED_SYMBOLS)
    sparks = fetch_sparklines(FEATURED_SYMBOLS)
    for q in quotes:
        q["sparkline"] = sparks.get(q["symbol"], [])
    return quotes


@router.get("/home")
def get_home_data():
    """Combined endpoint: ticker + featured in one round trip.

    Offline-first strategy: if the in-memory cache is cold (server just
    restarted and external APIs are slow), return the last DB-persisted
    snapshot immediately so the user never sees a long spinner.
    Fresh data replaces the snapshot once it arrives via the background
    scheduler (every 2 min).
    """
    all_syms = list(dict.fromkeys(TICKER_SYMBOLS + FEATURED_SYMBOLS))
    quotes = fetch_live_quotes(all_syms)
    quote_map = {q["symbol"]: q for q in quotes}

    ticker = [quote_map[s] for s in TICKER_SYMBOLS if s in quote_map]
    sparks = fetch_sparklines(FEATURED_SYMBOLS)
    featured = []
    for s in FEATURED_SYMBOLS:
        if s in quote_map:
            entry = {**quote_map[s], "sparkline": sparks.get(s, [])}
            featured.append(entry)

    result = {"ticker": ticker, "featured": featured}

    # If we got real data, persist it for next cold start
    if ticker:
        threading.Thread(
            target=save_home_snapshot, args=(result,),
            daemon=True, name="save-home-snap"
        ).start()
        return result

    # Cache is cold — serve last known DB snapshot instead of empty response
    logger.info("Market cache cold — serving DB snapshot")
    snapshot = load_home_snapshot()
    if snapshot and snapshot.get("ticker"):
        snapshot["_stale"] = True  # signal to frontend that data is cached
        return snapshot

    return result  # truly empty — nothing in DB either


@router.get("/cache-status")
def cache_status():
    return get_cache_status()
