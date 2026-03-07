# src/ — Backend Gotchas

## Auth System (`auth.py`)

**DO NOT** change without understanding the full flow:
1. `AuthMiddleware` runs on EVERY request (except `PUBLIC_PATHS`)
2. JWT is in httponly cookie `investai_session` — not in headers
3. `request.state.user_id` is set by middleware, consumed by `get_current_user()`
4. `SECRET_KEY` comes from `INVESTAI_SECRET` env var — if missing, it regenerates on restart (invalidates all sessions)

**Security invariants:**
- Cookie: `httponly=True`, `secure=True`, `samesite="lax"` — never weaken these
- Password minimum: 8 characters, bcrypt hashed — never reduce
- Rate limiting: 3/min register, 5/min login — uses in-memory counters, disabled when `TESTING=1`
- `PUBLIC_PATHS` whitelist is the only way to bypass auth — adding paths here is a security decision

## Database (`database.py`)

- `DATABASE_URL` auto-detects SQLite vs PostgreSQL
- `postgres://` → `postgresql://` rewrite is critical (SQLAlchemy 2.x requirement)
- `get_db()` yields a session and ALWAYS closes it in finally — don't break this pattern
- SQLite: `check_same_thread=False` needed for FastAPI async — only applied for SQLite, not PostgreSQL

## Models (`models.py`)

- ALL models with user data MUST have `user_id` foreign key
- Every query MUST filter by `user_id` — this is the user isolation boundary
- Adding columns: use `nullable=True` or `server_default` for migration safety
- `ScanResult` model stores scan cache in DB — key is string, data is JSON blob

## Main (`main.py`)

This file does a lot:
- Auth routes (register, login, logout, forgot-password, reset-password)
- Middleware registration (auth, security headers, CORS, memory)
- Router registration (22 routers)
- Startup event (create tables, seed admin, restore caches, start warmer)
- Static file serving

**When editing:**
- Don't remove security header middleware
- Router registration order doesn't matter, but keep it alphabetical
- Startup sequence ORDER matters: migrate → seed → restore cache → start warmer
- `TESTING=1` disables rate limiting — never check this in production

## Circular Import Prevention

- `auth.py` does `from src.models import User` inside function (not at top level)
- This is intentional — `models.py` imports from `database.py`, and `auth.py` already imports from `database.py`
- Don't move the import to top level
