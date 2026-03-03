from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import RiskProfile
from src.schemas.recommendations import PortfolioRecommendation
from src.services.recommendations import generate_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=PortfolioRecommendation)
def get_recommendations(db: Session = Depends(get_db)):
    profile = db.query(RiskProfile).order_by(RiskProfile.id.desc()).first()
    if not profile:
        raise HTTPException(404, "No risk profile found. Complete the wizard first.")

    return generate_recommendations(
        risk_score=profile.risk_score,
        profile_label=profile.profile_label,
    )
