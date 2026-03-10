"""ETF Deep Analysis API — holdings, overlap, comparison, screening."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter

from src.services.etf_analysis import (
    compare_etfs,
    compute_overlap,
    get_etf_detail,
    get_etf_list,
    screen_etfs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/etf-analysis", tags=["etf-analysis"])


@router.get("")
def list_etfs(
    type: Optional[str] = None,
    region: Optional[str] = None,
    max_expense: Optional[float] = None,
    min_yield: Optional[float] = None,
    category: Optional[str] = None,
) -> dict:
    """Return all ETFs with metadata and optional filters.

    Query params:
      - type: Equity, Bond, Sector, Thematic, Commodity, etc.
      - region: US, International, Emerging, Asia, Europe, Global
      - max_expense: maximum expense ratio (e.g. 0.20)
      - min_yield: minimum dividend yield (e.g. 2.0)
      - category: text search in category name
    """
    has_filters = any([type, region, max_expense, min_yield, category])
    if has_filters:
        items = screen_etfs(
            etf_type=type,
            region=region,
            max_expense=max_expense,
            min_yield=min_yield,
            category=category,
        )
    else:
        items = get_etf_list()
    return {"count": len(items), "items": items}


@router.get("/compare")
def compare(symbols: str = "SPY,QQQ") -> dict:
    """Compare 2–5 ETFs side by side.

    Query params:
      - symbols: comma-separated tickers (e.g. SPY,QQQ,VTI)
    """
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(sym_list) < 2:
        return {"error": "Provide at least 2 symbols to compare"}
    return compare_etfs(sym_list)


@router.get("/overlap")
def overlap(a: str = "SPY", b: str = "QQQ") -> dict:
    """Compute holdings overlap between two ETFs.

    Query params:
      - a: first ETF symbol
      - b: second ETF symbol
    """
    return compute_overlap(a.strip().upper(), b.strip().upper())


@router.get("/{symbol}")
def get_etf(symbol: str) -> dict:
    """Return deep analysis for a single ETF."""
    result = get_etf_detail(symbol.strip().upper())
    if result is None:
        return {
            "symbol": symbol.upper(),
            "error": "No data available for this ETF",
        }
    return result
