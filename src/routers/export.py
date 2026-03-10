"""CSV export endpoints for screener, portfolio, watchlist, and transactions."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.database import get_db
from src.models import Transaction, User, Watchlist
from src.services.screener import screen_instruments

router = APIRouter(prefix="/api/export", tags=["export"])


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    """Build a StreamingResponse with CSV content from a list of dicts."""
    if not rows:
        buf = io.StringIO()
        buf.write("")
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/screener")
def export_screener(
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export all screener results to CSV."""
    items = screen_instruments()
    rows = [
        {
            "Symbol": it.get("symbol", ""),
            "Name": it.get("name", ""),
            "Sector": it.get("sector", ""),
            "Industry": it.get("industry", ""),
            "Price": it.get("price", ""),
            "Market Cap": it.get("market_cap_fmt", ""),
            "P/E": it.get("pe_ratio", ""),
            "Forward P/E": it.get("forward_pe", ""),
            "Div Yield %": it.get("dividend_yield", ""),
            "Beta": it.get("beta", ""),
            "52W Change %": it.get("year_change", ""),
            "Signal": it.get("signal", ""),
            "Signal Reason": it.get("signal_reason", ""),
            "52W High": it.get("week52_high", ""),
            "52W Low": it.get("week52_low", ""),
            "% From High": it.get("pct_from_high", ""),
            "Revenue Growth": it.get("revenue_growth", ""),
            "Earnings Growth": it.get("earnings_growth", ""),
            "Profit Margin": it.get("profit_margin", ""),
            "ROE": it.get("return_on_equity", ""),
            "Debt/Equity": it.get("debt_to_equity", ""),
            "Region": it.get("region", ""),
        }
        for it in items
    ]
    ts = datetime.now().strftime("%Y%m%d")
    return _csv_response(rows, f"screener_{ts}.csv")


@router.get("/portfolio")
def export_portfolio(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export portfolio holdings to CSV with enriched data."""
    from src.services.portfolio import calculate_portfolio

    try:
        summary = calculate_portfolio(db, user.id)
        holdings = summary.get("holdings", [])
    except Exception:
        holdings = []

    rows = [
        {
            "Symbol": h.get("symbol", ""),
            "Name": h.get("name", ""),
            "Quantity": h.get("quantity", ""),
            "Buy Price": h.get("buy_price", ""),
            "Buy Date": h.get("buy_date", ""),
            "Current Price": h.get("current_price", ""),
            "Current Value": h.get("current_value", ""),
            "Cost Basis": h.get("cost_basis", ""),
            "Gain/Loss": h.get("gain_loss", ""),
            "Gain/Loss %": h.get("gain_loss_pct", ""),
            "Sector": h.get("sector", ""),
            "Notes": h.get("notes", ""),
        }
        for h in holdings
    ]
    ts = datetime.now().strftime("%Y%m%d")
    return _csv_response(rows, f"portfolio_{ts}.csv")


@router.get("/watchlist")
def export_watchlist(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export watchlist to CSV with basic info."""
    items = db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.added_at.desc()).all()
    rows = [
        {
            "Symbol": it.symbol,
            "Name": it.name or "",
            "Added At": it.added_at.isoformat() if it.added_at else "",
        }
        for it in items
    ]
    ts = datetime.now().strftime("%Y%m%d")
    return _csv_response(rows, f"watchlist_{ts}.csv")


@router.get("/transactions")
def export_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export transaction history to CSV."""
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.date.desc()).all()
    rows = [
        {
            "Date": tx.date.isoformat() if tx.date else "",
            "Type": tx.type or "",
            "Description": tx.description or "",
            "Amount": tx.amount,
            "Category": tx.category.name if tx.category else "",
        }
        for tx in txs
    ]
    ts = datetime.now().strftime("%Y%m%d")
    return _csv_response(rows, f"transactions_{ts}.csv")
