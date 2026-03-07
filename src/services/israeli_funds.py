"""
Israeli mutual fund service — queries live data from funder.co.il
and provides filtering, sorting, and analytics.
"""

from typing import Optional

from src.services.funder_scraper import fetch_all_funds, get_categories, get_managers


def get_funds(
    fund_type: Optional[str] = None,
    manager: Optional[str] = None,
    kosher_only: bool = False,
    sort_by: str = "fee",
    max_fee: Optional[float] = None,
    min_return: Optional[float] = None,
    min_size: Optional[float] = None,
) -> list[dict]:
    all_funds = fetch_all_funds()

    filtered = list(all_funds)

    if fund_type:
        filtered = [f for f in filtered if f["category"] == fund_type]
    if manager:
        filtered = [f for f in filtered if f["manager"] == manager]
    if kosher_only:
        filtered = [f for f in filtered if f.get("kosher")]
    if max_fee is not None:
        filtered = [f for f in filtered if f["fee"] <= max_fee]
    if min_return is not None:
        filtered = [f for f in filtered if (f.get("annual_return") or 0) >= min_return]
    if min_size is not None:
        filtered = [f for f in filtered if (f.get("size_m") or 0) >= min_size]

    reverse = sort_by in ("annual_return", "ytd_return", "size_m", "monthly_return")
    filtered.sort(key=lambda x: x.get(sort_by) or 0, reverse=reverse)

    for i, f in enumerate(filtered):
        f["rank"] = i + 1

    return filtered


def get_fund_meta() -> dict:
    all_funds = fetch_all_funds()
    return {
        "categories": get_categories(),
        "managers": get_managers(all_funds),
        "total_funds": len(all_funds),
    }


def get_best_deals(category: Optional[str] = None, top_n: int = 5) -> dict:
    all_funds = fetch_all_funds()

    pool = all_funds
    if category:
        pool = [f for f in pool if f["category"] == category]

    if not pool:
        return {"top_funds": [], "stats": {}}

    by_fee = sorted(pool, key=lambda x: x.get("fee") or 999)
    best = by_fee[:top_n]

    fees = [f["fee"] for f in pool if f["fee"] is not None]
    returns = [f["annual_return"] for f in pool if f.get("annual_return") is not None]

    avg_fee = sum(fees) / len(fees) if fees else 0
    min_fee = min(fees) if fees else 0
    max_fee = max(fees) if fees else 0
    avg_return = sum(returns) / len(returns) if returns else 0

    for f in best:
        f["savings_vs_avg_100k"] = round((avg_fee - f["fee"]) / 100 * 100_000, 0)
        f["savings_vs_avg_1m"] = round((avg_fee - f["fee"]) / 100 * 1_000_000, 0)

    return {
        "top_funds": best,
        "stats": {
            "total_funds": len(pool),
            "avg_fee": round(avg_fee, 3),
            "min_fee": round(min_fee, 3),
            "max_fee": round(max_fee, 3),
            "fee_spread": round(max_fee - min_fee, 3),
            "avg_return": round(avg_return, 2) if returns else None,
            "savings_best_vs_worst_100k": round((max_fee - min_fee) / 100 * 100_000, 0),
        },
    }
