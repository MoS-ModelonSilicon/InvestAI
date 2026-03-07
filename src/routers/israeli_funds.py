from typing import Optional

from fastapi import APIRouter

from src.services.israeli_funds import get_funds, get_fund_meta, get_best_deals

router = APIRouter(prefix="/api/il-funds", tags=["israeli-funds"])


@router.get("")
def list_funds(
    fund_type: Optional[str] = None,
    manager: Optional[str] = None,
    kosher_only: bool = False,
    sort_by: str = "fee",
    max_fee: Optional[float] = None,
    min_return: Optional[float] = None,
    min_size: Optional[float] = None,
    page: int = 1,
    per_page: int = 50,
):
    all_results = get_funds(
        fund_type=fund_type,
        manager=manager,
        kosher_only=kosher_only,
        sort_by=sort_by,
        max_fee=max_fee,
        min_return=min_return,
        min_size=min_size,
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


@router.get("/best")
def best_deals(category: Optional[str] = None, top_n: int = 5):
    return get_best_deals(category=category, top_n=top_n)


@router.get("/meta")
def fund_meta():
    return get_fund_meta()


@router.get("/debug")
def debug_scrape():
    """Diagnostic: test funder.co.il connectivity from this server."""
    import requests  # type: ignore[import-untyped]
    import time
    results = {}
    for key, url in [("kaspit", "https://www.funder.co.il/kaspit"), ("mehakot", "https://www.funder.co.il/mehakot")]:
        t0 = time.time()
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            elapsed = round(time.time() - t0, 2)
            has_data = "kaspitData" in r.text or "mehakotData" in r.text
            results[key] = {"status": r.status_code, "length": len(r.text), "has_js_var": has_data, "elapsed_s": elapsed}
        except Exception as e:
            results[key] = {"error": str(e), "elapsed_s": round(time.time() - t0, 2)}
    return results
