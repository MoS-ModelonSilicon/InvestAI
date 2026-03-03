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
):
    return get_funds(
        fund_type=fund_type,
        manager=manager,
        kosher_only=kosher_only,
        sort_by=sort_by,
        max_fee=max_fee,
        min_return=min_return,
        min_size=min_size,
    )


@router.get("/best")
def best_deals(category: Optional[str] = None, top_n: int = 5):
    return get_best_deals(category=category, top_n=top_n)


@router.get("/meta")
def fund_meta():
    return get_fund_meta()
