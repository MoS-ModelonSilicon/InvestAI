# InvestAI — Claude Code Context

## Purpose

InvestAI is a full-stack personal investment advisory platform. FastAPI backend + vanilla JS frontend. Live at https://investai-utho.onrender.com. Cookie-based JWT auth, SQLite locally / PostgreSQL on Render. Market data from Finnhub (primary) with Yahoo Finance fallback.

## Repo Map

```
src/
├── main.py              # FastAPI app, auth routes, middleware, router registration
├── auth.py              # JWT, AuthMiddleware, password hashing — SENSITIVE
├── database.py          # SQLAlchemy engine, session factory — SENSITIVE
├── models.py            # All ORM models
├── routers/             # 22 API route modules (one per domain)
├── schemas/             # Pydantic request/response models
└── services/            # Business logic (no HTTP concerns)
    ├── finnhub_client.py    # Rate-limited Finnhub wrapper (60 calls/min)
    ├── data_provider.py     # Yahoo → Finnhub fallback
    ├── market_data.py       # Cache layer + background warmer
    ├── technical_analysis.py # 1100+ lines of indicators
    ├── persistence.py       # DB-backed cache persistence
    └── ...                  # 20+ service modules

static/                  # Vanilla HTML/CSS/JS SPA (NO React/Vue/Angular)
├── index.html           # All pages as hidden <section> divs
├── js/                  # 28 JS modules
└── style.css            # Dark/light theme

android/                 # Kotlin + Jetpack Compose WebView wrapper
tests/                   # Smoke tests (TestClient) + E2E (Playwright)
docs/                    # Architecture, ADRs, runbooks
```

## Rules

### NEVER
- Use frontend frameworks (React, Vue, Angular) — vanilla JS only
- Call Finnhub in loops — 60 calls/min limit, always use cache
- Write raw SQL — use SQLAlchemy ORM exclusively
- Store secrets in code — use env vars (`INVESTAI_SECRET`, `FINNHUB_API_KEY`, etc.)
- Edit `src/auth.py` or `src/database.py` without reading their local CLAUDE.md first
- Return reset codes in API responses (security vulnerability)
- Use `innerHTML` with user data — XSS risk, use `textContent`
- Skip `user_id` filtering on any data query — user isolation is mandatory
- Let files exceed 400 lines — split into modules

### ALWAYS
- Run `python -m pytest tests/test_api_smoke.py -v --tb=short` after backend changes
- Add Pydantic schemas for new endpoints (in `src/schemas/`)
- Keep business logic in `src/services/`, HTTP layer in `src/routers/`
- Use `request.state.user` for the authenticated user (set by `AuthMiddleware`)
- Use `Depends(get_db)` for database sessions
- Filter all user data by `user_id == current_user.id`
- Use `Depends(require_admin)` on admin endpoints
- Set `secure=True` on auth cookies
- Wrap external API calls with try/except and fallback behavior

## Commands

```bash
# Run locally
python -m uvicorn src.main:app --reload

# Run tests (fast, no external deps)
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short

# Run full E2E (needs running server on :8091)
python -m pytest tests/test_e2e.py -v

# Lint check
python -m py_compile src/main.py

# Network sharing
$env:INVESTAI_ACCESS_KEY="yourkey"
python -m uvicorn src.main:app --reload --host 0.0.0.0
```

## Git Workflow

### Branch

Single branch: `master`. Render auto-deploys on every push to `master`.

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) via CLI:

```bash
git add -A
git commit -m "type: concise description"
git push origin master
```

**Prefixes used in this repo:**

| Prefix | When to use | Example |
|--------|------------|----------|
| `feat:` | New feature or capability | `feat: server-side background scheduler for all periodic scans` |
| `fix:` | Bug fix | `fix: cache key mismatch — advisor 'Run Analysis' now returns instant results` |
| `perf:` | Performance improvement | `perf: move heavy client-side work to server-side` |
| `test:` | Adding or updating tests | `test: add smoke + E2E tests for perf optimizations` |
| `docs:` | Documentation only | `docs: update AGENTS.md for improved clarity` |
| `ci:` | CI/CD pipeline changes | `ci: add ruff lint, mypy type-check, and pre-commit config` |
| `security:` | Security fixes | `security: implement critical fixes from automated audit` |

### Deploy Cycle

```bash
# 1. Run smoke tests
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short

# 2. Commit
git add -A
git commit -m "fix: describe what changed"

# 3. Push → Render auto-deploys
git push origin master
```

## Key Context Files

- `.claude/skills/` — Reusable workflows (debugging, code review, new features)
- `docs/architecture.md` — Full system architecture
- `docs/adr/` — Engineering decision records
- `src/CLAUDE.md` — Backend gotchas
- `src/services/CLAUDE.md` — Service layer gotchas (caching, rate limits, fallbacks)
- `src/routers/CLAUDE.md` — Router patterns
- `AGENTS.md` — Full API reference (74 endpoints)
