from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from datetime import date
from typing import Optional

from src.schemas.categories import CategoryOut


class TransactionTypeEnum(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    amount: float = Field(gt=0, le=999_999_999, description="Transaction amount (positive)")
    type: TransactionTypeEnum
    description: str = Field(default="", max_length=500)
    date: date
    category_id: int


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    amount: Optional[float] = Field(default=None, gt=0, le=999_999_999)
    type: Optional[TransactionTypeEnum] = None
    description: Optional[str] = Field(default=None, max_length=500)
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
