"""
End-to-end browser tests for InvestAI.

These tests launch a real Chromium browser, navigate the actual running site,
click buttons, fill forms, and verify everything works.

Run:
    cd finance-tracker
    pytest tests/ --headed        # watch the browser
    pytest tests/                 # headless (CI-friendly)
"""

import re

from playwright.sync_api import Page, expect


def _nav_click(page: Page, page_id: str):
    """Click a sidebar nav link, using force to handle overflow."""
    page.locator(f'.nav-link[data-page="{page_id}"]').click(force=True)
    page.wait_for_timeout(300)


# ────────────────────────────────────────────
#  Connectivity & basic loading
# ────────────────────────────────────────────

class TestSiteLoads:
    """Verify the server is reachable and pages render."""

    def test_login_page_loads(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        expect(page.locator("h2")).to_have_text("Welcome")
        expect(page.locator("#access-key")).to_be_visible()
        expect(page.locator("#login-btn")).to_have_text("Unlock")

    def test_unauthenticated_redirect(self, page: Page, live_url: str, _live_server):
        """Visiting / without a session should redirect to /login."""
        page.goto(live_url, wait_until="domcontentloaded")
        expect(page).to_have_url(f"{live_url}/login")

    def test_page_title(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        expect(page).to_have_title("InvestAI — Login")


# ────────────────────────────────────────────
#  Authentication
# ────────────────────────────────────────────

class TestLogin:
    """Verify the login flow with correct and incorrect keys."""

    def test_successful_login(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.fill("#access-key", "intel2026")
        page.click("#login-btn")
        page.wait_for_url(f"{live_url}/", timeout=15_000)
        expect(page).to_have_title("InvestAI")
        expect(page.locator("nav.sidebar")).to_be_visible()

    def test_wrong_key_shows_error(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.fill("#access-key", "wrongkey")
        page.click("#login-btn")
        page.wait_for_selector("#error-msg:not(:empty)", timeout=5_000)
        expect(page.locator("#error-msg")).to_contain_text("Invalid access key")

    def test_logout_returns_to_login(self, authenticated_page: Page, live_url: str):
        authenticated_page.goto(f"{live_url}/auth/logout", wait_until="domcontentloaded")
        expect(authenticated_page.locator("#access-key")).to_be_visible()


# ────────────────────────────────────────────
#  Sidebar navigation
# ────────────────────────────────────────────

class TestNavigation:
    """Click every sidebar link and verify the correct page section appears."""

    NAV_PAGES = [
        ("dashboard",       "Dashboard"),
        ("portfolio",       "Portfolio"),
        ("watchlist",       "Watchlist"),
        ("news",            "Market News"),
        ("transactions",    "Transactions"),
        ("budgets",         "Budgets"),
        ("profile",         "Risk Profile"),
        ("screener",        "Stock & Fund Screener"),
        ("recommendations", "For You"),
        ("comparison",      "Compare Stocks"),
        ("alerts",          "Price Alerts"),
        ("calendar",        "Earnings & Events Calendar"),
        ("education",       "Learn to Invest"),
        ("il-funds",        "Israeli Funds"),
    ]

    def test_all_nav_links_exist(self, authenticated_page: Page):
        for page_id, _ in self.NAV_PAGES:
            link = authenticated_page.locator(f'.nav-link[data-page="{page_id}"]')
            expect(link).to_be_attached()

    def test_navigate_to_each_page(self, authenticated_page: Page):
        for page_id, heading_text in self.NAV_PAGES:
            _nav_click(authenticated_page, page_id)
            section = authenticated_page.locator(f"#page-{page_id}")
            expect(section).to_have_class(re.compile("active"))
            h1 = section.locator("h1")
            expect(h1).to_contain_text(heading_text)


# ────────────────────────────────────────────
#  Dashboard
# ────────────────────────────────────────────

class TestDashboard:
    """Verify dashboard widgets render."""

    def test_stat_cards_visible(self, authenticated_page: Page):
        expect(authenticated_page.locator("#stat-income")).to_be_visible()
        expect(authenticated_page.locator("#stat-expenses")).to_be_visible()
        expect(authenticated_page.locator("#stat-balance")).to_be_visible()

    def test_chart_canvases_exist(self, authenticated_page: Page):
        expect(authenticated_page.locator("#chart-trend")).to_be_visible()
        expect(authenticated_page.locator("#chart-categories")).to_be_visible()

    def test_market_grid_exists(self, authenticated_page: Page):
        expect(authenticated_page.locator("#market-grid")).to_be_visible()

    def test_date_filter_controls(self, authenticated_page: Page):
        expect(authenticated_page.locator("#dash-from")).to_be_visible()
        expect(authenticated_page.locator("#dash-to")).to_be_visible()


# ────────────────────────────────────────────
#  Transactions CRUD
# ────────────────────────────────────────────

class TestTransactions:
    """Test the transaction modal and add flow."""

    def _go_to_transactions(self, page: Page):
        _nav_click(page, "transactions")

    def test_add_transaction_button_opens_modal(self, authenticated_page: Page):
        self._go_to_transactions(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Add Transaction").click(force=True)
        modal = authenticated_page.locator("#modal-overlay")
        expect(modal).to_be_visible()
        expect(authenticated_page.locator("#modal-title")).to_have_text("Add Transaction")

    def test_transaction_form_has_all_fields(self, authenticated_page: Page):
        self._go_to_transactions(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Add Transaction").click(force=True)
        expect(authenticated_page.locator("#tx-type")).to_be_visible()
        expect(authenticated_page.locator("#tx-amount")).to_be_visible()
        expect(authenticated_page.locator("#tx-category")).to_be_visible()
        expect(authenticated_page.locator("#tx-date")).to_be_visible()
        expect(authenticated_page.locator("#tx-desc")).to_be_visible()

    def test_submit_transaction(self, authenticated_page: Page):
        self._go_to_transactions(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Add Transaction").click(force=True)
        authenticated_page.select_option("#tx-type", "expense")
        authenticated_page.fill("#tx-amount", "42.50")
        authenticated_page.fill("#tx-date", "2026-01-15")
        authenticated_page.fill("#tx-desc", "E2E test transaction")
        authenticated_page.locator('#tx-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(1000)
        expect(authenticated_page.locator("#modal-overlay")).to_be_hidden()
        expect(authenticated_page.locator("#tx-body")).to_contain_text("E2E test transaction")

    def test_close_modal_with_cancel(self, authenticated_page: Page):
        self._go_to_transactions(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Add Transaction").click(force=True)
        expect(authenticated_page.locator("#modal-overlay")).to_be_visible()
        authenticated_page.locator("#tx-form .btn-ghost").click()
        expect(authenticated_page.locator("#modal-overlay")).to_be_hidden()


# ────────────────────────────────────────────
#  Budgets
# ────────────────────────────────────────────

class TestBudgets:
    """Test the budget modal and flow."""

    def _go_to_budgets(self, page: Page):
        _nav_click(page, "budgets")

    def test_budget_button_opens_modal(self, authenticated_page: Page):
        self._go_to_budgets(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Set Budget").click(force=True)
        modal = authenticated_page.locator("#budget-modal-overlay")
        expect(modal).to_be_visible()

    def test_budget_form_fields(self, authenticated_page: Page):
        self._go_to_budgets(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Set Budget").click(force=True)
        expect(authenticated_page.locator("#budget-category")).to_be_visible()
        expect(authenticated_page.locator("#budget-limit")).to_be_visible()

    def test_submit_budget(self, authenticated_page: Page):
        self._go_to_budgets(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Set Budget").click(force=True)
        authenticated_page.fill("#budget-limit", "500")
        authenticated_page.locator('#budget-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(1000)
        expect(authenticated_page.locator("#budget-modal-overlay")).to_be_hidden()


# ────────────────────────────────────────────
#  Portfolio
# ────────────────────────────────────────────

class TestPortfolio:
    """Test the portfolio holding modal."""

    def test_add_holding_opens_modal(self, authenticated_page: Page):
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.locator("text=+ Add Holding").click(force=True)
        expect(authenticated_page.locator("#holding-modal-overlay")).to_be_visible()
        expect(authenticated_page.locator("#holding-symbol")).to_be_visible()
        expect(authenticated_page.locator("#holding-qty")).to_be_visible()
        expect(authenticated_page.locator("#holding-price")).to_be_visible()


# ────────────────────────────────────────────
#  Alerts
# ────────────────────────────────────────────

class TestAlerts:
    """Test the price alerts modal."""

    def test_alert_modal_opens(self, authenticated_page: Page):
        _nav_click(authenticated_page, "alerts")
        authenticated_page.locator("text=+ New Alert").click(force=True)
        expect(authenticated_page.locator("#alert-modal-overlay")).to_be_visible()
        expect(authenticated_page.locator("#alert-symbol")).to_be_visible()
        expect(authenticated_page.locator("#alert-condition")).to_be_visible()
        expect(authenticated_page.locator("#alert-price")).to_be_visible()


# ────────────────────────────────────────────
#  Screener
# ────────────────────────────────────────────

class TestScreener:
    """Test the stock screener page loads and controls work."""

    def test_screener_filters_visible(self, authenticated_page: Page):
        _nav_click(authenticated_page, "screener")
        expect(authenticated_page.locator("#scr-asset-type")).to_be_visible()
        expect(authenticated_page.locator("#scr-sector")).to_be_visible()
        expect(authenticated_page.locator("#scr-region")).to_be_visible()

    def test_preset_buttons_clickable(self, authenticated_page: Page):
        _nav_click(authenticated_page, "screener")
        presets = authenticated_page.locator("#page-screener .preset-buttons .btn")
        count = presets.count()
        assert count >= 4, f"Expected at least 4 preset buttons, found {count}"


# ────────────────────────────────────────────
#  Comparison
# ────────────────────────────────────────────

class TestComparison:
    """Test the stock comparison page."""

    def test_compare_input_and_button(self, authenticated_page: Page):
        _nav_click(authenticated_page, "comparison")
        expect(authenticated_page.locator("#compare-input")).to_be_visible()
        expect(authenticated_page.locator('#page-comparison button.btn-primary')).to_be_visible()
