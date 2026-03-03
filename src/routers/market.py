from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from src.services.market_data import fetch_live_quotes, fetch_sparklines, get_cache_status

router = APIRouter(prefix="/api/market", tags=["market"])

TICKER_SYMBOLS = [
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "NFLX", "AMD", "XOM", "LLY", "BABA", "TSM",
]

FEATURED_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META",
    "BABA", "TSM", "GOOGL", "JPM",
]


@router.get("/ticker")
def get_ticker_data():
    return fetch_live_quotes(TICKER_SYMBOLS)


@router.get("/featured")
def get_featured_stocks():
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_quotes = pool.submit(fetch_live_quotes, FEATURED_SYMBOLS)
        f_sparks = pool.submit(fetch_sparklines, FEATURED_SYMBOLS)
        quotes = f_quotes.result()
        sparklines = f_sparks.result()
    for q in quotes:
        q["sparkline"] = sparklines.get(q["symbol"], [])
    return quotes


@router.get("/cache-status")
def cache_status():
    return get_cache_status()
