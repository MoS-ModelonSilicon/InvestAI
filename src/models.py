import enum
from datetime import date as date_type, datetime

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from src.database import Base


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


# ── User Model ───────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, default="")
    is_admin = Column(Integer, default=0)  # 0 = regular user, 1 = admin
    is_active = Column(Integer, default=1)  # 0 = disabled, 1 = active
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    transactions = relationship("Transaction", back_populates="owner")
    categories = relationship("Category", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")
    risk_profiles = relationship("RiskProfile", back_populates="owner")
    watchlist_items = relationship("Watchlist", back_populates="owner")
    holdings = relationship("Holding", back_populates="owner")
    alerts = relationship("Alert", back_populates="owner")
    dca_plans = relationship("DcaPlan", back_populates="owner")


# ── Finance Tracker Models ───────────────────────────────────

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    color = Column(String, default="#6366f1")
    type = Column(String, nullable=False, default="expense")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_user_name"),
    )

    owner = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, default="")
    date = Column(Date, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    owner = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    monthly_limit = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_budget_user_cat"),
    )

    owner = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")


# ── Investment Models ────────────────────────────────────────

class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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

    owner = relationship("User", back_populates="risk_profiles")


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    added_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )

    owner = relationship("User", back_populates="watchlist_items")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(Date, nullable=False)
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="holdings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    condition = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    active = Column(Integer, default=1)
    triggered = Column(Integer, default=0)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="alerts")


class DcaPlan(Base):
    __tablename__ = "dca_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    name = Column(String, default="")
    monthly_budget = Column(Float, nullable=False)
    dip_threshold = Column(Float, nullable=False, default=-15.0)
    dip_multiplier = Column(Float, nullable=False, default=2.0)
    is_long_term = Column(Integer, default=1)
    notes = Column(String, default="")
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_dca_user_symbol"),
    )

    owner = relationship("User", back_populates="dca_plans")


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Integer, default=0)
