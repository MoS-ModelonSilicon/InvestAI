# Skill: Debugging Flow

Step-by-step debugging process for InvestAI issues.

## Step 1: Classify the Bug

| Symptom | Likely Area |
|---------|-------------|
| 500 error on API call | Router → Service → check logs |
| Page won't load / blank | Frontend JS error → browser console |
| Data not showing | API returns empty → check user_id filter, cache state |
| "Not authenticated" | Auth cookie missing/expired → check AuthMiddleware flow |
| Slow response | External API timeout → check Finnhub/Yahoo, cache miss |
| Stale data | Cache not refreshing → check background warmer, TTL |
| OOM on Render | Memory leak → check LowMemoryMiddleware, scan loops |

## Step 2: Reproduce

```bash
# Start local server with debug
TESTING=1 python -m uvicorn src.main:app --reload --log-level debug

# Check specific endpoint
curl http://localhost:8000/api/<endpoint>

# Run failing test in isolation
python -m pytest tests/test_api_smoke.py -k "test_name" -v --tb=long
```

## Step 3: Trace the Request Path

1. **Middleware** (`src/auth.py` → `AuthMiddleware`) — Is the request authenticated?
2. **Router** (`src/routers/<domain>.py`) — Is the endpoint registered? Correct method?
3. **Dependencies** — `get_db()` and `get_current_user()` working?
4. **Service** (`src/services/<domain>.py`) — Business logic error?
5. **External API** — Finnhub/Yahoo timeout or rate limit?
6. **Database** — Missing table/column? Migration ran?

## Step 4: Common Fixes

### Auth Issues
- Check `PUBLIC_PATHS` in `src/auth.py` — is the path exempted when it shouldn't be?
- Check cookie: `httponly=True` means you can't see it in JS — use browser DevTools → Application → Cookies
- JWT expired? Check `ACCESS_TOKEN_EXPIRE_DAYS` (currently 7)

### Market Data Issues
- Finnhub rate limit hit? Check `finnhub_client.py` rate limiter
- Yahoo disabled? Check `DISABLE_YAHOO` env var and auto-disable cooldown in `data_provider.py`
- Cache miss? Check `market_data.py` → `_cache` dict, look at TTL values
- Background warmer not running? Check `background_scheduler.py` thread startup in `main.py`

### Database Issues
- New column missing? Auto-migration runs on startup — check `main.py` startup event
- SQLite locked? Single-writer constraint — check for concurrent writes
- PostgreSQL connection? Verify `DATABASE_URL` env var format (must be `postgresql://`, not `postgres://`)

### Memory Issues (Render)
- Check `LowMemoryMiddleware` in `src/main.py`
- Large scan results? Value scanner and trading advisor cache full universes
- Consider: `persistence.py` saves to DB — is it flushing after save?

### Frontend Issues
- Check browser console for JS errors
- API calls go through `static/js/api.js` — check `fetchAPI()` wrapper
- 401 → auto-redirect to login page (by design)
- Check if new `<script>` tag was added to `index.html`

## Step 5: Verify Fix

```bash
# Run smoke tests
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short

# Check for regressions
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short -x

# Manual check
curl -v http://localhost:8000/api/<fixed-endpoint>
```

## Step 6: Prevent Recurrence

- Add test case for the bug
- If it's a gotcha, add it to the relevant local CLAUDE.md
- If it's a pattern, add to `.claude/skills/code-review.md`
