from pydantic import BaseModel
from datetime import date
from typing import Optional

from src.schemas.categories import CategoryOut


class TransactionCreate(BaseModel):
    amount: float
    type: str
    description: str = ""
    date: date
    category_id: int


class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    type: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    category_id: Optional[int] = None


class TransactionOut(BaseModel):
    id: int
    amount: float
    type: str
    description: str
    date: date
    category_id: int
    category: CategoryOut

    class Config:
        from_attributes = True
