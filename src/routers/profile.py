from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import RiskProfile
from src.schemas.profile import ProfileAnswers, ProfileOut, AllocationOut
from src.services.risk_profile import calculate_risk_score, get_allocation

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileOut | None)
def get_current_profile(db: Session = Depends(get_db)):
    profile = db.query(RiskProfile).order_by(RiskProfile.id.desc()).first()
    return profile


@router.post("", response_model=ProfileOut)
def submit_profile(payload: ProfileAnswers, db: Session = Depends(get_db)):
    score, label = calculate_risk_score(
        goal=payload.goal,
        timeline=payload.timeline,
        investment_style=payload.investment_style,
        initial_investment=payload.initial_investment,
        monthly_investment=payload.monthly_investment,
        experience=payload.experience,
        risk_reaction=payload.risk_reaction,
        income_stability=payload.income_stability,
    )

    profile = RiskProfile(
        **payload.model_dump(),
        risk_score=score,
        profile_label=label,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/allocation", response_model=AllocationOut)
def get_allocation_for_profile(db: Session = Depends(get_db)):
    profile = db.query(RiskProfile).order_by(RiskProfile.id.desc()).first()
    if not profile:
        raise HTTPException(404, "No risk profile found. Complete the wizard first.")

    alloc = get_allocation(profile.profile_label)
    return AllocationOut(
        stocks_pct=alloc["stocks"],
        bonds_pct=alloc["bonds"],
        cash_pct=alloc["cash"],
        profile_label=profile.profile_label,
        risk_score=profile.risk_score,
    )
