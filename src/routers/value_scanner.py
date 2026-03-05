from typing import Optional

from fastapi import APIRouter

from src.services.value_scanner import scan_value_stocks, build_action_plan, EXCLUDED_SECTORS
from src.services.market_data import SECTORS

router = APIRouter(prefix="/api/value-scanner", tags=["value-scanner"])


@router.get("")
def run_value_scanner(
    sector: Optional[str] = None,
    signal: Optional[str] = None,
    sort_by: str = "score",
    page: int = 1,
    per_page: int = 15,
):
    return scan_value_stocks(
        sector=sector,
        signal_filter=signal,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )


@router.get("/action-plan")
def get_action_plan(
    amount: float = 10000,
    sector: Optional[str] = None,
    signal: Optional[str] = None,
):
    """Generate a portfolio action plan from current value scanner candidates."""
    return build_action_plan(amount=amount, sector=sector, signal_filter=signal)


@router.get("/sectors")
def list_sectors():
    return {
        "sectors": [s for s in SECTORS if s not in EXCLUDED_SECTORS],
        "excluded": list(EXCLUDED_SECTORS),
    }
