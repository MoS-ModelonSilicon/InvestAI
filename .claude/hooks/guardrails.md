# Claude Code Hooks — InvestAI Guardrails

These hooks define automated checks that MUST run. Models forget. Hooks don't.

## Hook: Post-Edit — Run Tests on Core Changes

**Trigger**: After any edit to files in `src/`
**Action**: Run smoke tests

```bash
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short -x
```

**Why**: Every backend change must pass the 80+ smoke tests. The `-x` flag stops on first failure for fast feedback.

---

## Hook: Post-Edit — Lint Check

**Trigger**: After any edit to `.py` files
**Action**: Verify syntax

```bash
python -c "from src.main import app; print('✓ Import OK')"
```

**Why**: Catches broken imports, syntax errors, and circular dependencies before they reach production.

---

## Hook: Block — Auth & Database Safety

**Trigger**: Before editing `src/auth.py` or `src/database.py`
**Action**: STOP and read the local CLAUDE.md

These files are security-critical. Before any edit:
1. Read `src/CLAUDE.md` for auth/database gotchas
2. Understand the change's security implications
3. After the edit, run the FULL smoke test suite (not just one test)

**Blocked patterns in auth.py**:
- Removing `secure=True` from cookies
- Adding paths to `PUBLIC_PATHS` without justification
- Changing `SECRET_KEY` logic
- Reducing password requirements

**Blocked patterns in database.py**:
- Changing the engine creation without testing both SQLite and PostgreSQL
- Removing session cleanup in `get_db()`

---

## Hook: Post-Edit — Verify Security Headers

**Trigger**: After editing `src/main.py` middleware section
**Action**: Check security headers are intact

Must verify these headers are still present:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security`
- `Content-Security-Policy`

---

## Hook: Post-Edit — Frontend XSS Check

**Trigger**: After editing any `static/js/*.js` file
**Action**: Search for `innerHTML` usage

```bash
grep -n "innerHTML" static/js/*.js
```

Every `innerHTML` occurrence must be reviewed. If it touches user data, replace with `textContent` or sanitize.

---

## Hook: Pre-Edit — Finnhub Rate Limit Check

**Trigger**: Before editing any file in `src/services/`
**Action**: Verify no Finnhub calls inside loops

```bash
# Search for loop + finnhub patterns
grep -B5 "finnhub\|_fh_client" src/services/*.py | grep -i "for \|while "
```

The free tier allows 60 calls/min. A loop over 280 symbols = instant rate limit block.

---

## Hook: Post-Deploy — Cache Restoration Check

**Trigger**: After deploying to Render
**Action**: Verify caches restored from PostgreSQL

Hit `/api/market/cache-status` and verify:
- Cache not empty
- Background warmer running
- Scan results loaded from DB

---

## How to Use These Hooks

When Claude Code makes an edit, mentally apply the matching hooks:

1. **Edited `src/*.py`?** → Run smoke tests
2. **Edited `src/auth.py` or `src/database.py`?** → STOP, read local CLAUDE.md, extra scrutiny
3. **Edited `src/main.py` middleware?** → Verify security headers
4. **Edited `static/js/*.js`?** → Check for innerHTML
5. **Edited `src/services/*.py`?** → Check Finnhub loop safety
6. **Deploying?** → Follow release skill, verify caches
