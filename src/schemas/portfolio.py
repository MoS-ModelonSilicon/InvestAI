from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class HoldingCreate(BaseModel):
    symbol: str
    name: str = ""
    quantity: float
    buy_price: float
    buy_date: date
    notes: str = ""


class HoldingOut(BaseModel):
    id: int
    symbol: str
    name: str
    quantity: float
    buy_price: float
    buy_date: date
    notes: str
    created_at: datetime
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    cost_basis: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_pct: Optional[float] = None
    sector: str = "N/A"

    class Config:
        from_attributes = True


class SectorAllocation(BaseModel):
    sector: str
    value: float
    pct: float


class PortfolioSummary(BaseModel):
    total_invested: float
    total_value: float
    total_gain_loss: float
    total_gain_loss_pct: float
    holdings: list[HoldingOut]
    sector_allocation: list[SectorAllocation]
    best_performer: Optional[str] = None
    worst_performer: Optional[str] = None
