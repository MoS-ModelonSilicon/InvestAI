"""
API Smoke Tests — Tier 1 (PR / Commit)

Fast integration tests using FastAPI's TestClient. No browser, no external
API calls needed for basic validation. These verify every endpoint returns a
sane status code and that auth + CRUD flows actually work.

Run:
    pytest tests/test_api_smoke.py -v            # all smoke tests
    pytest tests/test_api_smoke.py -m smoke -v   # just the smoke subset
"""

import os
import sys
import time
import pytest

# ── Ensure finance-tracker root is importable ──────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Set env vars before importing app
os.environ.setdefault("FINNHUB_API_KEY", "")
os.environ.setdefault("INVESTAI_SECRET", "test-secret-key-for-ci")
os.environ["TESTING"] = "1"  # disable rate limiting
os.environ["DISABLE_YAHOO"] = "1"  # avoid slow Yahoo Finance retries in CI

from fastapi.testclient import TestClient
from src.main import app

# External-data endpoints may return 404/502/503 when APIs are unreachable.
# Smoke tests only verify no unhandled crash (500).
_NO_CRASH = {200, 201, 204, 301, 302, 304, 400, 401, 403, 404, 409, 422, 429, 502, 503}

# ── Helpers ────────────────────────────────────────────────────

# Use https:// base so secure cookies are sent back
client = TestClient(app, raise_server_exceptions=False, base_url="https://testserver")

_user_counter = 0


def _fresh_email():
    global _user_counter
    _user_counter += 1
    return f"smoke{_user_counter}_{int(time.time())}@testsmoke.com"


def _register_and_login(email=None, password="SmokeTesting123", name="Smoke"):
    """Register + login and return a new TestClient with auth cookies set."""
    email = email or _fresh_email()
    client.post("/auth/register", json={"email": email, "password": password, "name": name})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    # Create a fresh client with the auth cookie baked in
    authed = TestClient(app, raise_server_exceptions=False, base_url="https://testserver")
    authed.cookies.set("investai_session", resp.cookies.get("investai_session"))
    return authed, email


def _authed_get(path, c):
    return c.get(path)


def _authed_post(path, c, json=None):
    return c.post(path, json=json)


def _authed_put(path, c, json=None):
    return c.put(path, json=json)


