# InvestAI — Claude Code Context

## Purpose

InvestAI is a full-stack personal investment advisory platform. FastAPI backend + vanilla JS frontend. Cookie-based JWT auth, SQLite locally / PostgreSQL on Render. Market data from Finnhub (primary) with Yahoo Finance fallback.

**Environments:**
- **Production**: https://investai-utho.onrender.com (manual promote only)
- **Staging**: https://finance-tracker-staging.onrender.com (auto-deploys on push to master)

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
- Run `ruff format src/ tests/` before shipping to avoid CI lint failures
- Actively monitor GitHub CI logs during ship pipeline — use `gh run view --log-failed` on failures, never wait blindly

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

Single branch: `master`. Staging auto-deploys on every push to `master`. Production is promoted after nightly E2E tests pass on staging.

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

### Intel Network Proxy (REQUIRED)

Git push will fail on the Intel corporate network without the proxy. **Always ensure this is set before pushing:**

```bash
git config --global http.proxy http://proxy-dmz.intel.com:911
```

This only needs to be set once per machine, but may be cleared by IT policy or reinstalls. If `git push` fails with `Failed to connect to github.com port 443`, re-run the command above.

### Deploy Cycle — Ship Pipeline (PREFERRED)

```powershell
# The automated way — one command does everything:
.\ship.ps1 "feat: describe what changed"

# This will: create issue → branch → commit → PR → wait for CI →
# auto-fix if failures → auto-merge → wait for staging deploy → E2E verify staging → promote to prod → close issue
# Set RENDER_PROD_DEPLOY_HOOK env var for auto-promote (see DEPLOY-KEYS.md).
# See docs/ship-pipeline.md for full details.
```

### Deploy Cycle — Manual (fallback)

```bash
# 1. Commit
git add -A
git commit -m "fix: describe what changed"

# 2. Ensure proxy is set (Intel network)
git config --global http.proxy http://proxy-dmz.intel.com:911

# 3. Push → staging auto-deploys, CI runs smoke tests
git push origin master

# 4. VERIFY CI passes (MANDATORY — do not skip):
#    Fetch: https://github.com/MoS-ModelonSilicon/InvestAI/actions/workflows/pr-tests.yml
#    ✅ "completed successfully" → staging deploys automatically
#    ❌ Failed → Read logs, fix, commit, push, re-check. Repeat until green.

# 5. Verify staging after deploy (~2 min):
#    https://finance-tracker-staging.onrender.com

# 6. Promote to production (choose one):
#    a) Wait for nightly E2E — auto-promotes if tests pass
#    b) Manual: Actions → "Promote to Production" → Run workflow
#    c) Direct: curl -X POST "$RENDER_PROD_DEPLOY_HOOK"
```

### CI Pipeline (4 workflows)

| Workflow | Trigger | Target | Purpose |
|----------|---------|--------|---------|
| `pr-tests.yml` | Push to master | Local (TestClient) | Smoke tests + lint gate |
| `nightly-tests.yml` | 2 AM UTC daily | Staging | E2E smoke tests, auto-promote to prod on success |
| `weekly-tests.yml` | 4 AM UTC Sunday | Production | Full regression suite |
| `promote-to-prod.yml` | Manual dispatch | Production | On-demand staging → prod promotion |

**Pipeline**: push → staging auto-deploy → E2E on staging → auto-promote to prod (immediate if via ship.ps1, nightly as fallback)

## Key Context Files

- `ship.ps1` — **Ship pipeline**: one-command feature delivery (issue → PR → CI → fix → merge → deploy → E2E)
- `docs/ship-pipeline.md` — Full pipeline documentation and architecture
- `.vscode/tasks.json` — VS Code Ctrl+Shift+B integration for ship pipeline
- `.claude/skills/` — Reusable workflows (debugging, code review, new features, bug lifecycle)
- `.claude/skills/bug-lifecycle.md` — **Mandatory 8-phase bug flow**: report → reproduce → diagnose → fix → validate → deploy → verify live → close
- `.claude/skills/ci-monitoring.md` — **CI monitoring during ship pipeline**: always check GitHub CI logs actively, never wait blindly; pre-ship lint check
- `.claude/agents/` — **Specialized bug-handling agents** (see below)
- `.claude/bugs/open.md` — Live bug tracker ledger maintained by Bug Reviewer Agent
- `docs/architecture.md` — Full system architecture
- `docs/adr/` — Engineering decision records
- `src/CLAUDE.md` — Backend gotchas
- `src/services/CLAUDE.md` — Service layer gotchas (caching, rate limits, fallbacks)
- `src/routers/CLAUDE.md` — Router patterns
- `AGENTS.md` — Full API reference (74 endpoints)

## Bug-Handling Agent System

Four specialized agents handle the full bug lifecycle. The **Orchestrator** coordinates all handoffs.

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│  .claude/agents/orchestrator.md                         │
│  Coordinates pipeline, owns deploy & verify steps       │
├─────────┬─────────────┬──────────────┬──────────────────┤
│ TESTER  │ REPRODUCER  │  DEVELOPER   │   REVIEWER       │
│ tester  │ reproducer  │  developer   │   reviewer       │
│ .md     │ .md         │  .md         │   .md            │
│ Finds   │ Confirms    │  Fixes       │   Tracks &       │
│ bugs    │ bugs        │  bugs        │   verifies       │
└─────────┴─────────────┴──────────────┴──────────────────┘
```

**When to use**: Any time a bug is reported, discovered in tests, or needs verification. Start with the Orchestrator — it will invoke the right agents in the right order.

**Pipeline**: Report → Tester → Reproducer → Developer → Orchestrator (deploy) → Tester (live verify) → Reviewer (close)
