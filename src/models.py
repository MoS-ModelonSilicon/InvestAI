import enum
from datetime import date as date_type, datetime

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


# ── Finance Tracker Models ───────────────────────────────────

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, default="#6366f1")
    type = Column(String, nullable=False, default="expense")

    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, default="")
    date = Column(Date, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, unique=True)
    monthly_limit = Column(Float, nullable=False)

    category = relationship("Category", back_populates="budgets")


# ── Investment Models ────────────────────────────────────────

class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    goal = Column(String, nullable=False)
    timeline = Column(String, nullable=False)
    investment_style = Column(String, nullable=False, default="both")
    initial_investment = Column(Float, nullable=False, default=0)
    monthly_investment = Column(Float, nullable=False, default=0)
    experience = Column(String, nullable=False)
    risk_reaction = Column(String, nullable=False)
    income_stability = Column(String, nullable=False)
    risk_score = Column(Integer, nullable=False)
    profile_label = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, unique=True)
    name = Column(String, default="")
    added_at = Column(DateTime, default=datetime.utcnow)


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(Date, nullable=False)
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    condition = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    active = Column(Integer, default=1)
    triggered = Column(Integer, default=0)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
