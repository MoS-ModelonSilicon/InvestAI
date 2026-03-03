from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Watchlist, Holding
from src.services.news import get_market_news, get_ticker_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("")
def market_news(db: Session = Depends(get_db)):
    watchlist = db.query(Watchlist).all()
    holdings = db.query(Holding).all()
    symbols = list(set(
        [w.symbol for w in watchlist] + [h.symbol for h in holdings]
    ))
    if not symbols:
        symbols = None
    return get_market_news(symbols)


@router.get("/{symbol}")
def ticker_news(symbol: str):
    return get_ticker_news(symbol.upper())
