from pydantic import BaseModel
from typing import Optional


class ScreenerFilters(BaseModel):
    asset_type: Optional[str] = None
    sector: Optional[str] = None
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    dividend_yield_min: Optional[float] = None
    beta_min: Optional[float] = None
    beta_max: Optional[float] = None
    limit: int = 25


class RiskFactor(BaseModel):
    name: str
    score: float
    max: float
    label: str
    detail: str


class RiskAnalysis(BaseModel):
    overall_score: float
    overall_label: str
    factors: list[RiskFactor]


class AnalystTargets(BaseModel):
    target_mean: float
    target_high: Optional[float]
    target_low: Optional[float]
    upside_pct: float
    num_analysts: int


class StockResult(BaseModel):
    symbol: str
    name: str
    sector: str
    industry: str = "N/A"
    price: float
    market_cap: float
    market_cap_fmt: str
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    dividend_yield: Optional[float]
    beta: Optional[float]
    year_change: Optional[float]
    recommendation: Optional[str]
    signal: str = "Hold"
    signal_reason: str = ""
    week52_high: Optional[float]
    week52_low: Optional[float]
    pct_from_high: Optional[float]
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]
    profit_margin: Optional[float]
    return_on_equity: Optional[float]
    debt_to_equity: Optional[float]
    risk_analysis: Optional[RiskAnalysis]
    analyst_targets: Optional[AnalystTargets]
    summary: str = ""
    region: str = "US"


class WatchlistItem(BaseModel):
    id: int
    symbol: str
    name: str

    class Config:
        from_attributes = True
