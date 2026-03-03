from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    category_breakdown: list[dict]
    monthly_trend: list[dict]
    budget_status: list[dict]
