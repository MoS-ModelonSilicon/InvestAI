from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertCreate(BaseModel):
    symbol: str
    name: str = ""
    condition: str
    target_price: float


class AlertOut(BaseModel):
    id: int
    symbol: str
    name: str
    condition: str
    target_price: float
    active: int
    triggered: int
    triggered_at: Optional[datetime]
    created_at: datetime
    current_price: Optional[float] = None

    class Config:
        from_attributes = True
