import logging
import threading

from fastapi import APIRouter, Query

from src.services.autopilot import get_profiles, simulate, get_cached_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autopilot", tags=["autopilot"])


@router.get("/profiles")
def list_profiles():
    try:
        return get_profiles()
    except Exception as e:
        logger.error("autopilot profiles error: %s", e)
        return []


@router.get("/cached-status")
def cached_status():
    """Return which profile/period combos have cached data ready."""
    try:
        return get_cached_status()
    except Exception as e:
        logger.error("autopilot cached-status error: %s", e)
        return {}


@router.post("/warmup")
def trigger_warmup():
    """Manually trigger autopilot warmup in the background."""
    try:
        from src.services.autopilot import run_full_warmup

        threading.Thread(target=run_full_warmup, daemon=True, name="ap-warmup").start()
        return {"status": "warmup started"}
    except Exception as e:
        logger.error("autopilot warmup trigger error: %s", e)
        return {"error": str(e)}


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
