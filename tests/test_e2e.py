"""
End-to-end browser tests for InvestAI.

These tests launch a real Chromium browser, navigate the actual running site,
and exercise every major feature flow — not just "does the button exist" but
"does the feature actually return data and work."

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

    def test_login_page_loads(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        expect(page.locator("h2")).to_have_text("Welcome")
        expect(page.locator("#access-key")).to_be_visible()
        expect(page.locator("#login-btn")).to_have_text("Unlock")

    def test_unauthenticated_redirect(self, page: Page, live_url: str, _live_server):
        page.goto(live_url, wait_until="domcontentloaded")
        expect(page).to_have_url(f"{live_url}/login")

    def test_page_title(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        expect(page).to_have_title("InvestAI — Login")


# ────────────────────────────────────────────
#  Authentication
# ────────────────────────────────────────────

class TestLogin:

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

    def test_navigate_to_each_page(self, authenticated_page: Page):
        for page_id, heading_text in self.NAV_PAGES:
            _nav_click(authenticated_page, page_id)
            section = authenticated_page.locator(f"#page-{page_id}")
            expect(section).to_have_class(re.compile("active"))
            h1 = section.locator("h1")
            expect(h1).to_contain_text(heading_text)


# ────────────────────────────────────────────
#  Dashboard — real data flow
# ────────────────────────────────────────────

class TestDashboardFlow:
    """Dashboard should load stats and charts with actual data."""

    def test_dashboard_stats_show_dollar_values(self, authenticated_page: Page):
        """Income/Expenses/Balance should display dollar-formatted values."""
        income = authenticated_page.locator("#stat-income")
        expenses = authenticated_page.locator("#stat-expenses")
        balance = authenticated_page.locator("#stat-balance")
        expect(income).to_contain_text("$")
        expect(expenses).to_contain_text("$")
        expect(balance).to_contain_text("$")

    def test_market_grid_shows_live_data(self, authenticated_page: Page):
        """Market grid should populate with stock cards from the API."""
        grid = authenticated_page.locator("#market-grid")
        authenticated_page.wait_for_timeout(3000)
        cards = grid.locator(".market-card")
        count = cards.count()
        assert count > 0, (
            f"Market grid has 0 cards — /api/market/featured returned no data. "
            f"Grid HTML: {grid.inner_html()[:300]}"
        )

    def test_ticker_strip_has_data(self, authenticated_page: Page):
        """Ticker bar should show real market symbols."""
        strip = authenticated_page.locator("#ticker-strip")
        authenticated_page.wait_for_timeout(3000)
        html = strip.inner_html()
        assert "ticker-loading" not in html or len(html) > 200, (
            f"Ticker strip never loaded data. Content: {html[:300]}"
        )

    def test_chart_trend_renders(self, authenticated_page: Page):
        """Monthly trend chart canvas should have been drawn on (non-zero size)."""
        canvas = authenticated_page.locator("#chart-trend")
        expect(canvas).to_be_visible()
        width = canvas.evaluate("el => el.width")
        assert width > 0, "Trend chart canvas has zero width — Chart.js didn't render"

    def test_budget_overview_section_present(self, authenticated_page: Page):
        bars = authenticated_page.locator("#budget-bars")
        expect(bars).to_be_attached()


# ────────────────────────────────────────────
#  Transactions — full CRUD flow
# ────────────────────────────────────────────

class TestTransactionsFlow:

    def _go(self, page: Page):
        _nav_click(page, "transactions")

    def test_create_and_see_transaction(self, authenticated_page: Page):
        """Create a transaction via the modal and verify it appears in the table."""
        self._go(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Add Transaction").click(force=True)
        authenticated_page.select_option("#tx-type", "expense")
        authenticated_page.fill("#tx-amount", "99.99")
        authenticated_page.fill("#tx-date", "2026-02-20")
        authenticated_page.fill("#tx-desc", "Playwright E2E grocery")
        authenticated_page.locator('#tx-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(1500)
        expect(authenticated_page.locator("#modal-overlay")).to_be_hidden()
        body = authenticated_page.locator("#tx-body")
        expect(body).to_contain_text("Playwright E2E grocery")
        expect(body).to_contain_text("99.99")

    def test_transaction_table_has_rows(self, authenticated_page: Page):
        """After creating a transaction, the table should have at least one row."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(1000)
        rows = authenticated_page.locator("#tx-body tr")
        count = rows.count()
        assert count > 0, "Transaction table is empty — /api/transactions returned nothing"

    def test_filter_by_type(self, authenticated_page: Page):
        """Selecting expense filter should still show our expense transaction."""
        self._go(authenticated_page)
        authenticated_page.select_option("#filter-type", "expense")
        authenticated_page.get_by_role("button", name="Filter").click(force=True)
        authenticated_page.wait_for_timeout(1000)
        rows = authenticated_page.locator("#tx-body tr")
        assert rows.count() > 0, "Expense filter returned no rows"


