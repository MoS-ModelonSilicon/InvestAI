# Skill: Code Review Checklist

Use this checklist when reviewing any PR or code change in InvestAI.

## Security (CRITICAL — check every time)

- [ ] No `innerHTML` with user-supplied data (use `textContent` or sanitize)
- [ ] All DB queries filter by `user_id` — no cross-user data leaks
- [ ] Admin endpoints use `Depends(require_admin)`
- [ ] No secrets hardcoded (check for API keys, passwords, tokens in code)
- [ ] Auth cookie has `httponly=True`, `secure=True`, `samesite="lax"`
- [ ] No password reset codes returned in API responses
- [ ] Rate limiting applied to auth endpoints (register: 3/min, login: 5/min)
- [ ] Security headers present (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)

## Architecture

- [ ] Business logic lives in `src/services/`, NOT in routers
- [ ] HTTP/request handling in `src/routers/` only
- [ ] Pydantic schemas used for request validation AND response models
- [ ] New routers registered in `src/main.py` with proper prefix/tags
- [ ] No file exceeds 400 lines — split if needed
- [ ] Frontend: vanilla JS only (no React/Vue/Angular)

## Data Layer

- [ ] SQLAlchemy ORM only — no raw SQL
- [ ] New models added to `src/models.py` with proper relationships
- [ ] Cascade deletes considered for parent-child relationships
- [ ] Indexes added for frequently queried columns (user_id, date, symbol)
- [ ] Migration-safe: new columns have defaults or are nullable

## External APIs

- [ ] Finnhub calls use `finnhub_client.py` rate limiter (60/min)
- [ ] No Finnhub calls inside loops
- [ ] Yahoo Finance calls wrapped in try/except with Finnhub fallback
- [ ] Results cached appropriately (15-min for full info, 90s for live quotes)
- [ ] Graceful degradation when APIs are down

## Caching

- [ ] Cache keys use **normalized types** (e.g., `int(amount)` not raw float from FastAPI)
- [ ] If a function parameter only affects the cache key (not computation), scan once + replicate keys
- [ ] Pre-warming covers ALL parameter permutations users can select, not just defaults
- [ ] Cache key format is documented in the function docstring

## Frontend

- [ ] New pages added as hidden `<section>` in `index.html`
- [ ] JS module created in `static/js/`
- [ ] `<script>` tag added in `index.html`
- [ ] Nav item registered in `js/app.js`
- [ ] Loading spinners for async operations
- [ ] Dark/light theme support verified
- [ ] Mobile responsive layout tested

## Testing

- [ ] Smoke test covers new endpoint (non-500 response)
- [ ] Auth-required endpoints tested with and without auth
- [ ] Admin endpoints tested for non-admin rejection
- [ ] Edge cases: empty data, invalid input, missing resources