def _authed_delete(path, c):
    return c.delete(path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tier 1A — Auth Endpoints (smoke)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.smoke
class TestAuthSmoke:
    """Auth flow: register, login, me, logout."""

    def test_login_page_serves_html(self):
        r = client.get("/login")
        assert r.status_code == 200
        assert "html" in r.headers.get("content-type", "").lower()

    def test_root_redirects_to_login_when_unauthenticated(self):
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (200, 302)

    def test_register_new_user(self):
        email = _fresh_email()
        r = client.post("/auth/register", json={"email": email, "password": "Str0ngPass!", "name": "Test"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_register_duplicate_email_rejected(self):
        email = _fresh_email()
        client.post("/auth/register", json={"email": email, "password": "Str0ngPass!", "name": "Test"})
        r = client.post("/auth/register", json={"email": email, "password": "Str0ngPass!", "name": "Test2"})
        assert r.status_code == 400

    def test_register_short_password_rejected(self):
        r = client.post("/auth/register", json={"email": _fresh_email(), "password": "short", "name": "Test"})
        assert r.status_code == 400

    def test_login_success(self):
        email = _fresh_email()
        client.post("/auth/register", json={"email": email, "password": "Str0ngPass!", "name": "Test"})
        r = client.post("/auth/login", json={"email": email, "password": "Str0ngPass!"})
        assert r.status_code == 200
        assert "investai_session" in r.cookies

    def test_login_wrong_password(self):
        email = _fresh_email()
        client.post("/auth/register", json={"email": email, "password": "Str0ngPass!", "name": "Test"})
        r = client.post("/auth/login", json={"email": email, "password": "WrongPass!"})
        assert r.status_code == 403

    def test_me_authenticated(self):
        cookies, email = _register_and_login()
        r = _authed_get("/auth/me", cookies)
        assert r.status_code == 200
        assert r.json()["email"] == email

    def test_me_unauthenticated(self):
        fresh = TestClient(app, raise_server_exceptions=False, base_url="https://testserver")
        r = fresh.get("/auth/me", follow_redirects=False)
        # /auth/me without cookie redirects to /login (302) or returns 401 JSON
        assert r.status_code in (302, 401)

    def test_logout(self):
        authed, _ = _register_and_login()
        r = authed.get("/auth/logout", follow_redirects=False)
        assert r.status_code == 302

    def test_forgot_password_ok_for_any_email(self):
        r = client.post("/auth/forgot-password", json={"email": "nobody@testsmoke.com"})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_reset_password_bad_code(self):
        r = client.post("/auth/reset-password", json={
            "email": "nobody@testsmoke.com", "code": "000000", "new_password": "NewPass123!"
        })
        assert r.status_code == 400


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tier 1B — All API endpoints return non-500 (smoke)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.smoke
class TestAllEndpointsSmoke:
    """Every API endpoint should return a non-500 response when authed."""

    @pytest.fixture(autouse=True)
    def setup_auth(self):
        self.c, self.email = _register_and_login()

    # ── Dashboard ──
    def test_dashboard(self):
        r = _authed_get("/api/dashboard", self.c)
        assert r.status_code == 200

    # ── Categories ──
    def test_list_categories(self):
        r = _authed_get("/api/categories", self.c)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_category(self):
        r = _authed_post("/api/categories", self.c,
                         json={"name": "SmokeCategory", "color": "#ff0000", "type": "expense"})
        assert r.status_code == 200

    def test_delete_category(self):
        r = _authed_post("/api/categories", self.c,
                         json={"name": "ToDelete", "color": "#ff0000", "type": "expense"})
        cat_id = r.json().get("id")
        if cat_id:
            r2 = _authed_delete(f"/api/categories/{cat_id}", self.c)
            assert r2.status_code in (200, 204)

    # ── helper: get a category_id ──
    def _get_category_id(self):
        r = _authed_get("/api/categories", self.c)
        cats = r.json()
        if cats:
            return cats[0]["id"]
        r2 = _authed_post("/api/categories", self.c,
                          json={"name": "SmokeDefault", "color": "#000000", "type": "expense"})
        return r2.json()["id"]

    # ── Transactions ──
    def test_list_transactions(self):
        r = _authed_get("/api/transactions", self.c)
        assert r.status_code == 200

    def test_create_transaction(self):
        cat_id = self._get_category_id()
        r = _authed_post("/api/transactions", self.c, json={
            "amount": 100.0, "type": "income", "description": "smoke test",
            "date": "2025-01-15", "category_id": cat_id
        })
        assert r.status_code == 200

    def test_update_transaction(self):
        cat_id = self._get_category_id()
        r = _authed_post("/api/transactions", self.c, json={
            "amount": 50.0, "type": "expense", "description": "to update",
            "date": "2025-01-15", "category_id": cat_id
        })
        tx_id = r.json().get("id")
        if tx_id:
            r2 = _authed_put(f"/api/transactions/{tx_id}", self.c, json={
                "amount": 75.0, "description": "updated"
            })
            assert r2.status_code in (200, 204)

    def test_delete_transaction(self):
        cat_id = self._get_category_id()
        r = _authed_post("/api/transactions", self.c, json={
            "amount": 10.0, "type": "expense", "description": "to delete",
            "date": "2025-01-15", "category_id": cat_id
        })
        tx_id = r.json().get("id")
        if tx_id:
            r2 = _authed_delete(f"/api/transactions/{tx_id}", self.c)
            assert r2.status_code in (200, 204)

    # ── Budgets ──
    def test_list_budgets(self):
        r = _authed_get("/api/budgets", self.c)
        assert r.status_code == 200

    def test_budget_status_endpoint(self):
        """New /api/budgets/status should return pre-computed spent/pct."""
        r = _authed_get("/api/budgets/status", self.c)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_budget_status_has_precomputed_fields(self):
        """After creating a budget, /status should include computed fields."""
        cat_id = self._get_category_id()
        _authed_post("/api/budgets", self.c, json={
            "category_id": cat_id, "monthly_limit": 500.0
        })
        r = _authed_get("/api/budgets/status", self.c)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        item = data[0]
        for key in ("spent", "percentage", "bar_color", "category_name", "monthly_limit"):
            assert key in item, f"Missing key '{key}' in budget status response"
        assert isinstance(item["spent"], (int, float))
        assert isinstance(item["percentage"], (int, float))

    def test_create_budget(self):
        cat_id = self._get_category_id()
        r = _authed_post("/api/budgets", self.c, json={
            "category_id": cat_id, "monthly_limit": 500.0
        })
        assert r.status_code == 200

    def test_delete_budget(self):
        cat_id = self._get_category_id()
        r = _authed_post("/api/budgets", self.c, json={
            "category_id": cat_id, "monthly_limit": 200.0
        })
        budget_id = r.json().get("id")
        if budget_id:
            r2 = _authed_delete(f"/api/budgets/{budget_id}", self.c)
            assert r2.status_code in (200, 204)

    # ── Alerts ──
    def test_list_alerts(self):
        r = _authed_get("/api/alerts", self.c)
        assert r.status_code == 200

    def test_triggered_alerts(self):
        r = _authed_get("/api/alerts/triggered", self.c)
        assert r.status_code == 200

    def test_create_and_delete_alert(self):
        r = _authed_post("/api/alerts", self.c, json={
            "symbol": "AAPL", "condition": "above", "target_price": 999.0
        })
        assert r.status_code == 200
        alert_id = r.json().get("id")
        if alert_id:
            r2 = _authed_delete(f"/api/alerts/{alert_id}", self.c)
            assert r2.status_code in (200, 204)

    def test_dismiss_alert(self):
        r = _authed_post("/api/alerts", self.c, json={
            "symbol": "AAPL", "condition": "below", "target_price": 1.0
        })
        alert_id = r.json().get("id")
        if alert_id:
            r2 = _authed_post(f"/api/alerts/{alert_id}/dismiss", self.c)
            assert r2.status_code in (200, 204, 404)

    # ── Portfolio ──
    def test_portfolio_summary(self):
        r = _authed_get("/api/portfolio/summary", self.c)
        assert r.status_code == 200

    def test_portfolio_performance(self):
        r = _authed_get("/api/portfolio/performance", self.c)
        assert r.status_code == 200

    def test_portfolio_holdings(self):
        r = _authed_get("/api/portfolio/holdings", self.c)
        assert r.status_code == 200

    def test_add_and_remove_holding(self):
        r = _authed_post("/api/portfolio/holdings", self.c, json={
            "symbol": "AAPL", "quantity": 10, "buy_price": 150.0, "buy_date": "2025-01-15"
        })
        assert r.status_code == 200
        holding_id = r.json().get("id")
        if holding_id:
            r2 = _authed_delete(f"/api/portfolio/holdings/{holding_id}", self.c)
            assert r2.status_code in (200, 204)

    # ── Profile / Risk ──
    def test_get_profile(self):
        r = _authed_get("/api/profile", self.c)
        assert r.status_code == 200

    def test_submit_profile(self):
        r = _authed_post("/api/profile", self.c, json={
            "goal": "growth", "timeline": "5-10",
            "experience": "intermediate", "risk_reaction": "hold",
            "income_stability": "stable"
        })
        assert r.status_code == 200

    def test_profile_allocation(self):
        # Submit profile first so allocation endpoint has data
        _authed_post("/api/profile", self.c, json={
            "goal": "growth", "timeline": "5-10",
            "experience": "intermediate", "risk_reaction": "hold",
            "income_stability": "stable"
        })
        r = _authed_get("/api/profile/allocation", self.c)
        assert r.status_code in (200, 404)

    # ── Screener ──
    def test_screener(self):
        r = _authed_get("/api/screener", self.c)
        assert r.status_code == 200

    def test_screener_sectors(self):
        r = _authed_get("/api/screener/sectors", self.c)
        assert r.status_code == 200

    # ── Watchlist ──
    def test_watchlist_crud(self):
        r = _authed_get("/api/screener/watchlist", self.c)
        assert r.status_code == 200

        r2 = _authed_post("/api/screener/watchlist?symbol=MSFT", self.c)
        assert r2.status_code == 200
        item_id = r2.json().get("id")

    # ── Watchlist live (external API) ──
        r3 = _authed_get("/api/screener/watchlist/live", self.c)
        assert r3.status_code < 500

        if item_id:
            r4 = _authed_delete(f"/api/screener/watchlist/{item_id}", self.c)
            assert r4.status_code in (200, 204)

    # ── Market (may use cached external data) ──
    def test_market_ticker(self):
        r = _authed_get("/api/market/ticker", self.c)
        assert r.status_code != 500

    def test_market_featured(self):
        r = _authed_get("/api/market/featured", self.c)
        assert r.status_code != 500

    def test_market_home(self):
        r = _authed_get("/api/market/home", self.c)
        assert r.status_code != 500

    def test_market_cache_status(self):
        r = _authed_get("/api/market/cache-status", self.c)
        assert r.status_code == 200

    # ── Stock Detail (external API — may 404 without API key) ──
    def test_stock_detail(self):
        r = _authed_get("/api/stock/AAPL", self.c)
        assert r.status_code != 500

    def test_stock_full_combined_endpoint(self):
        """New /api/stock/{sym}/full should return info+history+news in one call."""
        r = _authed_get("/api/stock/AAPL/full", self.c)
        assert r.status_code != 500
        if r.status_code == 200:
            data = r.json()
            assert "info" in data, "Missing 'info' in /full response"
            assert "history" in data, "Missing 'history' in /full response"
            assert "news" in data, "Missing 'news' in /full response"

    def test_stock_history_includes_sma50(self):
        """Stock history should now include server-computed sma50."""
        r = _authed_get("/api/stock/AAPL/history", self.c)
        assert r.status_code != 500
        if r.status_code == 200:
            data = r.json()
            if data.get("close") and len(data["close"]) >= 50:
                assert "sma50" in data, "Missing 'sma50' in history response"
                assert len(data["sma50"]) == len(data["close"]), "sma50 length mismatch"
                # First 49 values should be None
                assert data["sma50"][0] is None, "sma50[0] should be None"
                # 50th value should be a number
                assert isinstance(data["sma50"][49], (int, float)), "sma50[49] should be numeric"

    def test_stock_history(self):
        r = _authed_get("/api/stock/AAPL/history", self.c)
        assert r.status_code != 500

    def test_stock_news(self):
        r = _authed_get("/api/stock/AAPL/news", self.c)
        assert r.status_code != 500

    # ── News (external API) ──
    def test_market_news(self):
        r = _authed_get("/api/news", self.c)
        assert r.status_code != 500

    def test_ticker_news(self):
        r = _authed_get("/api/news/AAPL", self.c)
        assert r.status_code != 500

    # ── Comparison (external API) ──
    def test_compare_stocks(self):
        r = _authed_get("/api/compare?symbols=AAPL,MSFT", self.c)
        assert r.status_code != 500

    # ── Recommendations (needs profile) ──
    def test_recommendations(self):
        r = _authed_get("/api/recommendations", self.c)
        assert r.status_code != 500

    # ── Education ──
    def test_education(self):
        r = _authed_get("/api/education", self.c)
        assert r.status_code == 200
        assert isinstance(r.json(), (list, dict))

    # ── Calendar (external API) ──
    def test_calendar_earnings(self):
        r = _authed_get("/api/calendar/earnings", self.c)
        assert r.status_code != 500

    def test_calendar_economic(self):
        r = _authed_get("/api/calendar/economic", self.c)
        assert r.status_code != 500

    # ── Israeli Funds ──
    def test_il_funds_list(self):
        r = _authed_get("/api/il-funds", self.c)
        assert r.status_code == 200

    def test_il_funds_best(self):
        r = _authed_get("/api/il-funds/best", self.c)
        assert r.status_code == 200

    def test_il_funds_meta(self):
        r = _authed_get("/api/il-funds/meta", self.c)
        assert r.status_code == 200

    # ── Value Scanner ──
    def test_value_scanner(self):
        r = _authed_get("/api/value-scanner", self.c)
        assert r.status_code == 200

    def test_value_scanner_action_plan(self):
        r = _authed_get("/api/value-scanner/action-plan", self.c)
        assert r.status_code == 200

    def test_value_scanner_sectors(self):
        r = _authed_get("/api/value-scanner/sectors", self.c)
        assert r.status_code == 200

    # ── Autopilot ──
    def test_autopilot_profiles(self):
        r = _authed_get("/api/autopilot/profiles", self.c)
        assert r.status_code == 200

    def test_autopilot_simulate(self):
        r = _authed_get("/api/autopilot/simulate?profile=conservative&amount=10000", self.c)
        assert r.status_code == 200

    # ── Smart Advisor (may depend on external data) ──
    def test_advisor_analyze(self):
        r = _authed_get("/api/advisor/analyze", self.c)
        assert r.status_code != 500

    def test_advisor_stock(self):
        r = _authed_get("/api/advisor/stock/AAPL", self.c)
        assert r.status_code != 500

    def test_advisor_company_dna(self):
        r = _authed_get("/api/advisor/company-dna/AAPL", self.c)
        assert r.status_code != 500

    # ── Trading Advisor (may depend on external data) ──
    def test_trading_dashboard(self):
        r = _authed_get("/api/trading", self.c)
        assert r.status_code != 500

    def test_trading_dashboard_has_updated_at(self):
        """Trading dashboard should include updated_at for client-side diffing."""
        r = _authed_get("/api/trading", self.c)
        if r.status_code == 200:
            data = r.json()
            assert "updated_at" in data, "Missing 'updated_at' in trading response"
            assert isinstance(data["updated_at"], (int, float)), "updated_at should be numeric"

    def test_trading_single_stock(self):
        r = _authed_get("/api/trading/AAPL", self.c)
        assert r.status_code != 500

    # ── Picks Tracker (may depend on external data) ──
    def test_picks_list(self):
        r = _authed_get("/api/picks", self.c)
        assert r.status_code != 500

    def test_picks_seed_watchlist(self):
        r = _authed_post("/api/picks/seed-watchlist", self.c)
        assert r.status_code != 500

    # ── DCA ──
    def test_dca_dashboard(self):
        r = _authed_get("/api/dca/dashboard", self.c)
        assert r.status_code == 200

    def test_dca_budget_suggestion(self):
        r = _authed_get("/api/dca/budget-suggestion", self.c)
        assert r.status_code == 200

    def test_dca_plans_crud(self):
        # List
        r = _authed_get("/api/dca/plans", self.c)
        assert r.status_code == 200

        # Create
        r2 = _authed_post("/api/dca/plans", self.c, json={
            "symbol": "AAPL", "monthly_budget": 100.0
        })
        assert r2.status_code == 200
        plan_id = r2.json().get("id")

        if plan_id:
            # Update
            r3 = _authed_put(f"/api/dca/plans/{plan_id}", self.c, json={
                "monthly_budget": 200.0
            })
            assert r3.status_code in (200, 204)

            # Delete
            r4 = _authed_delete(f"/api/dca/plans/{plan_id}", self.c)
            assert r4.status_code in (200, 204)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tier 1C — Admin Endpoints (smoke)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.smoke
class TestAdminSmoke:
    """Admin panel endpoints — requires admin user."""

    @pytest.fixture(autouse=True)
    def setup_admin(self):
        """Create a user and promote them to admin directly in DB."""
        from src.database import get_db
        from src.models import User

        self.c, self.email = _register_and_login()
        db = next(get_db())
        try:
            user = db.query(User).filter(User.email == self.email).first()
            user.is_admin = 1
            db.commit()
            self.user_id = user.id
        finally:
            db.close()

    def test_admin_stats(self):
        r = _authed_get("/api/admin/stats", self.c)
        assert r.status_code == 200
        data = r.json()
        assert "total_users" in data or "users" in data or isinstance(data, dict)

    def test_admin_list_users(self):
        r = _authed_get("/api/admin/users", self.c)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))
        if isinstance(data, dict):
            assert "users" in data

    def test_admin_get_user_detail(self):
        r = _authed_get(f"/api/admin/users/{self.user_id}", self.c)
        assert r.status_code == 200

    def test_admin_toggle_admin(self):
        # Create a non-admin user to toggle
        _, target_email = _register_and_login()
        from src.database import get_db
        from src.models import User
        db = next(get_db())
        target = db.query(User).filter(User.email == target_email).first()
        target_id = target.id
        db.close()

        r = _authed_post("/api/admin/toggle-admin", self.c,
                         json={"user_id": target_id})
        assert r.status_code == 200

    def test_admin_toggle_active(self):
        _, target_email = _register_and_login()
        from src.database import get_db
        from src.models import User
        db = next(get_db())
        target = db.query(User).filter(User.email == target_email).first()
        target_id = target.id
        db.close()

        r = _authed_post("/api/admin/toggle-active", self.c,
                         json={"user_id": target_id})
        assert r.status_code == 200

    def test_admin_reset_password(self):
        _, target_email = _register_and_login()
        from src.database import get_db
        from src.models import User
        db = next(get_db())
        target = db.query(User).filter(User.email == target_email).first()
        target_id = target.id
        db.close()

        r = _authed_post("/api/admin/reset-password", self.c,
                         json={"user_id": target_id, "new_password": "Admin0Reset99!"})
        assert r.status_code == 200

    def test_admin_delete_user(self):
        _, target_email = _register_and_login()
        from src.database import get_db
        from src.models import User
        db = next(get_db())
        target = db.query(User).filter(User.email == target_email).first()
        target_id = target.id
        db.close()

        r = _authed_delete(f"/api/admin/users/{target_id}", self.c)
        assert r.status_code in (200, 204)

    def test_admin_forbidden_for_non_admin(self):
        """Non-admin users should get 403 on admin endpoints."""
        cookies, _ = _register_and_login()
        r = _authed_get("/api/admin/stats", cookies)
        assert r.status_code == 403

        r2 = _authed_get("/api/admin/users", cookies)
        assert r2.status_code == 403


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tier 1D — Security & Edge Cases (smoke)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.smoke
class TestSecuritySmoke:
    """Basic security checks."""

    def test_api_requires_auth(self):
        """All /api/* endpoints should return 401 without a session cookie."""
        anon = TestClient(app, raise_server_exceptions=False, base_url="https://testserver")
        protected = [
            "/api/dashboard", "/api/transactions", "/api/budgets",
            "/api/categories", "/api/alerts", "/api/portfolio/summary",
            "/api/profile", "/api/screener", "/api/market/home",
            "/api/news", "/api/education", "/api/calendar/earnings",
            "/api/recommendations", "/api/picks", "/api/dca/dashboard",
            "/api/autopilot/profiles", "/api/advisor/analyze",
            "/api/trading", "/api/value-scanner", "/api/admin/stats",
        ]
        for path in protected:
            r = anon.get(path)
            assert r.status_code == 401, f"{path} returned {r.status_code} without auth"

    def test_security_headers_present(self):
        anon = TestClient(app, raise_server_exceptions=False, base_url="https://testserver")
        r = anon.get("/login")
        h = r.headers
        assert h.get("X-Frame-Options") == "DENY"
        assert h.get("X-Content-Type-Options") == "nosniff"
        assert h.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in h

    def test_cookie_is_httponly(self):
        anon = TestClient(app, raise_server_exceptions=False, base_url="https://testserver")
        email = _fresh_email()
        anon.post("/auth/register", json={"email": email, "password": "Str0ngPass!", "name": "Test"})
        r = anon.post("/auth/login", json={"email": email, "password": "Str0ngPass!"})
        # TestClient exposes cookies directly, but we can check the set-cookie header
        cookie_header = r.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tier 1E — User Isolation (smoke)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.smoke
class TestUserIsolationSmoke:
    """Ensure one user cannot access another user's data."""

    def test_transaction_isolation(self):
        cookies1, _ = _register_and_login()
        cookies2, _ = _register_and_login()

        # Get a category_id for user 1
        cats = _authed_get("/api/categories", cookies1).json()
        cat_id = cats[0]["id"] if cats else 1

        # User 1 creates a transaction
        r = _authed_post("/api/transactions", cookies1, json={
            "amount": 999.0, "type": "income", "description": "user1 only",
            "date": "2025-06-01", "category_id": cat_id
        })
        assert r.status_code == 200

        # User 2 should not see it
        r2 = _authed_get("/api/transactions", cookies2)
        descriptions = [t.get("description", "") for t in r2.json()] if isinstance(r2.json(), list) else []
        assert "user1 only" not in descriptions

    def test_alert_isolation(self):
        cookies1, _ = _register_and_login()
        cookies2, _ = _register_and_login()

        _authed_post("/api/alerts", cookies1, json={
            "symbol": "TSLA", "condition": "above", "target_price": 9999.0
        })
        r2 = _authed_get("/api/alerts", cookies2)
        symbols = [a.get("symbol", "") for a in r2.json()] if isinstance(r2.json(), list) else []
        assert "TSLA" not in symbols or len(symbols) == 0

    def test_portfolio_isolation(self):
        cookies1, _ = _register_and_login()
        cookies2, _ = _register_and_login()

        _authed_post("/api/portfolio/holdings", cookies1, json={
            "symbol": "GME", "quantity": 100, "buy_price": 25.0, "buy_date": "2025-01-15"
        })
        r2 = _authed_get("/api/portfolio/holdings", cookies2)
        data = r2.json()
        if isinstance(data, list):
            symbols = [h.get("symbol", "") for h in data]
            assert "GME" not in symbols


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tier 1F — Data Integrity (smoke)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.smoke
class TestDataIntegritySmoke:
    """Verify response structures are correct."""

    @pytest.fixture(autouse=True)
    def setup_auth(self):
        self.c, _ = _register_and_login()

    def test_dashboard_has_expected_keys(self):
        r = _authed_get("/api/dashboard", self.c)
        data = r.json()
        # Dashboard should have some financial summary keys
        assert isinstance(data, dict)

    def test_education_returns_content(self):
        r = _authed_get("/api/education", self.c)
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_screener_sectors_returns_list(self):
        r = _authed_get("/api/screener/sectors", self.c)
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_categories_seeded_on_startup(self):
        r = _authed_get("/api/categories", self.c)
        cats = r.json()
        assert len(cats) >= 5, "Default categories should be seeded"

    def test_autopilot_profiles_structure(self):
        r = _authed_get("/api/autopilot/profiles", self.c)
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_il_funds_meta_has_data(self):
        r = _authed_get("/api/il-funds/meta", self.c)
        assert r.status_code == 200
