import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── Database URL ──────────────────────────────────────────────
# Production (Render): set DATABASE_URL env var pointing to external PostgreSQL
# Local dev: falls back to SQLite file
_raw_url = os.environ.get("DATABASE_URL", "sqlite:///./finance.db")

# Render/Heroku sometimes provide postgres:// which SQLAlchemy 2.x rejects
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = _raw_url
_is_sqlite = DATABASE_URL.startswith("sqlite")

_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
