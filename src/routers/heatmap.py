"""Heatmap API — serves treemap data for S&P 500, sector, and ETF views."""

import logging
from typing import Optional

from fastapi import APIRouter

from src.services.market_data import (
    ETF_UNIVERSE,
    STOCK_UNIVERSE,
    fetch_batch,
    get_cached_quotes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


def _build_heatmap_items(
    symbols: list[str],
    *,
    cached_only: bool = True,
) -> list[dict]:
    """Return lightweight heatmap records from the info + quote caches.

    Each item: {symbol, name, sector, market_cap, change_pct, price}
    """
    infos = fetch_batch(symbols, cached_only=cached_only, include_stale=True)
    # Enrich with cached quote data (O(n) dict lookups, no API calls)
    quote_map = get_cached_quotes(symbols)

    items: list[dict] = []
    for info in infos:
        sym = info["symbol"]
        q = quote_map.get(sym, {})
        change_pct = q.get("change_pct") or info.get("change_pct") or 0
        # Use quote price if fresher, else info price
        price = q.get("price") or info.get("price", 0)
        market_cap = info.get("market_cap", 0) or 0
        if price <= 0:
            continue

        items.append(
            {
                "symbol": sym,
                "name": info.get("name", sym),
                "sector": info.get("sector", "N/A"),
                "market_cap": market_cap,
                "change_pct": round(change_pct, 2),
                "price": round(price, 2),
                "asset_type": info.get("asset_type", "Stock"),
            }
        )
    return items


@router.get("")
def get_heatmap(
    view: str = "stocks",
    sector: Optional[str] = None,
):
    """Return heatmap data.

    Query params:
      view: "stocks" | "sectors" | "etfs"
      sector: filter to a specific sector (drill-down)
    """
    if view == "etfs":
        items = _build_heatmap_items(ETF_UNIVERSE)
        # Group ETFs by a simplified category
        return {"view": "etfs", "items": items}

    if view == "sectors":
        # Return sector-level aggregates
        items = _build_heatmap_items(STOCK_UNIVERSE)
        sector_agg: dict[str, dict] = {}
        for it in items:
            sec = it["sector"] or "Other"
            if sec not in sector_agg:
                sector_agg[sec] = {"sector": sec, "market_cap": 0, "weighted_change": 0, "count": 0}
            sector_agg[sec]["market_cap"] += it["market_cap"]
            sector_agg[sec]["weighted_change"] += it["change_pct"] * it["market_cap"]
            sector_agg[sec]["count"] += 1
        result = []
        for sec, agg in sector_agg.items():
            cap = agg["market_cap"]
            result.append(
                {
                    "sector": sec,
                    "market_cap": cap,
                    "change_pct": round(agg["weighted_change"] / cap, 2) if cap else 0,
                    "count": agg["count"],
                }
            )
        result.sort(key=lambda x: x["market_cap"], reverse=True)
        return {"view": "sectors", "items": result}

    # Default: stocks view
    symbols = STOCK_UNIVERSE
    items = _build_heatmap_items(symbols)
    if sector:
        items = [i for i in items if i["sector"] == sector]
    # Sort by market cap descending so the largest tiles are first
    items.sort(key=lambda x: x["market_cap"], reverse=True)
    return {"view": "stocks", "items": items}
