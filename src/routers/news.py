from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Watchlist, Holding, User
from src.services.news import get_market_news, get_ticker_news
from src.auth import get_current_user

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("")
def market_news(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    holdings = db.query(Holding).filter(Holding.user_id == user.id).all()
    symbols = list(set([w.symbol for w in watchlist] + [h.symbol for h in holdings]))
    if not symbols:
        return get_market_news(None)
    return get_market_news(symbols)


@router.get("/{symbol}")
def ticker_news(symbol: str):
    return get_ticker_news(symbol.upper())
