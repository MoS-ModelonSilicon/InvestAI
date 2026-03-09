from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


# ── User Model ───────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    name: Mapped[str] = mapped_column(default="")
    is_admin: Mapped[int] = mapped_column(default=0)  # 0 = regular user, 1 = admin
    is_active: Mapped[int] = mapped_column(default=1)  # 0 = disabled, 1 = active
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    # relationships
    transactions: Mapped[list[Transaction]] = relationship(back_populates="owner")
    categories: Mapped[list[Category]] = relationship(back_populates="owner")
    budgets: Mapped[list[Budget]] = relationship(back_populates="owner")
    risk_profiles: Mapped[list[RiskProfile]] = relationship(back_populates="owner")
    watchlist_items: Mapped[list[Watchlist]] = relationship(back_populates="owner")
    holdings: Mapped[list[Holding]] = relationship(back_populates="owner")
    alerts: Mapped[list[Alert]] = relationship(back_populates="owner")
    dca_plans: Mapped[list[DcaPlan]] = relationship(back_populates="owner")
    suggestions: Mapped[list[Suggestion]] = relationship(back_populates="owner")


# ── Finance Tracker Models ───────────────────────────────────


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    color: Mapped[str] = mapped_column(default="#6366f1")
    type: Mapped[str] = mapped_column(default="expense")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)

    owner: Mapped[Optional[User]] = relationship(back_populates="categories")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="category")
    budgets: Mapped[list[Budget]] = relationship(back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float]
    type: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    date: Mapped[date] = mapped_column(index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))

    owner: Mapped[User] = relationship(back_populates="transactions")
    category: Mapped[Category] = relationship(back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    monthly_limit: Mapped[float]

    __table_args__ = (UniqueConstraint("user_id", "category_id", name="uq_budget_user_cat"),)

    owner: Mapped[User] = relationship(back_populates="budgets")
    category: Mapped[Category] = relationship(back_populates="budgets")


# ── Investment Models ────────────────────────────────────────


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    goal: Mapped[str]
    timeline: Mapped[str]
    investment_style: Mapped[str] = mapped_column(default="both")
    initial_investment: Mapped[float] = mapped_column(default=0)
    monthly_investment: Mapped[float] = mapped_column(default=0)
    experience: Mapped[str]
    risk_reaction: Mapped[str]
    income_stability: Mapped[str]
    risk_score: Mapped[int]
    profile_label: Mapped[str]
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="risk_profiles")


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symbol: Mapped[str]
    name: Mapped[str] = mapped_column(default="")
    added_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),)

    owner: Mapped[User] = relationship(back_populates="watchlist_items")


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symbol: Mapped[str]
    name: Mapped[str] = mapped_column(default="")
    quantity: Mapped[float]
    buy_price: Mapped[float]
    buy_date: Mapped[date]
    notes: Mapped[str] = mapped_column(default="")
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="holdings")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str]
    name: Mapped[str] = mapped_column(default="")
    condition: Mapped[str]
    target_price: Mapped[float]
    active: Mapped[int] = mapped_column(default=1)
    triggered: Mapped[int] = mapped_column(default=0)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="alerts")


class DcaPlan(Base):
    __tablename__ = "dca_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symbol: Mapped[str]
    name: Mapped[str] = mapped_column(default="")
    monthly_budget: Mapped[float]
    dip_threshold: Mapped[float] = mapped_column(default=-15.0)
    dip_multiplier: Mapped[float] = mapped_column(default=2.0)
    is_long_term: Mapped[int] = mapped_column(default=1)
    notes: Mapped[str] = mapped_column(default="")
    active: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_dca_user_symbol"),)

    owner: Mapped[User] = relationship(back_populates="dca_plans")


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    code: Mapped[str]
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)
    used: Mapped[int] = mapped_column(default=0)


class Suggestion(Base):
    """User feature requests and suggestions captured by AI assistant or manual form."""

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(Text)  # original user message
    ai_summary: Mapped[str] = mapped_column(Text, default="")  # AI-generated summary
    category: Mapped[str] = mapped_column(default="feature")  # feature/bug/improvement/content
    status: Mapped[str] = mapped_column(default="new")  # new/reviewed/planned/done/declined
    admin_notes: Mapped[str] = mapped_column(Text, default="")
    votes: Mapped[int] = mapped_column(default=1)
    github_issue_url: Mapped[Optional[str]] = mapped_column(default=None)
    github_issue_number: Mapped[Optional[int]] = mapped_column(default=None)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    owner: Mapped[User] = relationship(back_populates="suggestions")


class Pick(Base):
    """A trade pick from any source (Discord, Reddit, TradingView, Finviz, manual).

    Stored in the database so picks survive server restarts / Render deploys
    and are instantly available to every user.
    """

    __tablename__ = "picks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(index=True)
    date: Mapped[str]  # YYYY-MM-DD
    pick_type: Mapped[str] = mapped_column(default="breakout")  # breakout/swing/options/short
    entry: Mapped[Optional[float]] = mapped_column(default=None)
    targets: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of floats
    stop: Mapped[Optional[float]] = mapped_column(default=None)
    source: Mapped[str] = mapped_column(default="unknown", index=True)  # discord, reddit, tradingview, finviz
    notes: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[Optional[str]] = mapped_column(default=None)
    author: Mapped[Optional[str]] = mapped_column(default=None)
    confidence: Mapped[Optional[float]] = mapped_column(default=None)  # 0-1 quality score
    created_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)

    # Dedup key: same symbol+date+entry = same pick
    __table_args__ = (UniqueConstraint("symbol", "date", "entry", "source", name="uq_pick_sym_date_entry_src"),)

    def to_dict(self) -> dict:
        """Convert to the flat dict format expected by picks_tracker.py."""
        import json as _json

        return {
            "date": self.date,
            "symbol": self.symbol,
            "type": self.pick_type,
            "entry": self.entry,
            "targets": _json.loads(self.targets) if self.targets else [],
            "stop": self.stop,
            "source": self.source,
            "notes": self.notes or "",
            "url": self.url or "",
            "author": self.author or "",
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Pick:
        """Create a Pick from a flat dict (discord-picks.json format)."""
        import json as _json

        targets = d.get("targets", [])
        return cls(
            symbol=d["symbol"].upper().strip(),
            date=d.get("date", ""),
            pick_type=d.get("type", "breakout"),
            entry=d.get("entry"),
            targets=_json.dumps(targets) if targets else "[]",
            stop=d.get("stop"),
            source=d.get("source", "unknown"),
            notes=d.get("notes", ""),
            url=d.get("url"),
            author=d.get("author"),
            confidence=d.get("confidence"),
        )


class ScanResult(Base):
    """Persisted scan/cache results that survive server restarts.

    Stores JSON-serialized scan data keyed by a string identifier
    (e.g. 'value_scan', 'trading_scan', 'market_cache').
    """

    __tablename__ = "scan_results"

    key: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.utcnow)
