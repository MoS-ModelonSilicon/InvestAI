from pydantic import BaseModel
from datetime import date
from typing import Optional


class CategoryCreate(BaseModel):
    name: str
    color: str = "#6366f1"
    type: str = "expense"


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    type: str

    class Config:
        from_attributes = True


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


class BudgetCreate(BaseModel):
    category_id: int
    monthly_limit: float


class BudgetOut(BaseModel):
    id: int
    category_id: int
    monthly_limit: float
    category: CategoryOut

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    category_breakdown: list[dict]
    monthly_trend: list[dict]
    budget_status: list[dict]
