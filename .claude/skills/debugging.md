# Skill: Debugging Flow

Step-by-step debugging process for InvestAI issues.

> **For the full bug lifecycle** (reproduce → fix → validate → deploy → verify live → close), see `.claude/skills/bug-lifecycle.md`. This file covers the **diagnosis** portion in depth.

## Step 1: Classify the Bug

| Symptom | Likely Area |
|---------|-------------|
| 500 error on API call | Router → Service → check logs |
| Page won't load / blank | Frontend JS error → browser console |
| Data not showing | API returns empty → check user_id filter, cache state |
| "Not authenticated" | Auth cookie missing/expired → check AuthMiddleware flow |
| Slow response | External API timeout → check Finnhub/Yahoo, cache miss |
| Stale data | Cache not refreshing → check background warmer, TTL |
| "Cached" endpoint still slow | Cache key mismatch — type/format differs between writer and reader |
| Some combos instant, others slow | Pre-warming missed combos — check scheduler covers all parameter permutations |
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

### Cache Key Mismatch (COMMON — hard to spot)
**Symptom**: A cached endpoint is instant for one caller but slow for another, even with identical parameters.
**Root cause**: The cache key is built from parameters, but types differ between callers:
- Scheduler calls `run_full_analysis(amount=10000)` → key `advisor:full:10000:balanced:1y`
- FastAPI parses query param as float → `run_full_analysis(amount=10000.0)` → key `advisor:full:10000.0:balanced:1y`
- Two different keys = cache miss every time from the API.
**Fix**: Normalize types at the TOP of the cached function: `amount = int(amount)`
**Prevention**: Always cast parameters to canonical types before building cache keys.

### Pre-Warming Gaps (scheduler doesn't cover all combos)
**Symptom**: Default parameter combo (e.g., 1y/balanced) is instant; other combos (6m, 3m) are slow.
**Root cause**: Scheduler only pre-computes a subset of parameter combinations.
**Debug**: Check `background_scheduler.py` → `_run_smart_advisor_scan()` — does it loop over ALL periods/risk profiles?
**Key gotcha**: `scan_and_score(period)` doesn't actually use `period` for computation — it uses `CANDLE_LOOKBACK_DAYS` constant. The period only affects the cache key. So scan ONCE and replicate the result to all period cache keys instead of scanning 4 times.

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

## Step 7: Deploy, Verify CI & Live Site

Follow the mandatory gates in `.claude/skills/bug-lifecycle.md` Phase 6-8:
1. Commit & push
2. Verify CI green on GitHub Actions
3. Verify the fix works on the live site
4. **A bug is NOT closed until verified on production**

## Real-World Debug Case Studies

### Case 1: Smart Advisor "Run Analysis" slow for non-default combos
- **Report**: 1y/balanced was instant, 6m/balanced took 30+ seconds
- **Investigation**: Cache key for scheduler = `advisor:full:10000:balanced:1y` (int). API cache key = `advisor:full:10000.0:balanced:1y` (float). Different keys → cache miss.
- **Fix 1**: `amount = int(amount)` at top of `run_full_analysis()` — normalizes both callers to same key.
- **Fix 2**: Scheduler was only pre-warming 1 of 12 combos. Expanded to scan once + replicate to all 4 period keys + pre-compute all 12 risk×period analyses.
- **Fix 3**: Initially "expanded" meant scanning 4 times. But `scan_and_score(period)` doesn't use `period` in computation. Fixed to scan once, copy cache to all period keys.
- **Lesson**: When adding cache pre-warming, trace the FULL parameter space. And always verify the function actually uses the parameter you're varying, vs just using it as a cache key.
- **Commits**: `fcdf3be` (key fix), `847c42c` (pre-warm all), `f5ff138` (scan-once optimization)
