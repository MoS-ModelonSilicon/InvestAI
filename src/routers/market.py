from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from src.services.market_data import fetch_live_quotes, fetch_sparklines, get_cache_status

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
    """Combined endpoint: ticker + featured in one round trip."""
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

    return {"ticker": ticker, "featured": featured}


@router.get("/cache-status")
def cache_status():
    return get_cache_status()
