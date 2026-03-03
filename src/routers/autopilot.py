import logging

from fastapi import APIRouter, Query

from src.services.autopilot import get_profiles, simulate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autopilot", tags=["autopilot"])


@router.get("/profiles")
def list_profiles():
    try:
        return get_profiles()
    except Exception as e:
        logger.error("autopilot profiles error: %s", e)
        return []


@router.get("/simulate")
def run_simulation(
    profile: str = Query(..., description="Profile id: daredevil, strategist, fortress"),
    amount: float = Query(10000, ge=100, le=10_000_000),
    period: str = Query("1y", pattern="^(1m|3m|6m|1y)$"),
):
    try:
        return simulate(profile, amount, period)
    except Exception as e:
        logger.error("autopilot simulate error: %s", e)
        return {"error": str(e)}
