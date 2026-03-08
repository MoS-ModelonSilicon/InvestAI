# tests/ — Testing Gotchas

## Test Tiers

1. **Smoke tests** (`test_api_smoke.py`) — fast, in-process, no external APIs, no browser
2. **E2E tests** (`test_e2e.py`) — Playwright browser tests, needs running server on :8091
3. **Live site tests** (`test_live_site.py`) — tests against deployed Render instance

## Running Tests

```bash
# Smoke tests (always run these after backend changes)
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short

# E2E (needs server running first)
python -m uvicorn src.main:app --port 8091 &
python -m pytest tests/test_e2e.py -v

# Live site
python -m pytest tests/test_live_site.py -v
```

## Gotchas

- `TESTING=1` env var MUST be set for smoke tests — it disables rate limiting on auth endpoints
- Smoke tests use ephemeral SQLite (fresh DB each run) — no data persists
- `conftest.py` sets up TestClient and test fixtures — read this before adding tests
- E2E tests expect specific DOM structure — if you change `index.html` sections, tests may break
- Live site tests depend on Render being awake and data being cached
- **Ship pipeline runs only 4 E2E tests** via `-k` filter: `test_login_page_loads`, `test_stock_detail_opens`, `test_dca_page_loads`, `test_dashboard_loads`. Use exact names — `test_dashboard` would also match `test_dashboard_api`
- `TestAPIHealth._fetch()` auto-recovers from 401 by calling `_reauth()` to re-login via browser — handles stale cookies after Render deploy

## Adding a New Smoke Test

```python
def test_new_endpoint(client, auth_headers):
    """Test that /api/new-endpoint returns 200."""
    response = client.get("/api/new-endpoint", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Assert response structure
```

## What to Test

- Every new endpoint returns non-500
- Auth-required endpoints return 401 without auth
- Admin endpoints return 403 for non-admins
- CRUD: create → read → update → delete
- User isolation: user A can't access user B's data
