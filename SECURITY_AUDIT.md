# InvestAI — Security Audit & Testing Strategy

> **Created:** 2026-03-06  
> **Status:** Planning  
> **Owner:** Yaron Klein (yaronklein1@gmail.com)

---

## Executive Summary

Full code audit revealed **6 critical/high** security issues and **zero unit or API tests** — all 60+ existing tests are Playwright browser E2E tests hitting real APIs. This document outlines a phased plan to fix vulnerabilities and build a layered test suite.

---

## Part 1: Security Findings

### Critical

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 1 | **No `secure` flag on session cookie** | `src/auth.py` — `set_cookie()` | Session hijacking over HTTP. Cookie sent on unencrypted requests. |
| 2 | **No CSRF protection** | Entire app | Cookie-based auth without CSRF tokens. POST/PUT/DELETE requests forgeable from external sites. |
| 3 | **Password reset code returned in API response** | `src/main.py` — `/auth/forgot-password` | When SMTP is unconfigured, the 6-digit code is returned directly → instant account takeover. |

### High

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 4 | **Stored XSS via `innerHTML`** | `static/app.js` (16 occurrences) | User-supplied data (transaction descriptions, category names) injected unsanitized into DOM. |
| 5 | **No rate limiting on auth endpoints** | `/auth/login`, `/auth/register`, `/auth/forgot-password` | Brute-force attacks on login and password reset codes. |
| 6 | **4-character minimum password** | `src/main.py` — registration | Trivially guessable passwords allowed. |

### Medium

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 7 | **No security headers** | `src/main.py` | Missing `X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`, `Strict-Transport-Security`. |
| 8 | **No email format validation** | `RegisterBody` uses `str` not `EmailStr` | Accounts created with invalid emails. |
| 9 | **Unpinned dependencies** | `requirements.txt` | Every install gets latest versions — supply-chain risk and reproducibility. |
| 10 | **Schema validation gaps** | `src/schemas/` | Transaction `type` accepts any string (no enum), `amount` allows negatives, no max-length on strings. |

### Low / Informational

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 11 | `SECRET_KEY` regenerates on restart if `INVESTAI_SECRET` env var not set | `src/auth.py` | All sessions invalidated on redeploy. Already set in Render? Verify. |
| 12 | `PasswordReset.code` stored in plaintext | `src/models.py` | DB compromise exposes active reset codes. |
| 13 | No DB indexes on `Transaction.user_id`, `Transaction.date` | `src/models.py` | Slow queries as data grows. |
| 14 | No cascade deletes on relationships | `src/models.py` | Orphaned records possible. |

### What's Already Good ✅

- **bcrypt password hashing** — proper salt, `hashpw`/`checkpw`
- **100% ORM queries** — no raw SQL, no injection vectors
- **User data isolation** — every query filters by `user_id == current_user.id`
- **Admin route protection** — all admin endpoints use `Depends(require_admin)`
- **Auth middleware** — catches 100% of requests, checks `is_active`
- **Self-operation prevention** — admin can't demote/delete own account

---

## Part 2: Security Fix Plan

### Phase S1 — Critical Fixes (Day 1)

**S1.1: Secure cookie flag**
```python
# src/auth.py — set_cookie()
response.set_cookie(
    key="investai_session", value=token,
    httponly=True, samesite="lax", path="/",
    secure=True,   # ← ADD THIS
    max_age=7*24*3600
)
```

**S1.2: Strengthen password policy**
```python
# src/main.py — registration
MIN_PASSWORD_LENGTH = 8  # was 4
# Add: at least 1 uppercase, 1 digit, 1 special char
```

**S1.3: Never return reset code in API response**
```python
# Remove the "code": code from forgot-password response when SMTP is down
# Return generic "If an account exists, instructions were sent" message
```

