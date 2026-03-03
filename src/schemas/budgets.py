from pydantic import BaseModel

from src.schemas.categories import CategoryOut


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
