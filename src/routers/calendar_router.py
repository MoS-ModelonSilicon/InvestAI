from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Watchlist, Holding, User
from src.services.calendar_service import get_earnings_calendar, get_economic_events
from src.auth import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/earnings")
def earnings_calendar(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    holdings = db.query(Holding).filter(Holding.user_id == user.id).all()
    symbols = list(set(
        [w.symbol for w in watchlist] + [h.symbol for h in holdings]
    ))
    if not symbols:
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "JNJ", "XOM"]
    return get_earnings_calendar(symbols)


@router.get("/economic")
def economic_events():
    return get_economic_events()
