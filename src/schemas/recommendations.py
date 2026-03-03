from pydantic import BaseModel
from typing import Optional


class RecommendationCard(BaseModel):
    symbol: str
    name: str
    asset_type: str
    sector: str
    price: float
    match_score: int
    risk_level: str
    reason: str
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    beta: Optional[float]
    year_change: Optional[float]


class PortfolioRecommendation(BaseModel):
    profile_label: str
    risk_score: int
    allocation: dict
    recommendations: list[RecommendationCard]
