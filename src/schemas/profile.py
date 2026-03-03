from pydantic import BaseModel
from datetime import datetime


class ProfileAnswers(BaseModel):
    goal: str
    timeline: str
    investment_style: str = "both"
    initial_investment: float = 0
    monthly_investment: float = 0
    experience: str
    risk_reaction: str
    income_stability: str


class ProfileOut(BaseModel):
    id: int
    goal: str
    timeline: str
    investment_style: str
    initial_investment: float
    monthly_investment: float
    experience: str
    risk_reaction: str
    income_stability: str
    risk_score: int
    profile_label: str
    created_at: datetime

    class Config:
        from_attributes = True


class AllocationOut(BaseModel):
    stocks_pct: float
    bonds_pct: float
    cash_pct: float
    profile_label: str
    risk_score: int