# ────────────────────────────────────────────
#  Budgets — full flow
# ────────────────────────────────────────────

class TestBudgetsFlow:

    def _go(self, page: Page):
        _nav_click(page, "budgets")

    def test_create_budget_and_verify_card(self, authenticated_page: Page):
        """Create a budget and verify a budget card with progress bar appears."""
        self._go(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Set Budget").click(force=True)
        authenticated_page.fill("#budget-limit", "300")
        authenticated_page.locator('#budget-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(1500)
        expect(authenticated_page.locator("#budget-modal-overlay")).to_be_hidden()
        grid = authenticated_page.locator("#budgets-grid")
        cards = grid.locator(".budget-card")
        assert cards.count() > 0, (
            "No budget cards appeared after creating a budget. "
            f"Grid HTML: {grid.inner_html()[:300]}"
        )

    def test_budget_card_shows_progress(self, authenticated_page: Page):
        """Budget cards should show a progress bar and spent/limit text."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(1000)
        card = authenticated_page.locator(".budget-card").first
        html = card.inner_html()
        assert "$" in html or "%" in html, (
            f"Budget card doesn't show any dollar or percent values: {html[:300]}"
        )


# ────────────────────────────────────────────
#  Risk Profile — wizard flow
# ────────────────────────────────────────────

class TestProfileFlow:

    def test_profile_wizard_loads(self, authenticated_page: Page):
        """Risk profile page should show a wizard with questions or a result."""
        _nav_click(authenticated_page, "profile")
        authenticated_page.wait_for_timeout(1500)
        wizard = authenticated_page.locator("#wizard-content")
        result = authenticated_page.locator("#profile-result")
        wizard_html = wizard.inner_html()
        result_visible = result.is_visible()
        assert len(wizard_html) > 10 or result_visible, (
            "Profile page is empty — neither wizard nor result loaded"
        )

    def test_profile_wizard_has_interactive_options(self, authenticated_page: Page):
        """The wizard should have clickable answer options or a saved result."""
        _nav_click(authenticated_page, "profile")
        authenticated_page.wait_for_timeout(1500)
        result = authenticated_page.locator("#profile-result")
        if result.is_visible():
            return  # already completed
        options = authenticated_page.locator("#wizard-content .wizard-option, #wizard-content button")
        count = options.count()
        assert count > 0, (
            "Wizard has no clickable options — /api/profile did not return questions"
        )


# ────────────────────────────────────────────
#  Screener — search flow
# ────────────────────────────────────────────

class TestScreenerFlow:

    def test_screener_filters_populated_from_api(self, authenticated_page: Page):
        """Sector and region dropdowns should be populated by /api/screener/sectors."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(2000)
        sector_opts = authenticated_page.locator("#scr-sector option")
        region_opts = authenticated_page.locator("#scr-region option")
        assert sector_opts.count() > 1, (
            f"Sector dropdown only has {sector_opts.count()} option(s) — "
            "/api/screener/sectors returned no sectors"
        )
        assert region_opts.count() > 1, (
            f"Region dropdown only has {region_opts.count()} option(s) — "
            "/api/screener/sectors returned no regions"
        )

    def test_screener_search_returns_results(self, authenticated_page: Page):
        """Running a screener search should return at least one stock card."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(5000)
        results = authenticated_page.locator("#scr-results-area")
        html = results.inner_html()
        assert len(html) > 50, (
            f"Screener returned empty results. /api/screener returned no data. "
            f"HTML: {html[:300]}"
        )

    def test_screener_preset_value_stocks(self, authenticated_page: Page):
        """Clicking 'Value Stocks' preset and searching should return results."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Value Stocks").click()
        authenticated_page.wait_for_timeout(500)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(5000)
        count_el = authenticated_page.locator("#scr-result-count")
        count_text = count_el.inner_text()
        assert count_text != "", (
            "Result count is empty after Value Stocks preset search"
        )


# ────────────────────────────────────────────
#  Recommendations
# ────────────────────────────────────────────

class TestRecommendationsFlow:

    def test_recommendations_loads_content_or_prompt(self, authenticated_page: Page):
        """Should show recommendations or a prompt to complete risk profile."""
        _nav_click(authenticated_page, "recommendations")
        authenticated_page.wait_for_timeout(3000)
        container = authenticated_page.locator("#recs-container")
        no_profile = authenticated_page.locator("#recs-no-profile")
        has_recs = len(container.inner_html()) > 20
        shows_prompt = no_profile.is_visible()
        assert has_recs or shows_prompt, (
            "Recommendations page is blank — neither recommendations nor profile prompt loaded"
        )


# ────────────────────────────────────────────
#  Watchlist
# ────────────────────────────────────────────

class TestWatchlistFlow:

    def test_watchlist_loads(self, authenticated_page: Page):
        """Watchlist should show cards or an empty state message."""
        _nav_click(authenticated_page, "watchlist")
        authenticated_page.wait_for_timeout(3000)
        container = authenticated_page.locator("#watchlist-container")
        html = container.inner_html()
        has_cards = ".watchlist-card" in html or "card" in html.lower()
        has_empty = "empty" in html.lower() or "no " in html.lower() or "add" in html.lower()
        assert has_cards or has_empty or len(html) > 20, (
            f"Watchlist page is blank — /api/screener/watchlist/live returned nothing. "
            f"HTML: {html[:300]}"
        )


# ────────────────────────────────────────────
#  News
# ────────────────────────────────────────────

class TestNewsFlow:

    def test_news_loads_articles(self, authenticated_page: Page):
        """News page should show article cards from /api/news."""
        _nav_click(authenticated_page, "news")
        authenticated_page.wait_for_timeout(5000)
        container = authenticated_page.locator("#news-container")
        html = container.inner_html()
        assert len(html) > 50, (
            f"News page is empty — /api/news returned no articles. "
            f"HTML: {html[:300]}"
        )

    def test_news_count_shown(self, authenticated_page: Page):
        """The news count badge should display a number."""
        _nav_click(authenticated_page, "news")
        authenticated_page.wait_for_timeout(5000)
        count = authenticated_page.locator("#news-count")
        text = count.inner_text()
        assert text != "", f"News count is empty — expected a number"


# ────────────────────────────────────────────
#  Portfolio — add holding flow
# ────────────────────────────────────────────

class TestPortfolioFlow:

    def test_add_holding_and_verify(self, authenticated_page: Page):
        """Add a stock holding and verify the portfolio page shows it."""
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("text=+ Add Holding").click(force=True)
        authenticated_page.fill("#holding-symbol", "AAPL")
        authenticated_page.fill("#holding-name", "Apple Inc.")
        authenticated_page.fill("#holding-qty", "10")
        authenticated_page.fill("#holding-price", "150.00")
        authenticated_page.fill("#holding-date", "2025-01-15")
        authenticated_page.locator('#holding-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(12000)
        container = authenticated_page.locator("#portfolio-container")
        html = container.inner_html()
        assert "AAPL" in html, (
            f"Portfolio does not show AAPL after adding holding. "
            f"HTML: {html[:500]}"
        )

    def test_portfolio_summary_has_values(self, authenticated_page: Page):
        """Portfolio page should show total value, gain/loss etc."""
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(12000)
        container = authenticated_page.locator("#portfolio-container")
        html = container.inner_html()
        assert "$" in html, (
            f"Portfolio shows no dollar values — summary didn't load. "
            f"HTML: {html[:500]}"
        )


# ────────────────────────────────────────────
#  Comparison — compare stocks flow
# ────────────────────────────────────────────

class TestComparisonFlow:

    def test_compare_stocks_returns_data(self, authenticated_page: Page):
        """Enter symbols and compare — should show a chart and table."""
        _nav_click(authenticated_page, "comparison")
        authenticated_page.fill("#compare-input", "AAPL, MSFT")
        authenticated_page.get_by_role("button", name="Compare").click()
        authenticated_page.wait_for_timeout(20000)
        results = authenticated_page.locator("#compare-results")
        html = results.inner_html()
        assert len(html) > 50, (
            f"Comparison returned no results for AAPL, MSFT. "
            f"/api/compare failed. HTML: {html[:300]}"
        )
        assert "AAPL" in html or "aapl" in html.lower(), (
            f"Comparison results don't mention AAPL. HTML: {html[:500]}"
        )


# ────────────────────────────────────────────
#  Alerts — create alert flow
# ────────────────────────────────────────────

class TestAlertsFlow:

    def test_create_alert_and_verify(self, authenticated_page: Page):
        """Create a price alert and verify it shows in the list."""
        _nav_click(authenticated_page, "alerts")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("text=+ New Alert").click(force=True)
        authenticated_page.fill("#alert-symbol", "TSLA")
        authenticated_page.select_option("#alert-condition", "above")
        authenticated_page.fill("#alert-price", "300")
        authenticated_page.locator('#alert-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(2000)
        container = authenticated_page.locator("#alerts-container")
        html = container.inner_html()
        assert "TSLA" in html, (
            f"Alert for TSLA not found after creation. "
            f"HTML: {html[:500]}"
        )

    def test_alerts_page_loads_list(self, authenticated_page: Page):
        """Alerts page should load and display active/triggered sections."""
        _nav_click(authenticated_page, "alerts")
        authenticated_page.wait_for_timeout(2000)
        container = authenticated_page.locator("#alerts-container")
        html = container.inner_html()
        assert len(html) > 20, (
            f"Alerts container is empty. HTML: {html[:300]}"
        )


# ────────────────────────────────────────────
#  Calendar
# ────────────────────────────────────────────

class TestCalendarFlow:

    def test_calendar_loads_content(self, authenticated_page: Page):
        """Calendar should show earnings/events or at least tab structure."""
        _nav_click(authenticated_page, "calendar")
        authenticated_page.wait_for_timeout(5000)
        container = authenticated_page.locator("#calendar-container")
        html = container.inner_html()
        assert len(html) > 30, (
            f"Calendar page is blank — /api/calendar endpoints returned nothing. "
            f"HTML: {html[:300]}"
        )


# ────────────────────────────────────────────
#  Education
# ────────────────────────────────────────────

class TestEducationFlow:

    def test_education_loads_articles(self, authenticated_page: Page):
        """Education page should show learning content cards."""
        _nav_click(authenticated_page, "education")
        authenticated_page.wait_for_timeout(3000)
        container = authenticated_page.locator("#edu-container")
        html = container.inner_html()
        assert len(html) > 50, (
            f"Education page is empty — /api/education returned no content. "
            f"HTML: {html[:300]}"
        )


# ────────────────────────────────────────────
#  Israeli Funds
# ────────────────────────────────────────────

class TestILFundsFlow:

    def test_il_funds_filters_loaded(self, authenticated_page: Page):
        """Fund type and manager dropdowns should be populated from /api/il-funds/meta."""
        _nav_click(authenticated_page, "il-funds")
        authenticated_page.wait_for_timeout(3000)
        type_opts = authenticated_page.locator("#il-filter-type option")
        assert type_opts.count() > 1, (
            f"IL Fund Type filter has only {type_opts.count()} option(s) — "
            "/api/il-funds/meta returned no types"
        )

    def test_il_funds_search_returns_results(self, authenticated_page: Page):
        """Running a fund search should return results."""
        _nav_click(authenticated_page, "il-funds")
        authenticated_page.wait_for_timeout(2000)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(5000)
        results = authenticated_page.locator("#il-results-area")
        html = results.inner_html()
        assert len(html) > 50, (
            f"IL Funds search returned no results. "
            f"HTML: {html[:300]}"
        )

    def test_il_funds_best_deals_loaded(self, authenticated_page: Page):
        """The best deals / kaspit highlight section should have content."""
        _nav_click(authenticated_page, "il-funds")
        authenticated_page.wait_for_timeout(8000)
        highlight = authenticated_page.locator("#il-kaspit-highlight")
        html = highlight.inner_html()
        assert len(html) > 20, (
            f"Kaspit highlight / best deals section is empty. "
            f"HTML: {html[:300]}"
        )
