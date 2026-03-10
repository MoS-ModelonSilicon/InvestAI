"""Dividend Analysis API — A–F grading system for income investors."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter

from src.services.dividend_analysis import (
    DIVIDEND_UNIVERSE,
    analyze_dividend,
    analyze_dividends_batch,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dividends", tags=["dividends"])


@router.get("")
def get_dividend_grades(
    symbols: Optional[str] = None,
) -> dict:
    """Return A–F dividend grades for a list of symbols.

    Query params:
      - symbols: comma-separated tickers (default: curated dividend universe)
    """
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        sym_list = DIVIDEND_UNIVERSE

    results = analyze_dividends_batch(sym_list)
    return {"count": len(results), "items": results}


@router.get("/{symbol}")
def get_dividend_grade_single(symbol: str) -> dict:
    """Return detailed dividend grade for a single symbol."""
    symbol = symbol.strip().upper()
    result = analyze_dividend(symbol)
    if result is None:
        return {
            "symbol": symbol,
            "error": "No data available for this symbol",
            "overall": {"score": 0, "grade": "N/A"},
            "grades": {},
        }
    return result
