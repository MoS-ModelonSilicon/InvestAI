from fastapi import APIRouter, Query

from src.services.stock_detail import get_stock_detail, get_price_history
from src.services.market_data import format_market_cap

router = APIRouter(prefix="/api/compare", tags=["comparison"])


@router.get("")
def compare_stocks(symbols: str = Query(..., description="Comma-separated symbols")):
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:4]

    stocks = []
    for sym in sym_list:
        info = get_stock_detail(sym)
        if info:
            info["market_cap_fmt"] = format_market_cap(info.get("market_cap", 0))
            stocks.append(info)

    histories = {}
    for sym in sym_list:
        hist = get_price_history(sym, period="1y", interval="1d")
        if hist and hist.get("close"):
            first = hist["close"][0]
            if first > 0:
                histories[sym] = {
                    "dates": hist["dates"],
                    "normalized": [round((v / first - 1) * 100, 2) for v in hist["close"]],
                }

    return {"stocks": stocks, "histories": histories}
