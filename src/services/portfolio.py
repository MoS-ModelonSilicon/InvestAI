from sqlalchemy.orm import Session
from src.models import Holding
from src.services.market_data import fetch_stock_info


def calculate_portfolio(db: Session) -> dict:
    holdings = db.query(Holding).all()
    if not holdings:
        return {
            "total_invested": 0,
            "total_value": 0,
            "total_gain_loss": 0,
            "total_gain_loss_pct": 0,
            "holdings": [],
            "sector_allocation": [],
            "best_performer": None,
            "worst_performer": None,
        }

    enriched = []
    total_invested = 0
    total_value = 0
    sector_map = {}
    best = None
    worst = None

    for h in holdings:
        info = fetch_stock_info(h.symbol)
        current_price = info.get("price", 0) if info else 0
        sector = info.get("sector", "N/A") if info else "N/A"

        cost_basis = h.quantity * h.buy_price
        current_val = h.quantity * current_price
        gl = current_val - cost_basis
        gl_pct = (gl / cost_basis * 100) if cost_basis > 0 else 0

        total_invested += cost_basis
        total_value += current_val

        sector_map[sector] = sector_map.get(sector, 0) + current_val

        entry = {
            "id": h.id,
            "symbol": h.symbol,
            "name": h.name or (info.get("name", h.symbol) if info else h.symbol),
            "quantity": h.quantity,
            "buy_price": h.buy_price,
            "buy_date": h.buy_date,
            "notes": h.notes,
            "created_at": h.created_at,
            "current_price": round(current_price, 2),
            "current_value": round(current_val, 2),
            "cost_basis": round(cost_basis, 2),
            "gain_loss": round(gl, 2),
            "gain_loss_pct": round(gl_pct, 2),
            "sector": sector,
        }
        enriched.append(entry)

        if best is None or gl_pct > best[1]:
            best = (h.symbol, gl_pct)
        if worst is None or gl_pct < worst[1]:
            worst = (h.symbol, gl_pct)

    allocation = []
    for sec, val in sorted(sector_map.items(), key=lambda x: x[1], reverse=True):
        allocation.append({
            "sector": sec,
            "value": round(val, 2),
            "pct": round(val / total_value * 100, 1) if total_value > 0 else 0,
        })

    total_gl = total_value - total_invested
    total_gl_pct = (total_gl / total_invested * 100) if total_invested > 0 else 0

    return {
        "total_invested": round(total_invested, 2),
        "total_value": round(total_value, 2),
        "total_gain_loss": round(total_gl, 2),
        "total_gain_loss_pct": round(total_gl_pct, 2),
        "holdings": enriched,
        "sector_allocation": allocation,
        "best_performer": best[0] if best else None,
        "worst_performer": worst[0] if worst else None,
    }


def get_portfolio_performance(db: Session) -> dict:
    """Calculate time-weighted portfolio performance for charting."""
    holdings = db.query(Holding).all()
    if not holdings:
        return {"dates": [], "portfolio": [], "benchmark": []}

    import yfinance as yf
    from datetime import datetime, timedelta
    from src.services.market_data import _get_cached, _set_cache

    cache_key = "portfolio_perf"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    earliest = min(h.buy_date for h in holdings)
    start_str = earliest.strftime("%Y-%m-%d")

    spy = yf.Ticker("SPY")
    bench_hist = spy.history(start=start_str, interval="1d")
    if bench_hist.empty:
        return {"dates": [], "portfolio": [], "benchmark": []}

    dates = [d.strftime("%Y-%m-%d") for d in bench_hist.index]
    bench_start = bench_hist["Close"].iloc[0]
    benchmark = [round((v / bench_start - 1) * 100, 2) for v in bench_hist["Close"]]

    symbol_histories = {}
    for h in holdings:
        if h.symbol not in symbol_histories:
            try:
                t = yf.Ticker(h.symbol)
                hist = t.history(start=start_str, interval="1d")
                symbol_histories[h.symbol] = hist
            except Exception:
                symbol_histories[h.symbol] = None

    portfolio_values = []
    for i, date_str in enumerate(dates):
        total = 0
        invested = 0
        for h in holdings:
            hist = symbol_histories.get(h.symbol)
            if hist is None or hist.empty:
                continue
            buy_date_str = h.buy_date.strftime("%Y-%m-%d")
            if date_str < buy_date_str:
                continue
            try:
                idx = min(i, len(hist) - 1)
                price = hist["Close"].iloc[idx]
                total += h.quantity * price
                invested += h.quantity * h.buy_price
            except Exception:
                continue
        if invested > 0:
            portfolio_values.append(round((total / invested - 1) * 100, 2))
        else:
            portfolio_values.append(0)

    result = {"dates": dates, "portfolio": portfolio_values, "benchmark": benchmark}
    _set_cache(cache_key, result)
    return result
