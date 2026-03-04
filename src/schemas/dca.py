from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ── DCA Plan CRUD ────────────────────────────────────────────

class DcaPlanCreate(BaseModel):
    symbol: str
    name: str = ""
    monthly_budget: float = Field(..., gt=0, description="Monthly $ to invest in this stock")
    dip_threshold: float = Field(
        default=-15.0,
        le=0,
        description="Drop % from cost basis that triggers extra buy (e.g. -15 means 15% drop)",
    )
    dip_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Buy multiplier when dip detected (2 = double down)",
    )
    is_long_term: bool = True
    notes: str = ""


class DcaPlanOut(BaseModel):
    id: int
    symbol: str
    name: str
    monthly_budget: float
    dip_threshold: float
    dip_multiplier: float
    is_long_term: bool
    notes: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DcaPlanUpdate(BaseModel):
    monthly_budget: Optional[float] = None
    dip_threshold: Optional[float] = None
    dip_multiplier: Optional[float] = None
    is_long_term: Optional[bool] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


# ── Monthly Allocation Recommendation ────────────────────────

class MonthlyAllocationItem(BaseModel):
    symbol: str
    name: str
    normal_amount: float
    dip_detected: bool
    dip_pct: float  # how much the stock dipped (negative %)
    recommended_amount: float
    multiplier_applied: float
    reason: str
    current_price: Optional[float] = None
    avg_cost: Optional[float] = None
    shares_to_buy: Optional[float] = None


class MonthlyAllocationResponse(BaseModel):
    total_monthly_budget: float
    total_recommended: float
    over_budget: bool
    over_budget_amount: float
    allocations: list[MonthlyAllocationItem]
    month: str  # e.g. "2026-03"
    suggestions: list[str]  # general tips


# ── DCA Opportunity (dip alert) ──────────────────────────────

class DcaOpportunity(BaseModel):
    symbol: str
    name: str
    current_price: float
    avg_cost: float
    drop_from_cost: float  # % drop from avg cost basis
    drop_from_high: Optional[float] = None  # % drop from 52-week high
    plan_budget: float
    recommended_buy: float
    multiplier: float
    shares_to_buy: float
    urgency: str  # "high", "medium", "low"
    reason: str


class DcaDashboardResponse(BaseModel):
    plans: list[DcaPlanOut]
    opportunities: list[DcaOpportunity]
    monthly_allocation: MonthlyAllocationResponse
    portfolio_dca_value: float  # total $ allocated to DCA plans
    next_buy_date: str  # suggested next DCA buy date
