# InvestAI — Testing Strategy

## Overview: Two-Tier Testing Pyramid

```
                     ┌──────────────────────────┐
                     │    Nightly (Tier 2)       │  Full browser E2E + API
                     │    ~227 Playwright tests  │  against live Render site
                     │    + API smoke tests      │  Runs at 2 AM UTC daily
                     ├──────────────────────────┤
                     │    PR Gate (Tier 1)       │  Fast TestClient tests
                     │    ~80 fast API tests     │  No browser, no ext API
                     │    + lint + import check  │  Runs on every push/PR
                     └──────────────────────────┘
```

Every push/PR runs fast smoke tests (~1-2 min) to prevent broken code from merging.
Every night, the full Playwright E2E suite runs against the live site to catch regressions.

---

## Tier 1 — PR / Commit Gate (~1-2 minutes)

**Workflow:** `.github/workflows/pr-tests.yml`
**Trigger:** Every `push` to `main` + every `pull_request` targeting `main`

### Jobs

| Job | What it does | Time |
|-----|-------------|------|
| `smoke-tests` | Runs `test_api_smoke.py` with FastAPI TestClient — no browser needed | ~60s |
| `lint` | Syntax-checks all `.py` files + verifies `from src.main import app` | ~15s |

### What Smoke Tests Cover

- **All 74 API endpoints** return non-500 status codes
- **Auth flows:** register, login, logout, me, forgot-password, reset-password
- **Full CRUD:** transactions, budgets, alerts, portfolio, DCA plans, categories, watchlist
- **Admin panel:** all 7 admin endpoints (stats, user list, detail, toggle-admin, toggle-active, reset-password, delete)
- **User isolation:** one user's data is invisible to another
- **Security:** auth required on `/api/*`, security headers, httponly cookies
- **Data integrity:** response structures, seeded categories, profile allocation

### Key Properties

- Uses `FastAPI.TestClient` (in-process HTTP, zero network)
- Ephemeral SQLite DB (fresh each run)
- Zero external dependencies (no Finnhub, no Yahoo Finance, no browser)
- All tests marked `@pytest.mark.smoke`

**If this fails → PR is blocked from merging.**

---

## Tier 2 — Nightly Regression (~15-25 min)

**Workflow:** `.github/workflows/nightly-tests.yml`
**Trigger:** Cron `0 2 * * *` (2 AM UTC daily) + manual `workflow_dispatch`

### Jobs

| Job | What it does |
|-----|-------------|
| `wake-site` | Pings Render to wake it from cold sleep |
| `api-smoke` | Same Tier 1 smoke tests (catch regressions in test infra itself) |
| `test` | Full Playwright E2E suite — all 227+ browser tests against live site |
| `notify-failure` | Auto-creates a GitHub Issue with failure details + log excerpt |
| `close-on-success` | Auto-closes any open `nightly-failure` issues |

### What E2E Tests Cover (in addition to Tier 1)

- Real browser rendering (Chromium via Playwright)
- Real external API calls (Finnhub, Yahoo Finance)
- Sparkline chart rendering (canvas pixel validation)
- Full user journeys (register → profile → portfolio → screener → advisor)
- Mobile layout, theme toggle, search bars
- Performance checks (page load times)
- Advanced feature flows (DCA, autopilot, advisor, comparison, stock detail)

**If this fails → GitHub Issue auto-created with failure details.**

---

## Test Files

| File | Purpose | Tier | Tests |
|------|---------|------|-------|
| `tests/test_api_smoke.py` | Fast API contract tests (TestClient) | 1 (PR) | ~80 |
| `tests/test_e2e.py` | Browser E2E (Playwright, local or remote) | 2 (Nightly) | ~133 |
| `tests/test_live_site.py` | Browser E2E for live deployment only | 2 (Nightly) | ~94 |

---

## CI Workflow Files

| File | Trigger | Runs |
|------|---------|------|
| `.github/workflows/pr-tests.yml` | Push to `main`, PRs | Tier 1 smoke + lint |
| `.github/workflows/nightly-tests.yml` | Daily 2 AM UTC, manual | Tier 1 + Tier 2 full suite |

---

## Endpoint Coverage: 74/74 (100%)

Previously untested endpoints now covered by `test_api_smoke.py`:
- All 7 admin endpoints (stats, users, toggle-admin, toggle-active, reset-password, delete)
- `GET /api/alerts/triggered`
- `POST /api/categories` + `DELETE /api/categories/{id}`
- `DELETE /api/budgets/{id}`
- `PUT /api/transactions/{id}`
- `DELETE /api/alerts/{id}` + `POST /api/alerts/{id}/dismiss`
- `DELETE /api/portfolio/holdings/{id}`
- `DELETE /api/screener/watchlist/{id}`
- `GET /api/calendar/economic`
- `GET /api/news/{symbol}`
- `GET /api/advisor/company-dna/{symbol}`
- `GET /api/stock/{symbol}/history` + `/news`
- `GET /api/trading/{symbol}`
- `GET /api/value-scanner/sectors`
- `PUT /api/dca/plans/{id}` + `DELETE /api/dca/plans/{id}`
- `POST /api/picks/seed-watchlist`

---

## Running Tests Locally

```bash
# Tier 1 — fast smoke (no server needed, ~60 seconds)
pytest tests/test_api_smoke.py -m smoke -v

# Tier 2 — full E2E against local server
pytest tests/test_e2e.py -v

# Tier 2 — full E2E against live site
pytest tests/ --live-url https://investai-utho.onrender.com -v

# Just admin tests
pytest tests/test_api_smoke.py::TestAdminSmoke -v

# Just security checks
pytest tests/test_api_smoke.py::TestSecuritySmoke -v
```

---

## Adding Tests for New Features

When adding a new feature/endpoint:

1. **Add an API smoke test** in `test_api_smoke.py` — verify endpoint returns correct status and basic structure. Mark with `@pytest.mark.smoke`.

2. **Add a Playwright E2E test** in `test_e2e.py` or `test_live_site.py` — verify the UI renders correctly and user flow works end-to-end.

3. PR gate catches API contract regressions; nightly catches rendering/integration issues.
