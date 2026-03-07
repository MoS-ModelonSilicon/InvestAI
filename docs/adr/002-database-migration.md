# ADR-002: Database Migration Strategy

**Date**: 2026-03-06  
**Status**: Accepted  
**Deciders**: Yaron Klein

## Context

The app started with SQLite. Render's free tier has an ephemeral filesystem — every deploy wipes the DB. Need persistence across redeploys.

## Decision

Use **external PostgreSQL (Supabase free tier)** for production, keep **SQLite for local development**.

## Implementation

- `src/database.py` reads `DATABASE_URL` env var, falls back to `sqlite:///./finance.db`
- Auto-detects `postgres://` vs `postgresql://` prefix issue
- SQLAlchemy 2.0 ORM abstracts the DB engine — same code works for both
- Auto-migration on startup: inspects existing tables, adds missing columns/indexes safely

## Scan Result Persistence

Expensive scan results (value scanner, trading advisor, smart advisor, picks tracker) are:
1. Computed in-memory by background threads
2. Saved to `ScanResult` table in PostgreSQL via `persistence.py`
3. Restored from PostgreSQL on startup (before background threads start)

This means a redeploy restores cached data instantly instead of waiting 15-30 min for scans.

## Gotchas

- **SQLite**: Single-writer, no concurrent writes. Fine for local dev.
- **PostgreSQL**: Connection pooling needed. Supabase pooler uses port 6543 (not 5432).
- **Migration safety**: Adding nullable columns is safe. Renaming or dropping columns requires manual migration.
- **`postgres://` prefix**: Render/Heroku use this, but SQLAlchemy 2.x requires `postgresql://`. We auto-fix this in `database.py`.