**S1.4: Add security headers middleware**
```python
# src/main.py
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### Phase S2 — High Priority (Day 2-3)

**S2.1: XSS remediation** — Replace all `innerHTML` with safe alternatives:
- Option A: `textContent` for text-only content
- Option B: Create a `escapeHTML()` helper for template literals
- Option C: Use DOMPurify library for complex HTML

```javascript
// static/app.js — add escape helper
function esc(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
// Then: ${esc(t.description)} instead of ${t.description}
```

**S2.2: Rate limiting**
```
pip install slowapi
```
```python
# src/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")   # 5 attempts per minute per IP
async def login(...): ...

@app.post("/auth/register")
@limiter.limit("3/minute")

@app.post("/auth/forgot-password")
@limiter.limit("3/minute")
```

**S2.3: Input validation hardening**
```python
# src/schemas/transactions.py
from enum import Enum
class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class TransactionCreate(BaseModel):
    amount: float = Field(gt=0, le=999_999_999)
    type: TransactionType
    description: str = Field(max_length=500)

# src/main.py — registration
from pydantic import EmailStr
class RegisterBody(BaseModel):
    email: EmailStr  # was: str
    password: str = Field(min_length=8, max_length=128)
```

### Phase S3 — Hardening (Day 4-5)

- **S3.1:** Pin all dependency versions in `requirements.txt`
- **S3.2:** Hash `PasswordReset.code` with bcrypt before storing
- **S3.3:** Add DB indexes on `Transaction(user_id, date)`, `Alert(user_id)`
- **S3.4:** Set `INVESTAI_SECRET` on Render (verify it exists, or create one)
- **S3.5:** Add CSRF token for state-changing requests (or migrate to `Authorization: Bearer` header)

---

## Part 3: Testing Strategy

### Current State

| Layer | Count | Status |
|-------|-------|--------|
| **Unit tests** | 0 | ❌ None |
| **API integration tests** | 0 | ❌ None |
| **E2E browser tests** | ~60 | ✅ Comprehensive (Playwright) |
| **Security tests** | 0 | ❌ None |
| **Performance tests** | ~2 | ⚠️ Basic |
| **Mocking** | 0 | ❌ All tests hit real APIs |

### Target State — Testing Pyramid

```
          ╱╲
         ╱  ╲         E2E (Playwright) — 60 existing
        ╱ E2E╲        Keep & maintain
       ╱──────╲
      ╱        ╲      API Tests (TestClient) — NEW
     ╱  API     ╲     Every endpoint, auth, edge cases
    ╱────────────╲
   ╱              ╲   Unit Tests — NEW
  ╱    Unit        ╲  Auth, schemas, services, models
 ╱──────────────────╲
╱    Security        ╲  Security Tests — NEW
╱────────────────────────╲  OWASP, fuzzing, injection
```

### Phase T1 — Unit Tests (tests/test_unit.py)

**Auth module** (~15 tests):
```
test_hash_password_returns_bcrypt_hash
test_verify_password_correct
test_verify_password_wrong
test_verify_password_empty
test_create_jwt_contains_user_id_and_email
test_create_jwt_has_expiry
test_decode_jwt_valid
test_decode_jwt_expired
test_decode_jwt_tampered
test_decode_jwt_wrong_secret
test_require_admin_passes_for_admin
test_require_admin_rejects_non_admin
test_require_admin_rejects_inactive
test_get_current_user_valid_cookie
test_get_current_user_no_cookie
```

**Password validation** (~8 tests):
```
test_password_min_length_rejected
test_password_meets_minimum
test_password_with_complexity_requirements
test_password_max_length
test_password_common_patterns_rejected  (optional)
test_registration_email_format_valid
test_registration_email_format_invalid
test_registration_duplicate_email
```

**Schema validation** (~12 tests):
```
test_transaction_create_valid
test_transaction_create_negative_amount
test_transaction_create_zero_amount
test_transaction_create_invalid_type
test_transaction_create_long_description
test_holding_create_valid
test_holding_create_negative_quantity
test_alert_create_valid
test_alert_create_invalid_condition
test_budget_create_valid
test_budget_create_zero_limit
test_budget_create_negative_limit
```

**Services** (~10 tests with mocking):
```
test_finnhub_quote_returns_price
test_finnhub_quote_handles_api_error
test_finnhub_quote_handles_timeout
test_data_provider_get_candles_valid
test_data_provider_get_candles_invalid_symbol
test_market_data_cache_hit
test_market_data_cache_miss
test_market_data_cache_expiry
test_risk_profile_score_calculation
test_recommendation_ranking
```

### Phase T2 — API Integration Tests (tests/test_api.py)

Use FastAPI `TestClient` — no browser, no network, fast:

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
```

**Auth endpoints** (~15 tests):
```
test_register_success
test_register_duplicate_email
test_register_weak_password
test_register_invalid_email_format
test_login_success_sets_cookie
test_login_wrong_password
test_login_nonexistent_email
test_login_inactive_user
test_logout_clears_cookie
test_forgot_password_existing_email
test_forgot_password_nonexistent_email_no_leak
test_reset_password_valid_code
test_reset_password_expired_code
test_reset_password_used_code
test_reset_password_wrong_code
```

**Transaction CRUD** (~10 tests):
```
test_create_transaction_success
test_list_transactions_pagination
test_list_transactions_filter_by_type
test_update_transaction_own
test_update_transaction_other_user_forbidden
test_delete_transaction_own
test_delete_transaction_other_user_forbidden
test_create_transaction_unauthenticated
test_create_transaction_invalid_amount
test_create_transaction_missing_fields
```

**Portfolio** (~8 tests):
```
test_add_holding_success
test_delete_holding_own
test_delete_holding_other_user
test_portfolio_summary_empty
test_portfolio_summary_with_holdings
test_portfolio_performance_endpoint
test_add_holding_invalid_symbol
test_add_holding_negative_quantity
```

**Admin** (~10 tests):
```
test_list_users_as_admin
test_list_users_as_regular_user_forbidden
test_toggle_admin_as_admin
test_toggle_admin_self_prevented
test_delete_user_as_admin
test_delete_user_self_prevented
test_reset_user_password_as_admin
test_admin_endpoint_unauthenticated
test_toggle_active_deactivates_user
test_deactivated_user_cannot_login
```

**Multi-user isolation** (~5 tests):
```
test_user_a_cannot_see_user_b_transactions
test_user_a_cannot_delete_user_b_transaction
test_user_a_cannot_see_user_b_holdings
test_user_a_cannot_see_user_b_budgets
test_user_a_cannot_see_user_b_alerts
```

### Phase T3 — Security Tests (tests/test_security.py)

**OWASP Top 10 coverage:**

```
# A01: Broken Access Control
test_idor_transaction_access_by_id
test_idor_holding_access_by_id
test_idor_budget_access_by_id
test_admin_endpoints_require_admin_role
test_api_requires_authentication

# A02: Cryptographic Failures
test_password_not_stored_in_plaintext
test_jwt_uses_strong_secret
test_session_cookie_httponly
test_session_cookie_secure_flag
test_session_cookie_samesite

# A03: Injection
test_sql_injection_in_login_email
test_sql_injection_in_transaction_description
test_sql_injection_in_symbol_search
test_xss_in_transaction_description
test_xss_in_category_name
test_xss_in_user_display_name

# A04: Insecure Design
test_password_reset_code_not_in_response
test_password_reset_rate_limited
test_login_rate_limited
test_registration_rate_limited

# A05: Security Misconfiguration
test_security_headers_present
test_no_server_version_header
test_error_response_no_stack_trace
test_debug_mode_disabled

# A07: Authentication Failures
test_expired_jwt_rejected
test_tampered_jwt_rejected
test_empty_jwt_rejected
test_brute_force_login_blocked
test_password_minimum_length_enforced
test_password_complexity_enforced

# A09: Logging & Monitoring
test_failed_login_logged
test_admin_action_logged
test_password_reset_logged
```

### Phase T4 — Performance & Load Tests (tests/test_perf.py)

```
test_dashboard_api_under_200ms
test_screener_api_under_500ms
test_concurrent_10_users_no_errors
test_large_transaction_list_pagination
test_memory_stable_after_100_requests
```

---

## Part 4: Implementation Priority & Timeline

### Week 1: Security Fixes + Unit Tests

| Day | Task | Est. Hours |
|-----|------|-----------|
| 1 | S1.1-S1.4: Critical security fixes (cookie, password policy, reset code, headers) | 3h |
| 2 | S2.1: XSS remediation (`innerHTML` → safe alternatives) | 3h |
| 2 | S2.2: Rate limiting with `slowapi` | 2h |
| 3 | S2.3: Input validation hardening (schemas, EmailStr) | 2h |
| 3 | T1: Unit tests — auth, schemas, password validation (~35 tests) | 3h |
| 4 | T2: API integration tests — auth endpoints (~15 tests) | 3h |
| 4 | T2: API integration tests — CRUD + admin (~28 tests) | 3h |
| 5 | T3: Security tests — OWASP coverage (~25 tests) | 4h |

### Week 2: Hardening + Full Coverage

| Day | Task | Est. Hours |
|-----|------|-----------|
| 1 | S3.1-S3.5: Pin deps, hash reset codes, indexes, CSRF | 4h |
| 2 | T1: Unit tests — services with mocking (~10 tests) | 3h |
| 3 | T2: API integration tests — multi-user isolation (~5 tests) | 2h |
| 4 | T4: Performance tests | 2h |
| 5 | CI/CD: Add `pytest` to Render build, dependency scanning | 3h |

---

## Part 5: Test Infrastructure

### Running Tests

```powershell
# Unit + API tests (fast, no browser, no network)
python -m pytest tests/test_unit.py tests/test_api.py tests/test_security.py -v

# E2E tests against local server
python -m pytest tests/test_e2e.py -v

# E2E tests against live Render
python -m pytest tests/test_live_site.py --live-url https://investai-utho.onrender.com -v

# Security tests only
python -m pytest tests/test_security.py -v --tb=short

# All tests with coverage
python -m pytest --cov=src --cov-report=html -v
```

### New Dependencies Needed

```
# requirements.txt additions
slowapi>=0.1.9          # Rate limiting
pytest-cov>=4.1         # Coverage reporting
httpx>=0.25             # Async test client for FastAPI
```

### CI Pipeline (future)

```yaml
# Run on every push:
# 1. pip install -r requirements.txt
# 2. python -m pytest tests/test_unit.py tests/test_api.py tests/test_security.py -v
# 3. bandit -r src/ -ll          # Static security scan
# 4. pip-audit                    # Dependency vulnerability scan
# 5. Deploy only if all pass
```

---

## Part 6: Quick Wins Checklist

Fixes that take < 30 min each and have outsized impact:

- [ ] Add `secure=True` to session cookie (1 line)
- [ ] Change password minimum from 4 → 8 chars (1 line)
- [ ] Remove reset code from API response (3 lines)
- [ ] Add `esc()` helper to `app.js` + wrap user data (30 min)
- [ ] Add security headers middleware (15 lines)
- [ ] Change `email: str` → `email: EmailStr` in RegisterBody (1 line)
- [ ] Add `TransactionType` enum to schema (5 lines)
- [ ] Pin dependency versions (run `pip freeze > requirements.txt`)
- [ ] Set `INVESTAI_SECRET` on Render if missing

---

## Appendix: Files Modified Per Fix

| Fix | Files |
|-----|-------|
| Secure cookie | `src/auth.py` |
| Password policy | `src/main.py`, `src/routers/admin.py` |
| Reset code leak | `src/main.py` |
| Security headers | `src/main.py` |
| XSS fix | `static/app.js`, all JS modules in `static/js/` |
| Rate limiting | `src/main.py`, `requirements.txt` |
| Schema validation | `src/schemas/transactions.py`, `src/schemas/portfolio.py`, `src/schemas/alerts.py` |
| Email validation | `src/main.py` |
| Pin deps | `requirements.txt` |
| New tests | `tests/test_unit.py`, `tests/test_api.py`, `tests/test_security.py`, `tests/test_perf.py` |
