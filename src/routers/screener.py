from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Watchlist
from src.schemas.screener import StockResult, WatchlistItem
from src.services.screener import screen_instruments
from src.services.market_data import SECTORS, REGIONS

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("")
def run_screener(
    asset_type: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    pe_min: Optional[float] = None,
    pe_max: Optional[float] = None,
    dividend_yield_min: Optional[float] = None,
    beta_min: Optional[float] = None,
    beta_max: Optional[float] = None,
    page: int = 1,
    per_page: int = 50,
):
    all_results = screen_instruments(
        asset_type=asset_type,
        sector=sector,
        region=region,
        market_cap_min=market_cap_min,
        market_cap_max=market_cap_max,
        pe_min=pe_min,
        pe_max=pe_max,
        dividend_yield_min=dividend_yield_min,
        beta_min=beta_min,
        beta_max=beta_max,
    )
    total = len(all_results)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": all_results[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.get("/sectors")
def list_sectors():
    return {"sectors": SECTORS, "regions": REGIONS}


@router.get("/watchlist", response_model=list[WatchlistItem])
def get_watchlist(db: Session = Depends(get_db)):
    return db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()


@router.get("/watchlist/live")
def get_watchlist_live(db: Session = Depends(get_db)):
    """Watchlist with live prices and change data."""
    items = db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
    from src.services.market_data import fetch_stock_info, format_market_cap
    result = []
    for item in items:
        info = fetch_stock_info(item.symbol)
        if info:
            price = info.get("price", 0)
            result.append({
                "id": item.id,
                "symbol": item.symbol,
                "name": info.get("name", item.name),
                "price": round(price, 2),
                "market_cap_fmt": format_market_cap(info.get("market_cap", 0)),
                "pe_ratio": info.get("pe_ratio"),
                "dividend_yield": info.get("dividend_yield"),
                "beta": info.get("beta"),
                "year_change": info.get("year_change"),
                "sector": info.get("sector", "N/A"),
                "added_at": item.added_at.isoformat() if item.added_at else None,
            })
        else:
            result.append({
                "id": item.id,
                "symbol": item.symbol,
                "name": item.name,
                "price": 0,
                "market_cap_fmt": "N/A",
                "pe_ratio": None,
                "dividend_yield": None,
                "beta": None,
                "year_change": None,
                "sector": "N/A",
                "added_at": item.added_at.isoformat() if item.added_at else None,
            })
    return result


@router.post("/watchlist", response_model=WatchlistItem)
def add_to_watchlist(symbol: str, name: str = "", db: Session = Depends(get_db)):
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
    if existing:
        raise HTTPException(400, "Already in watchlist")
    item = Watchlist(symbol=symbol.upper(), name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/watchlist/{item_id}")
def remove_from_watchlist(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not item:
        raise HTTPException(404, "Not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
