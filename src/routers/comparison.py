import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Query

from src.services.stock_detail import get_stock_detail, get_price_history
from src.services.market_data import format_market_cap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compare", tags=["comparison"])


def _fetch_detail(sym: str):
    try:
        info = get_stock_detail(sym)
        if info:
            info["market_cap_fmt"] = format_market_cap(info.get("market_cap", 0))
        return sym, info
    except Exception as e:
        logger.warning("compare detail error for %s: %s", sym, e)
        return sym, None


def _fetch_history(sym: str):
    try:
        hist = get_price_history(sym, period="1y", interval="1d")
        if hist and hist.get("close"):
            first = hist["close"][0]
            if first > 0:
                return sym, {
                    "dates": hist["dates"],
                    "normalized": [round((v / first - 1) * 100, 2) for v in hist["close"]],
                }
        return sym, None
    except Exception as e:
        logger.warning("compare history error for %s: %s", sym, e)
        return sym, None


@router.get("")
def compare_stocks(symbols: str = Query(..., description="Comma-separated symbols")):
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:4]

    stocks = []
    histories = {}

    with ThreadPoolExecutor(max_workers=len(sym_list) * 2) as pool:
        detail_futures = {pool.submit(_fetch_detail, s): s for s in sym_list}
        hist_futures = {pool.submit(_fetch_history, s): s for s in sym_list}

        for fut in as_completed(detail_futures):
            sym, info = fut.result()
            if info:
                stocks.append(info)

        for fut in as_completed(hist_futures):
            sym, data = fut.result()
            if data:
                histories[sym] = data

    sym_order = {s: i for i, s in enumerate(sym_list)}
    stocks.sort(key=lambda x: sym_order.get(x.get("symbol", ""), 99))

    return {"stocks": stocks, "histories": histories}
