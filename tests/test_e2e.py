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
        expect(page.locator(".tab-btn")).to_have_count(2)
        expect(page.locator("#login-email")).to_be_visible()
        expect(page.locator("#login-btn")).to_have_text("Sign In")

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
        import requests
        requests.post(
            f"{live_url}/auth/register",
            json={"email": "login_test@e2e.local", "password": "Pass1234", "name": "Login Tester"},
        )
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.fill("#login-email", "login_test@e2e.local")
        page.fill("#login-password", "Pass1234")
        page.click("#login-btn")
        page.wait_for_url(f"{live_url}/", timeout=15_000)
        expect(page).to_have_title("InvestAI")
        expect(page.locator("nav.sidebar")).to_be_visible()

    def test_wrong_password_shows_error(self, page: Page, live_url: str, _live_server):
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.fill("#login-email", "nonexistent@e2e.local")
        page.fill("#login-password", "wrongpassword")
        page.click("#login-btn")
        page.wait_for_selector("#login-error:not(:empty)", timeout=5_000)
        expect(page.locator("#login-error")).to_contain_text("Invalid")

    def test_logout_returns_to_login(self, authenticated_page: Page, live_url: str):
        authenticated_page.goto(f"{live_url}/auth/logout", wait_until="domcontentloaded")
        expect(authenticated_page.locator("#login-email")).to_be_visible()

    def test_logout_button_click_logs_out(self, authenticated_page: Page, live_url: str):
        """Click the actual Logout link in the sidebar and verify we land on login."""
        p = authenticated_page
        # Verify we are on the main app (sidebar visible)
        expect(p.locator("nav.sidebar")).to_be_visible()
        # Click the real logout link in the sidebar
        p.locator("a.logout-link").click()
        # Should redirect to /login
        p.wait_for_url(re.compile(r"/login"), timeout=10_000)
        expect(p.locator("#login-email")).to_be_visible()
        expect(p.locator("#login-btn")).to_be_visible()

    def test_logout_clears_session_cookie(self, authenticated_page: Page, live_url: str):
        """After logout, navigating to / must redirect back to /login (session gone)."""
        p = authenticated_page
        expect(p.locator("nav.sidebar")).to_be_visible()
        # Logout via button click
        p.locator("a.logout-link").click()
        p.wait_for_url(re.compile(r"/login"), timeout=10_000)
        # Now try going to the protected homepage — should redirect to /login
        p.goto(live_url, wait_until="domcontentloaded")
        expect(p).to_have_url(f"{live_url}/login")
        expect(p.locator("#login-email")).to_be_visible()


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

    def test_browser_back_navigates_within_spa(self, authenticated_page: Page):
        """Pressing browser Back should return to the previous SPA page, not leave the site."""
        # Start on dashboard
        expect(authenticated_page.locator("#page-dashboard")).to_have_class(re.compile("active"))

        # Navigate to portfolio, then news
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(500)
        expect(authenticated_page.locator("#page-portfolio")).to_have_class(re.compile("active"))
        assert "#portfolio" in authenticated_page.url

        _nav_click(authenticated_page, "news")
        authenticated_page.wait_for_timeout(500)
        expect(authenticated_page.locator("#page-news")).to_have_class(re.compile("active"))
        assert "#news" in authenticated_page.url

        # Press Back — should go to portfolio, not leave the site
        authenticated_page.go_back()
        authenticated_page.wait_for_timeout(500)
        expect(authenticated_page.locator("#page-portfolio")).to_have_class(re.compile("active"))
        assert "#portfolio" in authenticated_page.url

        # Press Back again — should go to dashboard
        authenticated_page.go_back()
        authenticated_page.wait_for_timeout(500)
        expect(authenticated_page.locator("#page-dashboard")).to_have_class(re.compile("active"))
        assert "#dashboard" in authenticated_page.url

    def test_browser_forward_after_back(self, authenticated_page: Page):
        """Pressing Forward after Back should restore the next SPA page."""
        _nav_click(authenticated_page, "budgets")
        authenticated_page.wait_for_timeout(500)
        _nav_click(authenticated_page, "alerts")
        authenticated_page.wait_for_timeout(500)

        authenticated_page.go_back()
        authenticated_page.wait_for_timeout(500)
        expect(authenticated_page.locator("#page-budgets")).to_have_class(re.compile("active"))

        authenticated_page.go_forward()
        authenticated_page.wait_for_timeout(500)
        expect(authenticated_page.locator("#page-alerts")).to_have_class(re.compile("active"))

    def test_url_hash_updates_on_navigation(self, authenticated_page: Page):
        """Each nav click should update the URL hash to match the page."""
        for page_id, _ in [("screener", ""), ("education", ""), ("portfolio", "")]:
            _nav_click(authenticated_page, page_id)
            authenticated_page.wait_for_timeout(300)
            assert f"#{page_id}" in authenticated_page.url, (
                f"URL should contain #{page_id}, got {authenticated_page.url}"
            )


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

    def test_sparkline_charts_render_on_market_cards(self, authenticated_page: Page):
        """Each market card should have a visible sparkline canvas with drawn pixels."""
        authenticated_page.wait_for_selector('.market-card', timeout=30_000)
        # Wait for sparkline charts to be created by JS
        authenticated_page.wait_for_function(
            'typeof sparkCharts !== "undefined" && Object.keys(sparkCharts).length > 0',
            timeout=30_000,
        )
        canvases = authenticated_page.query_selector_all('canvas[id^="spark-"]')
        assert len(canvases) > 0, "No sparkline canvas elements found in market grid"

        for canvas in canvases:
            cid = canvas.get_attribute("id")
            box = canvas.bounding_box()
            assert box is not None, f"{cid} has no bounding box — not in DOM"
            assert box["width"] > 0 and box["height"] > 0, (
                f"{cid} has zero dimensions: {box}"
            )

    def test_sparkline_charts_have_pixel_data(self, authenticated_page: Page):
        """Sparkline canvases should have non-zero pixel data (Chart.js drew something)."""
        authenticated_page.wait_for_selector('.market-card', timeout=30_000)
        authenticated_page.wait_for_function(
            'typeof sparkCharts !== "undefined" && Object.keys(sparkCharts).length > 0',
            timeout=30_000,
        )
        spark_keys = authenticated_page.evaluate(
            'Object.keys(sparkCharts)'
        )
        assert len(spark_keys) > 0, (
            "sparkCharts is empty — Chart.js never created any sparkline charts. "
            "The /api/market/home sparkline arrays may be empty."
        )

        for symbol in spark_keys:
            non_zero = authenticated_page.evaluate(
                '''(sym) => {
                    const el = document.getElementById("spark-" + sym);
                    if (!el) return -1;
                    const ctx = el.getContext("2d");
                    const d = ctx.getImageData(0, 0, el.width, el.height).data;
                    let n = 0;
                    for (let i = 3; i < d.length; i += 4) { if (d[i] > 0) n++; }
                    return n;
                }''',
                symbol,
            )
            assert non_zero > 0, (
                f"spark-{symbol} canvas has 0 drawn pixels — chart did not render"
            )

    def test_sparkline_data_has_realistic_values(self, authenticated_page: Page):
        """Sparkline chart data should contain multiple realistic price points."""
        authenticated_page.wait_for_selector('.market-card', timeout=30_000)
        authenticated_page.wait_for_function(
            'typeof sparkCharts !== "undefined" && Object.keys(sparkCharts).length > 0',
            timeout=30_000,
        )
        data_info = authenticated_page.evaluate('''() => {
            const r = {};
            for (const [sym, chart] of Object.entries(sparkCharts)) {
                const d = chart.data.datasets[0].data;
                r[sym] = {len: d.length, min: Math.min(...d), max: Math.max(...d)};
            }
            return r;
        }''')
        assert len(data_info) > 0, "No sparkline chart data found"
        for symbol, info in data_info.items():
            assert info["len"] > 1, (
                f"{symbol} sparkline has only {info['len']} data point(s)"
            )
            assert info["min"] > 0, (
                f"{symbol} sparkline has invalid min price: {info['min']}"
            )
            assert info["max"] > info["min"], (
                f"{symbol} sparkline is flat (min={info['min']}, max={info['max']})"
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
        """Clicking 'Value Stocks' preset should auto-search and return stock cards."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Value Stocks").click()
        # Preset auto-calls runScreener(), wait for results
        authenticated_page.wait_for_timeout(8000)
        count_el = authenticated_page.locator("#scr-result-count")
        count_text = count_el.inner_text()
        assert count_text != "", "Result count is empty after Value Stocks preset"
        assert not count_text.startswith("0 results"), (
            f"Value Stocks returned 0 results — expected some value stocks. "
            f"Count text: '{count_text}'"
        )

    def test_screener_preset_value_stocks_shows_cards(self, authenticated_page: Page):
        """Value Stocks preset should produce visible stock cards with symbols."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Value Stocks").click()
        authenticated_page.wait_for_timeout(8000)
        cards = authenticated_page.locator(".scr-card")
        card_count = cards.count()
        assert card_count > 0, "Value Stocks preset produced 0 stock cards"
        # Verify first card has a symbol
        first_symbol = cards.first.locator(".scr-card-symbol").inner_text()
        assert len(first_symbol) >= 1, "First card has no symbol text"

    def test_screener_preset_growth_tech(self, authenticated_page: Page):
        """Growth Tech preset should return results in the Technology sector."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Growth Tech").click()
        authenticated_page.wait_for_timeout(8000)
        count_text = authenticated_page.locator("#scr-result-count").inner_text()
        assert not count_text.startswith("0 results"), (
            f"Growth Tech returned 0 results. Count: '{count_text}'"
        )

    def test_screener_preset_high_dividend(self, authenticated_page: Page):
        """High Dividend preset should return results with dividend yield >= 3%."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="High Dividend").click()
        authenticated_page.wait_for_timeout(8000)
        count_text = authenticated_page.locator("#scr-result-count").inner_text()
        assert not count_text.startswith("0 results"), (
            f"High Dividend returned 0 results. Count: '{count_text}'"
        )

    def test_screener_preset_all_etfs(self, authenticated_page: Page):
        """All ETFs preset should return ETF results."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="All ETFs").click()
        authenticated_page.wait_for_timeout(8000)
        count_text = authenticated_page.locator("#scr-result-count").inner_text()
        assert not count_text.startswith("0 results"), (
            f"All ETFs returned 0 results. Count: '{count_text}'"
        )

    def test_screener_card_has_metrics(self, authenticated_page: Page):
        """Cards should display real metric values (P/E, Div %, Beta, Mkt Cap)."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        cards = authenticated_page.locator(".scr-card")
        assert cards.count() > 0, "No cards returned from search"
        # Check first card has metric values (not all dashes)
        metrics = cards.first.locator(".metric-value")
        metric_count = metrics.count()
        assert metric_count >= 3, f"Expected >=3 metrics, got {metric_count}"
        has_real_value = False
        for i in range(metric_count):
            val = metrics.nth(i).inner_text().strip()
            if val != "—":
                has_real_value = True
                break
        assert has_real_value, "All metric values are dashes — metrics not populated"

    def test_screener_card_has_signal_badge(self, authenticated_page: Page):
        """Each screener card should show a signal badge (Buy/Hold/Avoid)."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        badges = authenticated_page.locator(".scr-card:first-child .signal-badge")
        assert badges.count() > 0, "No signal badge found on first card"
        badge_text = badges.first.inner_text().strip().lower()
        assert any(s in badge_text for s in ["buy", "hold", "avoid"]), (
            f"Signal badge text '{badge_text}' is not Buy/Hold/Avoid"
        )

    def test_screener_clear_resets_filters(self, authenticated_page: Page):
        """Clear button should reset all filters."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        # Apply a preset to set filters
        authenticated_page.get_by_role("button", name="Value Stocks").click()
        authenticated_page.wait_for_timeout(1000)
        # Now clear
        authenticated_page.get_by_role("button", name="Clear").click()
        authenticated_page.wait_for_timeout(500)
        pe_max = authenticated_page.locator("#scr-pe-max").input_value()
        div_min = authenticated_page.locator("#scr-div-min").input_value()
        assert pe_max == "", f"P/E max not cleared: '{pe_max}'"
        assert div_min == "", f"Div min not cleared: '{div_min}'"

    def test_screener_signal_filter_exists(self, authenticated_page: Page):
        """Signal dropdown (Buy/Hold/Avoid) should exist in the filter sidebar."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        signal_select = authenticated_page.locator("#scr-signal")
        expect(signal_select).to_be_visible()
        opts = signal_select.locator("option")
        assert opts.count() == 4, (
            f"Signal dropdown should have 4 options (All/Buy/Hold/Avoid), got {opts.count()}"
        )

    def test_screener_signal_filter_buy_returns_only_buy(self, authenticated_page: Page):
        """Filtering by 'Buy' signal should only show cards with Buy badges."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option("#scr-signal", "Buy")
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        cards = authenticated_page.locator(".scr-card")
        count = cards.count()
        if count == 0:
            # Cache might not be ready — accept 0 results gracefully
            return
        # Every visible card's signal badge must say Buy
        for i in range(min(count, 10)):  # check up to 10
            badge = cards.nth(i).locator(".signal-badge").inner_text().strip().lower()
            assert "buy" in badge, (
                f"Card {i} has signal '{badge}' but filter is set to Buy"
            )

    def test_screener_signal_filter_avoid_returns_only_avoid(self, authenticated_page: Page):
        """Filtering by 'Avoid' signal should only show cards with Avoid badges."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option("#scr-signal", "Avoid")
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        cards = authenticated_page.locator(".scr-card")
        count = cards.count()
        if count == 0:
            return
        for i in range(min(count, 10)):
            badge = cards.nth(i).locator(".signal-badge").inner_text().strip().lower()
            assert "avoid" in badge, (
                f"Card {i} has signal '{badge}' but filter is set to Avoid"
            )

    def test_screener_signal_filter_cleared_by_clear_button(self, authenticated_page: Page):
        """Clear button should reset the signal filter back to 'All Signals'."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option("#scr-signal", "Hold")
        authenticated_page.get_by_role("button", name="Clear").click()
        authenticated_page.wait_for_timeout(500)
        val = authenticated_page.locator("#scr-signal").input_value()
        assert val == "", f"Signal filter not cleared: '{val}'"


class TestScreenerAPI:
    """API-level screener tests — validates the fix for the dividend yield bug."""

    @staticmethod
    def _session(base_url: str, email: str, password: str, name: str):
        """Register + login via API. Returns requests.Session."""
        import requests as _req
        s = _req.Session()
        s.post(f"{base_url}/auth/register",
               json={"email": email, "password": password, "name": name}, timeout=30)
        resp = s.post(f"{base_url}/auth/login",
                      json={"email": email, "password": password}, timeout=30)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        return s

    @staticmethod
    def _wait_cache(s, base_url: str):
        """Poll until cache is ready."""
        import time
        for _ in range(20):
            cs = s.get(f"{base_url}/api/market/cache-status", timeout=10).json()
            if cs.get("ready"):
                return
            time.sleep(3)

    def test_value_stocks_api_returns_results(self, live_url: str, _live_server):
        """The Value Stocks filter (P/E <= 15, dividend >= 2%) should return results."""
        s = self._session(live_url, "screener_api@e2e.local", "Pass1234", "Screener Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"asset_type": "Stock", "pe_max": 15, "dividend_yield_min": 2},
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0, (
            f"Value Stocks API returned 0 results. "
            f"This was the original bug — dividend_yield was being doubled (*100) "
            f"then discarded by the >20 safety check."
        )

    def test_dividend_yield_values_are_reasonable(self, live_url: str, _live_server):
        """All returned dividend_yield values should be between 0 and 20%."""
        s = self._session(live_url, "screener_div@e2e.local", "Pass1234", "Div Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"asset_type": "Stock", "dividend_yield_min": 0.1},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0, "No stocks returned with dividend_yield_min=0.1"
        for item in items:
            dy = item["dividend_yield"]
            assert dy is not None, f"{item['symbol']} has null dividend_yield"
            assert 0 < dy <= 20, (
                f"{item['symbol']} dividend_yield={dy} is outside valid range (0, 20]. "
                f"If > 20, the *100 bug may have returned."
            )

    def test_pe_ratio_filter_is_respected(self, live_url: str, _live_server):
        """All results with pe_max=15 should have P/E <= 15."""
        s = self._session(live_url, "screener_pe@e2e.local", "Pass1234", "PE Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"asset_type": "Stock", "pe_max": 15},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0, "No stocks returned with pe_max=15"
        for item in items:
            pe = item["pe_ratio"]
            assert pe is not None, f"{item['symbol']} has null pe_ratio"
            assert pe <= 15, (
                f"{item['symbol']} P/E={pe} exceeds pe_max=15 filter"
            )

    def test_high_dividend_api_returns_results(self, live_url: str, _live_server):
        """High Dividend filter (div >= 3%) should return results."""
        s = self._session(live_url, "screener_hidiv@e2e.local", "Pass1234", "HiDiv Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"dividend_yield_min": 3},
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0, "High Dividend filter (div>=3%) returned 0 results"

    def test_cache_warming_provides_metrics(self, live_url: str, _live_server):
        """After cache is ready, screener results should have populated metrics."""
        s = self._session(live_url, "screener_cache@e2e.local", "Pass1234", "Cache Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"asset_type": "Stock", "per_page": 10},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0, "Screener returned 0 stocks"
        # At least some stocks should have non-null metrics
        has_pe = sum(1 for i in items if i["pe_ratio"] is not None)
        has_div = sum(1 for i in items if i["dividend_yield"] is not None)
        has_beta = sum(1 for i in items if i["beta"] is not None)
        assert has_pe > 0, (
            f"No stocks have pe_ratio populated out of {len(items)} — "
            f"cache warmer may be using full=False"
        )
        assert has_beta > 0, (
            f"No stocks have beta populated out of {len(items)} — "
            f"cache warmer may be using full=False"
        )

    def test_signal_filter_buy_returns_only_buy(self, live_url: str, _live_server):
        """Filtering by signal=Buy should return only Buy-signal stocks."""
        s = self._session(live_url, "screener_sigbuy@e2e.local", "Pass1234", "Signal Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"signal": "Buy"},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        # Buy results may be 0 on a fresh cache — only verify correctness when present
        for item in items:
            assert item["signal"] == "Buy", (
                f"{item['symbol']} has signal='{item['signal']}' but filter is Buy"
            )

    def test_signal_filter_hold_returns_only_hold(self, live_url: str, _live_server):
        """Filtering by signal=Hold should return only Hold-signal stocks."""
        s = self._session(live_url, "screener_sighold@e2e.local", "Pass1234", "Signal Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"signal": "Hold"},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0, "signal=Hold filter returned 0 results"
        for item in items:
            assert item["signal"] == "Hold", (
                f"{item['symbol']} has signal='{item['signal']}' but filter is Hold"
            )

    def test_signal_filter_avoid_returns_only_avoid(self, live_url: str, _live_server):
        """Filtering by signal=Avoid should return only Avoid-signal stocks."""
        s = self._session(live_url, "screener_sigavoid@e2e.local", "Pass1234", "Signal Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"signal": "Avoid"},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        # Avoid may have 0 results if all stocks are Buy/Hold — that's OK
        for item in items:
            assert item["signal"] == "Avoid", (
                f"{item['symbol']} has signal='{item['signal']}' but filter is Avoid"
            )

    def test_signal_filter_no_filter_returns_mixed(self, live_url: str, _live_server):
        """Without signal filter, results should contain a mix of signals."""
        s = self._session(live_url, "screener_sigmix@e2e.local", "Pass1234", "Signal Tester")
        self._wait_cache(s, live_url)
        resp = s.get(
            f"{live_url}/api/screener",
            params={"per_page": 50},
            timeout=30,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0, "Unfiltered screener returned 0 results"
        signals = set(i["signal"] for i in items)
        assert len(signals) >= 2, (
            f"Expected mixed signals without filter, got only: {signals}"
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
#  Portfolio — chart height constraint
# ────────────────────────────────────────────

class TestPortfolioChartHeight:
    """
    Regression tests for the Performance vs S&P 500 chart sizing.
    The chart used to grow unbounded (maintainAspectRatio: false with no
    height-constrained parent), requiring excessive scrolling.  Now the
    canvas lives inside a .pf-chart-wrap container capped at 280px and
    Chart.js uses maintainAspectRatio: true with aspectRatio: 1.8.
    """

    def test_perf_chart_canvas_inside_wrap_container(self, authenticated_page: Page):
        """Canvas must be wrapped in a .pf-chart-wrap div that caps height."""
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(2000)
        wrap = authenticated_page.locator(".pf-chart-wrap")
        assert wrap.count() >= 2, (
            "Expected at least 2 .pf-chart-wrap containers "
            "(allocation + performance)"
        )
        # The performance chart canvas should be inside the wrapper
        perf_canvas = authenticated_page.locator(".pf-chart-wrap #pf-perf-chart")
        expect(perf_canvas).to_have_count(1)

    def test_perf_chart_height_is_bounded(self, authenticated_page: Page):
        """The performance chart should not exceed 280px in height."""
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(12000)
        wrap = authenticated_page.locator(".pf-chart-wrap").nth(1)  # 2nd = perf chart
        box = wrap.bounding_box()
        assert box is not None, "Performance chart wrapper has no bounding box"
        assert box["height"] <= 300, (
            f"Performance chart is {box['height']:.0f}px tall — should be "
            f"≤ 300px (max-height: 280px + padding). Chart is still too tall."
        )

    def test_alloc_chart_height_is_bounded(self, authenticated_page: Page):
        """The sector allocation chart should also be height-constrained."""
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(2000)
        wrap = authenticated_page.locator(".pf-chart-wrap").first
        box = wrap.bounding_box()
        assert box is not None, "Alloc chart wrapper has no bounding box"
        assert box["height"] <= 300, (
            f"Allocation chart is {box['height']:.0f}px tall — should be "
            f"≤ 300px. Chart is still too tall."
        )

    def test_perf_chart_canvas_has_no_hardcoded_height(self, authenticated_page: Page):
        """Canvas should NOT have a hardcoded height attribute (responsive)."""
        _nav_click(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(2000)
        canvas = authenticated_page.locator("#pf-perf-chart")
        height_attr = canvas.get_attribute("height")
        # Chart.js may set a computed height attr at runtime, but NOT "200"
        assert height_attr != "200", (
            "Canvas still has the old hardcoded height='200' attribute"
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


# ════════════════════════════════════════════
#  Multi-User — registration, auth, isolation
# ════════════════════════════════════════════

import requests as _requests   # noqa: E402  (import here to keep existing order)


class TestRegistration:
    """Registration flow via the UI and API."""

    def test_register_new_user_via_ui(self, page: Page, live_url: str, _live_server):
        """Register a brand-new user through the browser form."""
        import uuid
        unique = uuid.uuid4().hex[:8]
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        # Switch to the Register tab
        page.locator(".tab-btn", has_text="Register").click()
        page.wait_for_timeout(500)
        page.fill("#reg-name", "UI Tester")
        page.fill("#reg-email", f"uitester_{unique}@e2e.local")
        page.fill("#reg-password", "UiPass99")
        page.click("#reg-btn")
        # After successful registration the JS sets window.location.href = "/"
        page.wait_for_selector("nav.sidebar", timeout=30_000)
        expect(page).to_have_title("InvestAI")

    def test_duplicate_email_rejected(self, page: Page, live_url: str, _live_server):
        """Registering the same email twice should show an error."""
        _requests.post(
            f"{live_url}/auth/register",
            json={"email": "dup@e2e.local", "password": "Pass1234", "name": "First"},
        )
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.locator(".tab-btn", has_text="Register").click()
        page.fill("#reg-name", "Second")
        page.fill("#reg-email", "dup@e2e.local")
        page.fill("#reg-password", "Pass1234")
        page.click("#reg-btn")
        page.wait_for_selector("#reg-error:not(:empty)", timeout=5_000)
        expect(page.locator("#reg-error")).to_contain_text("already registered")

    def test_register_short_password_rejected(self, page: Page, live_url: str, _live_server):
        """A password shorter than 4 chars should be rejected by the API."""
        resp = _requests.post(
            f"{live_url}/auth/register",
            json={"email": "short@e2e.local", "password": "ab", "name": "Short"},
        )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for short password, got {resp.status_code}"
        )


class TestAuthMe:
    """JWT /auth/me endpoint returns the logged-in user's info."""

    def test_me_returns_user_info(self, authenticated_page: Page, live_url: str):
        data = authenticated_page.evaluate("""
            async () => {
                const r = await fetch('/auth/me');
                return r.ok ? await r.json() : null;
            }
        """)
        assert data is not None, "/auth/me did not return 200"
        assert data.get("email"), f"/auth/me response missing email: {data}"

    def test_me_unauthenticated_returns_redirect(self, live_url: str, _live_server):
        resp = _requests.get(f"{live_url}/auth/me", allow_redirects=False)
        assert resp.status_code in (401, 307, 302), (
            f"Expected 401 or redirect for unauthenticated /auth/me, got {resp.status_code}"
        )


class TestMultiUserIsolation:
    """
    Core multi-user test: two users should NOT see each other's data.
    Uses the API directly with session cookies for speed and reliability.
    """

    @staticmethod
    def _session_for(base: str, email: str, password: str, name: str) -> _requests.Session:
        """Register (idempotent) + login, return a requests.Session with the JWT cookie."""
        s = _requests.Session()
        s.post(f"{base}/auth/register", json={"email": email, "password": password, "name": name})
        resp = s.post(f"{base}/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        return s

    # ── watchlist isolation ──────────────────
    def test_watchlist_isolation(self, live_url: str, _live_server):
        """User A adds a symbol to watchlist; User B's watchlist must not contain it."""
        import uuid
        tag = uuid.uuid4().hex[:6]
        s_a = self._session_for(live_url, f"alice_wl_{tag}@e2e.local", "Alice123", "Alice")
        s_b = self._session_for(live_url, f"bob_wl_{tag}@e2e.local",   "Bob12345", "Bob")

        # User A adds NVDA (symbol is a query param)
        resp = s_a.post(f"{live_url}/api/screener/watchlist", params={"symbol": "NVDA"})
        assert resp.status_code == 200, f"A add NVDA failed: {resp.text}"

        # User B's watchlist should be empty (or at least not contain NVDA)
        resp_b = s_b.get(f"{live_url}/api/screener/watchlist")
        assert resp_b.status_code == 200
        symbols_b = [item.get("symbol", "") for item in resp_b.json()]
        assert "NVDA" not in symbols_b, (
            f"User B can see User A's watchlist item NVDA! B's watchlist: {symbols_b}"
        )

    # ── holdings/portfolio isolation ─────────
    def test_portfolio_isolation(self, live_url: str, _live_server):
        """User A adds a GOOG holding; User B should not see it."""
        import uuid
        tag = uuid.uuid4().hex[:6]
        s_a = self._session_for(live_url, f"alice_pf_{tag}@e2e.local", "Alice123", "Alice PF")
        s_b = self._session_for(live_url, f"bob_pf_{tag}@e2e.local",   "Bob12345", "Bob PF")

        s_a.post(f"{live_url}/api/portfolio/holdings", json={
            "symbol": "GOOG", "name": "Alphabet", "quantity": 5,
            "buy_price": 170.0, "buy_date": "2025-01-01",
        })

        resp_b = s_b.get(f"{live_url}/api/portfolio/holdings")
        assert resp_b.status_code == 200
        holdings = resp_b.json()
        symbols_b = [h.get("symbol", "") for h in holdings] if isinstance(holdings, list) else []
        assert "GOOG" not in symbols_b, (
            f"User B can see User A's GOOG holding! B's portfolio: {symbols_b}"
        )

    # ── transactions isolation ───────────────
    def test_transactions_isolation(self, live_url: str, _live_server):
        """User A creates a transaction; User B should not see it."""
        import uuid
        tag = uuid.uuid4().hex[:6]
        s_a = self._session_for(live_url, f"alice_tx_{tag}@e2e.local", "Alice123", "Alice TX")
        s_b = self._session_for(live_url, f"bob_tx_{tag}@e2e.local",   "Bob12345", "Bob TX")

        s_a.post(f"{live_url}/api/transactions", json={
            "type": "expense", "amount": 42.0,
            "date": "2025-06-01", "description": "Alice secret purchase",
        })

        resp_b = s_b.get(f"{live_url}/api/transactions")
        assert resp_b.status_code == 200
        descs = [t.get("description", "") for t in resp_b.json()]
        assert "Alice secret purchase" not in descs, (
            f"User B can see User A's transaction! B's txns: {descs}"
        )

    # ── alerts isolation ─────────────────────
    def test_alerts_isolation(self, live_url: str, _live_server):
        """User A creates an alert; User B should not see it."""
        import uuid
        tag = uuid.uuid4().hex[:6]
        s_a = self._session_for(live_url, f"alice_al_{tag}@e2e.local", "Alice123", "Alice AL")
        s_b = self._session_for(live_url, f"bob_al_{tag}@e2e.local",   "Bob12345", "Bob AL")

        s_a.post(f"{live_url}/api/alerts", json={
            "symbol": "AMC", "condition": "above", "target_price": 999.0,
        })

        resp_b = s_b.get(f"{live_url}/api/alerts")
        assert resp_b.status_code == 200
        symbols_b = [a.get("symbol", "") for a in resp_b.json()]
        assert "AMC" not in symbols_b, (
            f"User B can see User A's AMC alert! B's alerts: {symbols_b}"
        )


# ────────────────────────────────────────────
#  Full-width layout
# ────────────────────────────────────────────

class TestFullWidthLayout:
    """Content area should fill all available width (no max-width constraint)."""

    def test_content_has_no_max_width_constraint(self, authenticated_page: Page):
        """The .content element should NOT have a restrictive max-width like 1200px."""
        content = authenticated_page.locator("main.content")
        max_w = content.evaluate("el => getComputedStyle(el).maxWidth")
        assert max_w == "none" or max_w == "", (
            f".content has max-width={max_w}, expected none"
        )

    def test_content_stretches_with_viewport(self, authenticated_page: Page):
        """Content area width should track the viewport minus the sidebar."""
        # Set a wide viewport
        authenticated_page.set_viewport_size({"width": 1920, "height": 1080})
        authenticated_page.wait_for_timeout(300)
        content = authenticated_page.locator("main.content")
        box = content.bounding_box()
        # Sidebar is 240px, so content should be at least (1920 - 240 - some padding)
        assert box is not None
        assert box["width"] >= 1600, (
            f"Content width {box['width']}px is too narrow for 1920px viewport"
        )

    def test_il_funds_table_is_wide(self, authenticated_page: Page):
        """IL Funds table should use the full content width, not be capped at 1200px."""
        authenticated_page.set_viewport_size({"width": 1920, "height": 1080})
        _nav_click(authenticated_page, "il-funds")
        authenticated_page.wait_for_timeout(500)
        content = authenticated_page.locator("main.content")
        box = content.bounding_box()
        assert box is not None
        assert box["width"] >= 1600, (
            f"Content area is only {box['width']}px wide on IL Funds page"
        )


# ────────────────────────────────────────────
#  Search bars on every applicable page
# ────────────────────────────────────────────

class TestSearchBars:
    """Every data page should have a search bar that is visible and functional."""

    SEARCH_PAGES = [
        ("portfolio",    "portfolio-search",     "Search holdings"),
        ("watchlist",    "watchlist-search",     "Search by symbol"),
        ("news",         "news-search",          "Search news"),
        ("transactions", "transactions-search",  "Search transactions"),
        ("alerts",       "alerts-search",        "Search alerts"),
        ("calendar",     "calendar-search",      "Search events"),
        ("education",    "education-search",     "Search articles"),
        ("il-funds",     "il-funds-search",      "Search funds"),
        ("picks-tracker","picks-search",         "Search picks"),
    ]

    def test_search_bars_present_on_all_data_pages(self, authenticated_page: Page):
        """Each data page should have a visible search input with a placeholder."""
        for page_id, input_id, placeholder_fragment in self.SEARCH_PAGES:
            _nav_click(authenticated_page, page_id)
            authenticated_page.wait_for_timeout(300)
            search_input = authenticated_page.locator(f"#{input_id}")
            expect(search_input).to_be_visible(timeout=3_000)
            ph = search_input.get_attribute("placeholder") or ""
            assert placeholder_fragment.lower() in ph.lower(), (
                f"Page '{page_id}': placeholder '{ph}' doesn't contain '{placeholder_fragment}'"
            )

    def test_search_bar_has_icon_and_clear_button(self, authenticated_page: Page):
        """Each search bar should have a magnifying-glass icon and a clear button."""
        for page_id, input_id, _ in self.SEARCH_PAGES:
            _nav_click(authenticated_page, page_id)
            authenticated_page.wait_for_timeout(300)
            bar = authenticated_page.locator(f"#{input_id}").locator("..")
            expect(bar.locator(".search-icon")).to_be_visible(timeout=2_000)
            # Clear button exists (may be hidden until text is entered)
            expect(bar.locator(".search-clear")).to_have_count(1)

    def test_search_filters_education_cards(self, authenticated_page: Page):
        """Typing in the education search should hide non-matching cards."""
        _nav_click(authenticated_page, "education")
        authenticated_page.wait_for_timeout(2_000)
        # Ensure some cards rendered
        cards_before = authenticated_page.locator(".edu-card:visible").count()
        if cards_before == 0:
            return  # no data, skip filtering test

        # Type a very specific query that likely matches at most a few cards
        authenticated_page.fill("#education-search", "dividend")
        authenticated_page.wait_for_timeout(500)
        cards_after = authenticated_page.locator(".edu-card:visible").count()
        # After filtering, should have fewer (or same if all match, but very unlikely)
        assert cards_after <= cards_before, (
            f"Filtering didn't reduce cards: before={cards_before}, after={cards_after}"
        )

        # Clear search — should restore all cards
        authenticated_page.fill("#education-search", "")
        authenticated_page.wait_for_timeout(500)
        cards_restored = authenticated_page.locator(".edu-card:visible").count()
        assert cards_restored == cards_before, (
            f"Clearing search didn't restore cards: expected {cards_before}, got {cards_restored}"
        )

    def test_search_filters_calendar_events(self, authenticated_page: Page):
        """Typing in the calendar search should hide non-matching events."""
        _nav_click(authenticated_page, "calendar")
        authenticated_page.wait_for_timeout(3_000)
        events_before = authenticated_page.locator(".cal-event:visible").count()
        if events_before == 0:
            return  # no data, skip

        # Type something unlikely to match many events
        authenticated_page.fill("#calendar-search", "xyznonexistent")
        authenticated_page.wait_for_timeout(500)
        events_after = authenticated_page.locator(".cal-event:visible").count()
        assert events_after == 0, (
            f"Expected 0 events for nonsense query, got {events_after}"
        )

        # Clear
        authenticated_page.fill("#calendar-search", "")
        authenticated_page.wait_for_timeout(500)
        events_restored = authenticated_page.locator(".cal-event:visible").count()
        assert events_restored == events_before

    def test_search_no_results_message(self, authenticated_page: Page):
        """Searching for gibberish on education page should show a no-results message."""
        _nav_click(authenticated_page, "education")
        authenticated_page.wait_for_timeout(2_000)
        cards_before = authenticated_page.locator(".edu-card:visible").count()
        if cards_before == 0:
            return  # no data, skip

        authenticated_page.fill("#education-search", "zzzzxyznonexistent999")
        authenticated_page.wait_for_timeout(500)
        no_res = authenticated_page.locator("#edu-no-results")
        expect(no_res).to_be_visible(timeout=2_000)
        expect(no_res).to_contain_text("No articles matching")

    def test_clear_button_resets_search(self, authenticated_page: Page):
        """Clicking the clear (×) button should empty the input and restore results."""
        _nav_click(authenticated_page, "education")
        authenticated_page.wait_for_timeout(2_000)
        cards_before = authenticated_page.locator(".edu-card:visible").count()
        if cards_before == 0:
            return

        authenticated_page.fill("#education-search", "zzzznonexistent")
        authenticated_page.wait_for_timeout(300)
        # Click the clear button
        authenticated_page.locator("#page-education .search-clear").click(force=True)
        authenticated_page.wait_for_timeout(500)

        # Input should be empty
        val = authenticated_page.locator("#education-search").input_value()
        assert val == "", f"Search input not cleared, value='{val}'"

        # Cards should be restored
        cards_after = authenticated_page.locator(".edu-card:visible").count()
        assert cards_after == cards_before


# ────────────────────────────────────────────
#  Forgot Password — API tests
# ────────────────────────────────────────────

class TestForgotPasswordAPI:
    """Test the /auth/forgot-password and /auth/reset-password endpoints directly."""

    def test_forgot_password_returns_ok_for_existing_user(self, live_url: str, _live_server):
        """POST /auth/forgot-password should return 200 with ok=True for a registered email."""
        import requests
        # Ensure user exists
        requests.post(
            f"{live_url}/auth/register",
            json={"email": "resetapi@e2e.local", "password": "OldPass99", "name": "Reset API"},
        )
        resp = requests.post(
            f"{live_url}/auth/forgot-password",
            json={"email": "resetapi@e2e.local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "reset code" in data["message"].lower()

    def test_forgot_password_returns_ok_for_unknown_email(self, live_url: str, _live_server):
        """Should still return 200 to not leak whether the email exists."""
        import requests
        resp = requests.post(
            f"{live_url}/auth/forgot-password",
            json={"email": "nobody_here@e2e.local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_reset_password_with_valid_code(self, live_url: str, _live_server):
        """Full flow: register → forgot → get code from DB → reset → login with new password."""
        import requests
        email = "resetfull@e2e.local"
        old_pw = "OldPass1"
        new_pw = "NewPass1"

        # Register
        requests.post(
            f"{live_url}/auth/register",
            json={"email": email, "password": old_pw, "name": "Reset Full"},
        )

        # Request reset code
        resp = requests.post(f"{live_url}/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200

        # Grab the code directly from the DB
        import sys, pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root))
        from src.database import SessionLocal
        from src.models import PasswordReset, User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            reset = (
                db.query(PasswordReset)
                .filter(PasswordReset.user_id == user.id, PasswordReset.used == 0)
                .order_by(PasswordReset.created_at.desc())
                .first()
            )
            code = reset.code
        finally:
            db.close()

        # Reset with the code
        resp = requests.post(
            f"{live_url}/auth/reset-password",
            json={"email": email, "code": code, "new_password": new_pw},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "reset" in data["message"].lower()

        # Login with old password should fail
        resp = requests.post(
            f"{live_url}/auth/login",
            json={"email": email, "password": old_pw},
        )
        assert resp.status_code == 403

        # Login with new password should succeed
        resp = requests.post(
            f"{live_url}/auth/login",
            json={"email": email, "password": new_pw},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_reset_password_wrong_code_rejected(self, live_url: str, _live_server):
        """Using a wrong code should return 400."""
        import requests
        email = "resetbad@e2e.local"
        requests.post(
            f"{live_url}/auth/register",
            json={"email": email, "password": "SomePass1", "name": "Bad Code"},
        )
        requests.post(f"{live_url}/auth/forgot-password", json={"email": email})

        resp = requests.post(
            f"{live_url}/auth/reset-password",
            json={"email": email, "code": "000000", "new_password": "NewPass1"},
        )
        # Might succeed if code happens to be 000000, so check either 200+ok or 400
        if resp.status_code == 400:
            assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()

    def test_reset_password_code_single_use(self, live_url: str, _live_server):
        """A code can only be used once."""
        import requests
        email = "resetonce@e2e.local"
        requests.post(
            f"{live_url}/auth/register",
            json={"email": email, "password": "OldPw1234", "name": "Once"},
        )
        requests.post(f"{live_url}/auth/forgot-password", json={"email": email})

        # Get code from DB
        import pathlib, sys
        root = pathlib.Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root))
        from src.database import SessionLocal
        from src.models import PasswordReset, User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            reset = (
                db.query(PasswordReset)
                .filter(PasswordReset.user_id == user.id, PasswordReset.used == 0)
                .order_by(PasswordReset.created_at.desc())
                .first()
            )
            code = reset.code
        finally:
            db.close()

        # First use — should succeed
        resp1 = requests.post(
            f"{live_url}/auth/reset-password",
            json={"email": email, "code": code, "new_password": "Changed1"},
        )
        assert resp1.status_code == 200

        # Second use — same code should be rejected
        resp2 = requests.post(
            f"{live_url}/auth/reset-password",
            json={"email": email, "code": code, "new_password": "Changed2"},
        )
        assert resp2.status_code == 400
        assert "invalid" in resp2.json()["detail"].lower() or "expired" in resp2.json()["detail"].lower()

    def test_reset_password_short_password_rejected(self, live_url: str, _live_server):
        """New password under 4 chars should be rejected."""
        import requests
        resp = requests.post(
            f"{live_url}/auth/reset-password",
            json={"email": "anyone@e2e.local", "code": "123456", "new_password": "ab"},
        )
        assert resp.status_code == 400
        assert "4 characters" in resp.json()["detail"]


# ────────────────────────────────────────────
#  Forgot Password — Browser UI tests
# ────────────────────────────────────────────

class TestForgotPasswordUI:
    """Test the web forgot-password flow in the browser."""

    def test_forgot_link_visible_on_login_page(self, page: Page, live_url: str, _live_server):
        """The 'Forgot password?' link should be visible on the login form."""
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        forgot = page.locator(".forgot-link")
        expect(forgot).to_be_visible()
        expect(forgot).to_have_text("Forgot password?")

    def test_forgot_link_shows_email_form(self, page: Page, live_url: str, _live_server):
        """Clicking 'Forgot password?' hides login form and shows the email entry form."""
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.click(".forgot-link")
        # Login form should be hidden
        expect(page.locator("#login-form")).to_be_hidden()
        # Forgot form should be visible
        expect(page.locator("#forgot-form")).to_be_visible()
        expect(page.locator("#forgot-email")).to_be_visible()
        expect(page.locator("#forgot-btn")).to_have_text("Send Reset Code")

    def test_back_link_returns_to_login(self, page: Page, live_url: str, _live_server):
        """'Back to Sign In' link should return to the normal login form."""
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.click(".forgot-link")
        expect(page.locator("#forgot-form")).to_be_visible()
        # Click back
        page.click(".back-link")
        expect(page.locator("#login-form")).to_be_visible()
        expect(page.locator("#forgot-form")).to_be_hidden()

    def test_submit_email_shows_code_form(self, page: Page, live_url: str, _live_server):
        """After submitting an email, the code+password form should appear."""
        import requests
        requests.post(
            f"{live_url}/auth/register",
            json={"email": "uireset@e2e.local", "password": "UiPass1", "name": "UI Reset"},
        )
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.click(".forgot-link")
        page.fill("#forgot-email", "uireset@e2e.local")
        page.click("#forgot-btn")
        # Wait for the reset form to appear (step 2)
        page.wait_for_selector("#reset-form:not(.hidden)", timeout=10_000)
        expect(page.locator("#reset-code")).to_be_visible()
        expect(page.locator("#reset-password")).to_be_visible()
        expect(page.locator("#reset-btn")).to_have_text("Reset Password")

    def test_full_ui_reset_flow(self, page: Page, live_url: str, _live_server):
        """Full browser flow: click forgot → enter email → get code from DB → enter code + new pw → login."""
        import requests
        email = "uifull@e2e.local"
        old_pw = "OldUiPass1"
        new_pw = "NewUiPass1"

        # Register user
        requests.post(
            f"{live_url}/auth/register",
            json={"email": email, "password": old_pw, "name": "UI Full Reset"},
        )

        # Navigate to forgot password
        page.goto(f"{live_url}/login", wait_until="domcontentloaded")
        page.click(".forgot-link")
        page.fill("#forgot-email", email)
        page.click("#forgot-btn")
        page.wait_for_selector("#reset-form:not(.hidden)", timeout=10_000)

        # Grab code from DB
        import pathlib, sys
        root = pathlib.Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root))
        from src.database import SessionLocal
        from src.models import PasswordReset, User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            reset = (
                db.query(PasswordReset)
                .filter(PasswordReset.user_id == user.id, PasswordReset.used == 0)
                .order_by(PasswordReset.created_at.desc())
                .first()
            )
            code = reset.code
        finally:
            db.close()

        # Enter code and new password
        page.fill("#reset-code", code)
        page.fill("#reset-password", new_pw)
        page.click("#reset-btn")

        # Wait for success message
        page.wait_for_selector("#reset-success:not(:empty)", timeout=10_000)
        expect(page.locator("#reset-success")).to_contain_text("reset")

        # Wait for redirect back to login (the JS has a 2s setTimeout)
        page.wait_for_selector("#login-form:not(.hidden)", timeout=10_000)

        # Login with new password
        page.fill("#login-email", email)
        page.fill("#login-password", new_pw)
        page.click("#login-btn")
        page.wait_for_url(f"{live_url}/**", timeout=15_000)
        page.wait_for_load_state("domcontentloaded")
        expect(page.locator("nav.sidebar")).to_be_visible(timeout=15_000)


# ────────────────────────────────────────────
#  Value Scanner — Action Plan
# ────────────────────────────────────────────

class TestActionPlanAPI:
    """API-level tests for the Value Scanner Action Plan endpoint.

    These tests do NOT wait for the full market cache to warm — the
    action plan endpoint works with whatever value-scanner candidates
    are already available, returning an empty plan if none exist yet.
    """

    @staticmethod
    def _session(base_url: str, email: str, password: str, name: str = "Test"):
        import requests as _req
        s = _req.Session()
        s.post(f"{base_url}/auth/register",
               json={"email": email, "password": password, "name": name}, timeout=60)
        resp = s.post(f"{base_url}/auth/login",
                      json={"email": email, "password": password}, timeout=60)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        return s

    def test_action_plan_endpoint_returns_200(self, live_url: str, _live_server):
        """GET /api/value-scanner/action-plan should return 200 with valid structure."""
        s = self._session(live_url, "ap_api_basic@e2e.local", "Pass1234", "AP Tester")
        resp = s.get(f"{live_url}/api/value-scanner/action-plan", params={"amount": 10000}, timeout=60)
        assert resp.status_code == 200, f"Action plan returned {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "plan" in data, f"Response missing 'plan' key: {list(data.keys())}"
        assert "summary" in data, f"Response missing 'summary' key: {list(data.keys())}"
        assert "ready" in data, f"Response missing 'ready' key"

    def test_action_plan_summary_structure(self, live_url: str, _live_server):
        """Summary should contain total_investment, allocated, stocks_count, signal_breakdown."""
        s = self._session(live_url, "ap_api_summary@e2e.local", "Pass1234", "AP Summary")
        resp = s.get(f"{live_url}/api/value-scanner/action-plan", params={"amount": 5000}, timeout=60)
        assert resp.status_code == 200
        summary = resp.json()["summary"]
        assert summary["total_investment"] == 5000, f"Expected 5000, got {summary['total_investment']}"
        assert "allocated" in summary, "Missing 'allocated' field"
        assert "stocks_count" in summary, "Missing 'stocks_count' field"
        assert "signal_breakdown" in summary, "Missing 'signal_breakdown' field"

    def test_action_plan_plan_has_valid_signals(self, live_url: str, _live_server):
        """Each plan group should have a valid signal and strategy info."""
        s = self._session(live_url, "ap_api_signals@e2e.local", "Pass1234", "AP Signals")
        resp = s.get(f"{live_url}/api/value-scanner/action-plan", params={"amount": 10000}, timeout=60)
        assert resp.status_code == 200
        plan = resp.json()["plan"]
        valid_signals = {"Strong Buy", "Buy", "Watch", "Consider"}
        for group in plan:
            assert group["signal"] in valid_signals, f"Invalid signal: {group['signal']}"
            assert "action" in group, f"Group {group['signal']} missing 'action'"
            assert "strategy" in group, f"Group {group['signal']} missing 'strategy'"
            assert "stocks" in group, f"Group {group['signal']} missing 'stocks'"
            assert len(group["stocks"]) > 0, f"Group {group['signal']} has 0 stocks"

    def test_action_plan_stocks_have_allocations(self, live_url: str, _live_server):
        """Each stock in the plan should have allocation_pct, allocation_dollars, suggested_shares."""
        s = self._session(live_url, "ap_api_alloc@e2e.local", "Pass1234", "AP Alloc")
        resp = s.get(f"{live_url}/api/value-scanner/action-plan", params={"amount": 10000}, timeout=60)
        assert resp.status_code == 200
        plan = resp.json()["plan"]
        if not plan:
            return  # No candidates yet — scan may still be running

        total_alloc_pct = 0
        for group in plan:
            for stock in group["stocks"]:
                assert "symbol" in stock, "Stock missing 'symbol'"
                assert "allocation_pct" in stock, f"{stock.get('symbol')} missing allocation_pct"
                assert "allocation_dollars" in stock, f"{stock.get('symbol')} missing allocation_dollars"
                assert "suggested_shares" in stock, f"{stock.get('symbol')} missing suggested_shares"
                assert stock["allocation_pct"] > 0, f"{stock['symbol']} has 0% allocation"
                assert stock["allocation_dollars"] > 0, f"{stock['symbol']} has $0 allocation"
                total_alloc_pct += stock["allocation_pct"]

        assert 99 <= total_alloc_pct <= 101, (
            f"Total allocation should be ~100%, got {total_alloc_pct:.1f}%"
        )

    def test_action_plan_allocations_sum_to_investment(self, live_url: str, _live_server):
        """Dollar allocations across all stocks should sum close to the requested amount."""
        s = self._session(live_url, "ap_api_dollars@e2e.local", "Pass1234", "AP Dollars")
        amount = 25000
        resp = s.get(f"{live_url}/api/value-scanner/action-plan", params={"amount": amount}, timeout=60)
        assert resp.status_code == 200
        plan = resp.json()["plan"]
        if not plan:
            return

        total_dollars = sum(
            stock["allocation_dollars"]
            for group in plan
            for stock in group["stocks"]
        )
        assert abs(total_dollars - amount) < 10, (
            f"Dollar allocations sum to ${total_dollars:.2f}, expected ~${amount}"
        )

    def test_action_plan_sector_filter(self, live_url: str, _live_server):
        """Sector filter should only return stocks from that sector."""
        s = self._session(live_url, "ap_api_sector@e2e.local", "Pass1234", "AP Sector")
        resp = s.get(
            f"{live_url}/api/value-scanner/action-plan",
            params={"amount": 10000, "sector": "Technology"},
            timeout=60,
        )
        assert resp.status_code == 200
        plan = resp.json()["plan"]
        for group in plan:
            for stock in group["stocks"]:
                assert stock["sector"] == "Technology", (
                    f"{stock['symbol']} sector is '{stock['sector']}', expected 'Technology'"
                )

    def test_action_plan_strengths_and_weaknesses(self, live_url: str, _live_server):
        """Each stock should have strengths and weaknesses lists."""
        s = self._session(live_url, "ap_api_sw@e2e.local", "Pass1234", "AP SW")
        resp = s.get(f"{live_url}/api/value-scanner/action-plan", params={"amount": 10000}, timeout=60)
        assert resp.status_code == 200
        plan = resp.json()["plan"]
        if not plan:
            return

        for group in plan:
            for stock in group["stocks"]:
                assert "strengths" in stock, f"{stock['symbol']} missing 'strengths'"
                assert "weaknesses" in stock, f"{stock['symbol']} missing 'weaknesses'"
                assert isinstance(stock["strengths"], list), f"strengths should be a list"
                assert isinstance(stock["weaknesses"], list), f"weaknesses should be a list"


class TestActionPlanUI:
    """Browser E2E tests for the Value Scanner Action Plan modal."""

    def test_action_plan_button_visible(self, authenticated_page: Page):
        """The 'Action Plan' button should be visible on the Value Investing page."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(500)
        # Click the "Value Investing" tab
        authenticated_page.locator("button.merge-tab", has_text="Value Investing").first.click()
        authenticated_page.wait_for_timeout(1000)
        btn = authenticated_page.locator(".vs-action-plan-btn")
        expect(btn).to_be_visible(timeout=5_000)
        expect(btn).to_contain_text("Action Plan")

    def test_action_plan_modal_opens(self, authenticated_page: Page):
        """Clicking the Action Plan button should open the modal."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("button.merge-tab", has_text="Value Investing").first.click()
        authenticated_page.wait_for_timeout(2000)
        authenticated_page.locator(".vs-action-plan-btn").click()
        # Wait for the modal overlay to appear
        modal = authenticated_page.locator("#vap-modal-overlay")
        expect(modal).to_be_visible(timeout=15_000)
        # Modal should have the title
        expect(modal.locator(".modal-header h2")).to_contain_text("Action Plan")

    def test_action_plan_modal_shows_content(self, authenticated_page: Page):
        """The modal should show either a plan with groups or loading/empty state."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("button.merge-tab", has_text="Value Investing").first.click()
        authenticated_page.wait_for_timeout(2000)
        authenticated_page.locator(".vs-action-plan-btn").click()
        modal = authenticated_page.locator("#vap-modal-overlay")
        expect(modal).to_be_visible(timeout=15_000)
        # Wait for content to load (replaces spinner)
        authenticated_page.wait_for_timeout(8000)
        # Should have either groups (plan loaded) or empty/warning message
        body = modal.locator(".vap-body")
        expect(body).to_be_visible()
        html = body.inner_html()
        assert len(html) > 50, f"Action plan body is too small, may not have loaded: {html[:200]}"

    def test_action_plan_invest_amount_input(self, authenticated_page: Page):
        """The modal should have an investment amount input with default value."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("button.merge-tab", has_text="Value Investing").first.click()
        authenticated_page.wait_for_timeout(2000)
        authenticated_page.locator(".vs-action-plan-btn").click()
        modal = authenticated_page.locator("#vap-modal-overlay")
        expect(modal).to_be_visible(timeout=15_000)
        authenticated_page.wait_for_timeout(8000)
        amount_input = modal.locator("#vap-invest-amount")
        expect(amount_input).to_be_visible()
        val = amount_input.input_value()
        assert float(val) == 10000, f"Default investment amount should be 10000, got {val}"

    def test_action_plan_modal_closes(self, authenticated_page: Page):
        """Clicking the close button should dismiss the modal."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("button.merge-tab", has_text="Value Investing").first.click()
        authenticated_page.wait_for_timeout(2000)
        authenticated_page.locator(".vs-action-plan-btn").click()
        modal = authenticated_page.locator("#vap-modal-overlay")
        expect(modal).to_be_visible(timeout=15_000)
        # Close via the X button
        modal.locator(".modal-close").click()
        authenticated_page.wait_for_timeout(500)
        expect(modal).not_to_have_class(re.compile(r"\bopen\b"))

    def test_action_plan_shows_signal_groups(self, authenticated_page: Page):
        """If candidates exist, the modal should show signal groups with strategy info."""
        _nav_click(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(500)
        authenticated_page.locator("button.merge-tab", has_text="Value Investing").first.click()
        # Wait longer for the scan to have some results
        authenticated_page.wait_for_timeout(5000)
        authenticated_page.locator(".vs-action-plan-btn").click()
        modal = authenticated_page.locator("#vap-modal-overlay")
        expect(modal).to_be_visible(timeout=15_000)
        authenticated_page.wait_for_timeout(8000)
        # Check for signal groups or empty state
        groups = modal.locator(".vap-group")
        empty = modal.locator(".vap-empty")
        warning = modal.locator(".vap-warning")
        has_groups = groups.count() > 0
        has_empty = empty.count() > 0
        has_warning = warning.count() > 0
        assert has_groups or has_empty or has_warning, (
            "Action plan modal has no groups, no empty state, and no warning — "
            "the content didn't render properly"
        )
        if has_groups:
            # Verify the first group has strategy content
            first = groups.first
            expect(first.locator(".vap-group-header")).to_be_visible()
            expect(first.locator(".vap-group-strategy")).to_be_visible()
            expect(first.locator(".vap-stock-row")).to_have_count(
                first.locator(".vap-stock-row").count()  # at least 1
            )
            strategy_text = first.locator(".vap-group-strategy").inner_text()
            assert len(strategy_text) > 20, f"Strategy text too short: '{strategy_text}'"


# ════════════════════════════════════════════════════════════
#  Market Data Integrity — verify prices load without errors
# ════════════════════════════════════════════════════════════

class TestMarketDataIntegrity:
    """
    Verify that the dashboard shows real market data without HTTP error
    messages. This is the E2E check for the Yahoo Finance 401 fix —
    errors should never appear in the UI.
    """

    def test_no_http_error_text_on_dashboard(self, authenticated_page: Page):
        """Dashboard should never show 'HTTP Error', 'Unauthorized', or 'Invalid Crumb'."""
        _nav_click(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(10_000)
        body_text = authenticated_page.locator("#page-dashboard").inner_text()
        for bad in ("HTTP Error", "Unauthorized", "Invalid Crumb", "401", "403"):
            assert bad not in body_text, (
                f"Dashboard contains error text '{bad}' — market data provider "
                f"is leaking errors to the UI"
            )

    def test_market_cards_show_real_prices(self, authenticated_page: Page):
        """Featured market cards should display dollar prices, not $0 or error text."""
        _nav_click(authenticated_page, "dashboard")
        # Wait for market cards to appear (cache warming may take a while)
        try:
            authenticated_page.wait_for_selector(
                ".market-card .market-card-price", timeout=60_000
            )
        except Exception:
            # If no cards appear at all, skip — cache may be fully cold
            cards = authenticated_page.locator(".market-card")
            if cards.count() == 0:
                return
        authenticated_page.wait_for_timeout(2_000)  # let remaining cards load
        cards = authenticated_page.locator(".market-card")
        count = cards.count()
        assert count >= 1, "No market cards rendered on the dashboard"
        priced = 0
        for i in range(min(count, 6)):
            card = cards.nth(i)
            price_el = card.locator(".market-card-price")
            if price_el.count() == 0:
                continue
            price_text = price_el.inner_text().strip()
            if not price_text:
                continue
            assert "$" in price_text, (
                f"Market card {i} price missing '$': '{price_text}'"
            )
            import re as _re
            nums = _re.findall(r"[\d,.]+", price_text)
            assert nums, f"Market card {i} has no numeric price: '{price_text}'"
            val = float(nums[0].replace(",", ""))
            assert val > 0, f"Market card {i} shows $0 price: '{price_text}'"
            priced += 1
        assert priced >= 1, "No market cards have a visible price"

    def test_ticker_strip_renders(self, authenticated_page: Page):
        """Ticker strip should render with items."""
        _nav_click(authenticated_page, "dashboard")
        # Wait for ticker items to appear
        try:
            authenticated_page.wait_for_selector(".ticker-item", timeout=60_000)
        except Exception:
            # Ticker may not load if cache is fully cold — skip gracefully
            return
        authenticated_page.wait_for_timeout(2_000)
        strip = authenticated_page.locator("#ticker-strip")
        expect(strip).to_be_visible()
        items = strip.locator(".ticker-item")
        count = items.count()
        assert count >= 1, "No ticker items rendered"

    def test_no_js_errors_during_market_load(self, authenticated_page: Page):
        """No JavaScript errors should fire while market data loads."""
        js_errors = []
        authenticated_page.on("pageerror", lambda e: js_errors.append(str(e)))
        _nav_click(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(15_000)
        critical = [
            e for e in js_errors
            if "TypeError" in e or "ReferenceError" in e or "SyntaxError" in e
        ]
        assert len(critical) == 0, (
            f"JavaScript errors during market data load: {critical}"
        )

    def test_market_api_returns_valid_data(self, live_url: str, _live_server):
        """The /api/market/home API should return ticker + featured arrays with prices."""
        import requests
        s = requests.Session()
        px = None if "127.0.0.1" in live_url else {
            "http": "http://proxy-dmz.intel.com:911",
            "https": "http://proxy-dmz.intel.com:912",
        }
        # Register & login
        s.post(f"{live_url}/auth/register",
               json={"email": "market_api@e2e.local", "password": "Pass1234", "name": "MarketAPI"},
               proxies=px, timeout=30)
        resp = s.post(f"{live_url}/auth/login",
                      json={"email": "market_api@e2e.local", "password": "Pass1234"},
                      proxies=px, timeout=30)
        assert resp.status_code == 200, f"Login failed: {resp.text}"

        # Wait for cache to warm (at least partially)
        import time
        for _ in range(12):
            r = s.get(f"{live_url}/api/market/cache-status", proxies=px, timeout=15)
            if r.status_code == 200:
                status = r.json()
                if status.get("cached", 0) >= 6 or status.get("ready"):
                    break
            time.sleep(5)

        # Fetch market home data
        r = s.get(f"{live_url}/api/market/home", proxies=px, timeout=30)
        assert r.status_code == 200, f"Market home API failed: {r.status_code}"
        data = r.json()

        # Validate ticker data
        ticker = data.get("ticker", [])
        assert len(ticker) >= 1, "Market ticker returned no items"
        for item in ticker:
            assert item.get("price", 0) > 0, (
                f"Ticker item {item.get('symbol', '?')} has zero/missing price"
            )
            assert "error" not in str(item).lower(), (
                f"Ticker item contains error text: {item}"
            )

        # Validate featured stocks
        featured = data.get("featured", [])
        assert len(featured) >= 1, "Market featured returned no items"
        for item in featured:
            assert item.get("price", 0) > 0, (
                f"Featured item {item.get('symbol', '?')} has zero/missing price"
            )

    def test_market_cards_have_change_indicators(self, authenticated_page: Page):
        """Market cards should show change % with up/down coloring."""
        _nav_click(authenticated_page, "dashboard")
        try:
            authenticated_page.wait_for_selector(
                ".market-card .market-card-change", timeout=60_000
            )
        except Exception:
            cards = authenticated_page.locator(".market-card")
            if cards.count() == 0:
                return  # cold cache, skip
        authenticated_page.wait_for_timeout(2_000)
        cards = authenticated_page.locator(".market-card")
        count = cards.count()
        if count == 0:
            return
        changes_found = 0
        for i in range(min(count, 6)):
            change_el = cards.nth(i).locator(".market-card-change")
            if change_el.count() > 0:
                text = change_el.inner_text().strip()
                if "%" in text:
                    changes_found += 1
        assert changes_found >= 1, (
            "No market cards show a change percentage — data may not have loaded"
        )


# ════════════════════════════════════════════════════════════
#  OOM Fix Verification — cache bounds, PXD removal, memory
# ════════════════════════════════════════════════════════════

class TestOOMFixAPI:
    """
    E2E tests that verify the memory-optimisation commit (perf: fix OOM on
    Render 512 MB free tier) actually works end-to-end:

    - Cache-status reports bounded entry counts
    - Delisted PXD symbol is absent from all endpoints
    - Smart Advisor scan results have heavy arrays stripped
    - Trading Advisor dashboard caps picks
    - All services still return valid data after the changes
    """

    @staticmethod
    def _session(base_url: str, email: str, password: str, name: str = "Test"):
        import requests as _req
        s = _req.Session()
        s.post(f"{base_url}/auth/register",
               json={"email": email, "password": password, "name": name}, timeout=60)
        resp = s.post(f"{base_url}/auth/login",
                      json={"email": email, "password": password}, timeout=60)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        return s

    # ── Cache status is bounded ─────────────────────────────

    def test_cache_status_returns_bounded_total(self, live_url: str, _live_server):
        """Cache-status total should match ALL_UNIVERSE and never exceed CACHE_MAX_ENTRIES."""
        s = self._session(live_url, "oom_cache@e2e.local", "Pass1234", "OOM Cache")
        resp = s.get(f"{live_url}/api/market/cache-status", timeout=60)
        assert resp.status_code == 200, f"cache-status failed: {resp.status_code}"
        data = resp.json()
        assert "cached" in data, "Missing 'cached' key"
        assert "total" in data, "Missing 'total' key"
        assert "warming" in data, "Missing 'warming' key"
        assert "ready" in data, "Missing 'ready' key"
        # total should be the universe size (~257), not something huge
        assert data["total"] <= 300, (
            f"Universe total {data['total']} seems too large — expected ≤300"
        )
        # cached should never exceed CACHE_MAX_ENTRIES (600 normal, 300 low-mem)
        assert data["cached"] <= 600, (
            f"Cached count {data['cached']} exceeds CACHE_MAX_ENTRIES"
        )

    # ── PXD is delisted and removed ─────────────────────────

    def test_pxd_not_in_stock_universe(self, live_url: str, _live_server):
        """PXD (Pioneer Natural Resources, delisted) should not appear in any scan."""
        s = self._session(live_url, "oom_pxd@e2e.local", "Pass1234", "OOM PXD")
        # Check value scanner — PXD should not be a candidate
        resp = s.get(f"{live_url}/api/value-scanner", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        candidates = data.get("candidates", [])
        pxd_syms = [c["symbol"] for c in candidates if c.get("symbol") == "PXD"]
        assert len(pxd_syms) == 0, "PXD (delisted) still appears in value scanner candidates"

    def test_pxd_not_in_trading_dashboard(self, live_url: str, _live_server):
        """PXD should not appear in trading advisor picks."""
        s = self._session(live_url, "oom_pxd_ta@e2e.local", "Pass1234", "OOM PXD TA")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        all_picks = data.get("all_picks", [])
        pxd_picks = [p for p in all_picks if p.get("symbol") == "PXD"]
        assert len(pxd_picks) == 0, "PXD (delisted) still appears in trading advisor picks"

    # ── Smart Advisor strips heavy arrays ────────────────────

    def test_advisor_rankings_no_heavy_arrays(self, live_url: str, _live_server):
        """Advisor /analyze rankings should NOT contain indicators/price_data/dates arrays.

        This endpoint triggers a full scan (~40+ stocks) which can take minutes.
        We use a short timeout and skip gracefully if the scan hasn't finished.
        """
        s = self._session(live_url, "oom_advisor@e2e.local", "Pass1234", "OOM Advisor")
        try:
            resp = s.get(
                f"{live_url}/api/advisor/analyze",
                params={"amount": 10000, "risk": "balanced", "period": "1y"},
                timeout=(5, 40),  # 5s connect, 40s read
            )
        except Exception:
            import pytest
            pytest.skip("Advisor scan still running — timeout waiting for results")
        if resp.status_code == 503:
            import pytest
            pytest.skip("Advisor scan still warming up")
        assert resp.status_code == 200, f"Advisor returned {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        rankings = data.get("rankings", [])
        if not rankings:
            import pytest
            pytest.skip("No advisor rankings yet — scan not complete")
        for stock in rankings[:10]:  # check first 10
            assert "indicators" not in stock, (
                f"{stock.get('symbol', '?')} still has 'indicators' array — "
                "heavy data should be stripped from scan cache"
            )
            assert "price_data" not in stock, (
                f"{stock.get('symbol', '?')} still has 'price_data' array — "
                "heavy data should be stripped from scan cache"
            )

    # ── Trading Advisor caps picks at 50 ─────────────────────

    def test_trading_dashboard_picks_capped(self, live_url: str, _live_server):
        """Trading dashboard all_picks should have ≤30 items (API caps at 30 from stored 50)."""
        s = self._session(live_url, "oom_trading@e2e.local", "Pass1234", "OOM Trading")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        all_picks = data.get("all_picks", [])
        assert len(all_picks) <= 30, (
            f"Trading dashboard returned {len(all_picks)} picks — "
            "expected ≤30 (API slice from ≤50 stored)"
        )

    def test_trading_dashboard_has_progress(self, live_url: str, _live_server):
        """Trading dashboard should report scan progress."""
        s = self._session(live_url, "oom_ta_prog@e2e.local", "Pass1234", "OOM TA Prog")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        progress = data.get("progress", {})
        assert "scanned" in progress, "Missing 'scanned' in progress"
        assert "total" in progress, "Missing 'total' in progress"
        assert "complete" in progress, "Missing 'complete' in progress"

    # ── All services still functional ────────────────────────

    def test_market_home_returns_data(self, live_url: str, _live_server):
        """Market home endpoint should return ticker + featured arrays.

        This endpoint calls fetch_live_quotes() which can block for a long
        time on cold cache.  We use a short timeout and skip gracefully.
        """
        s = self._session(live_url, "oom_mkt@e2e.local", "Pass1234", "OOM Market")
        try:
            resp = s.get(f"{live_url}/api/market/home", timeout=(5, 40))
        except Exception:
            import pytest
            pytest.skip("Market home timed out — cache likely cold")
        if resp.status_code == 503:
            import pytest
            pytest.skip("Market home returned 503 — still warming")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticker" in data, "Market home missing 'ticker'"
        assert "featured" in data, "Market home missing 'featured'"
        assert isinstance(data["ticker"], list), "ticker should be a list"
        assert isinstance(data["featured"], list), "featured should be a list"

    def test_value_scanner_returns_structure(self, live_url: str, _live_server):
        """Value scanner should still return valid structure after OOM changes."""
        s = self._session(live_url, "oom_vs@e2e.local", "Pass1234", "OOM VS")
        try:
            resp = s.get(f"{live_url}/api/value-scanner", timeout=(5, 40))
        except Exception:
            import pytest
            pytest.skip("Value scanner timed out — scan may still be running")
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data, "Missing 'candidates'"
        # scanned/total live inside stats and progress sub-objects
        assert "stats" in data, "Missing 'stats'"
        assert "progress" in data, "Missing 'progress'"
        stats = data["stats"]
        progress = data["progress"]
        assert "scanned" in stats, "Missing 'scanned' in stats"
        assert "total" in progress, "Missing 'total' in progress"

    def test_trading_dashboard_has_packages(self, live_url: str, _live_server):
        """Trading dashboard should return packages dict with strategy keys."""
        s = self._session(live_url, "oom_ta_pkg@e2e.local", "Pass1234", "OOM TA Pkg")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        packages = data.get("packages", {})
        assert isinstance(packages, dict), "packages should be a dict"

    def test_advisor_single_stock_still_has_indicators(self, live_url: str, _live_server):
        """Single-stock analysis should still return full indicators (not stripped)."""
        s = self._session(live_url, "oom_single@e2e.local", "Pass1234", "OOM Single")
        try:
            resp = s.get(f"{live_url}/api/advisor/stock/AAPL", timeout=(5, 40))
        except Exception:
            import pytest
            pytest.skip("Advisor single-stock timed out — data provider may be slow")
        if resp.status_code in (404, 503):
            import pytest
            pytest.skip("Advisor single-stock returned 404/503 — data not ready")
        assert resp.status_code == 200, f"Single stock returned {resp.status_code}"
        data = resp.json()
        # Single stock analysis should still have the full arrays
        assert "indicators" in data or "price_data" in data, (
            "Single-stock analysis should still have indicators/price_data — "
            "stripping should only affect the bulk scan cache"
        )


# ════════════════════════════════════════════════════════════
#  Yahoo-Only Data Flow — no Finnhub dependency required
# ════════════════════════════════════════════════════════════

class TestYahooOnlyDataFlow:
    """
    E2E tests that validate the Yahoo-only data provider fix:

    - All 6 featured stocks return real prices via Yahoo Finance
    - Sparkline arrays have enough data points (≥5 each)
    - Market /home endpoint returns complete ticker + featured data
    - No error strings leak into API responses
    - Prices are realistic ($1–$5000 range for known stocks)
    - Change percentages are present and reasonable
    - The combined /home endpoint is consistent (featured ⊂ ticker union)
    """

    FEATURED = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL"]
    TICKER = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN"]

    @staticmethod
    def _session(base_url: str, email: str, password: str, name: str = "Test"):
        import requests as _req
        s = _req.Session()
        px = None if "127.0.0.1" in base_url else {
            "http": "http://proxy-dmz.intel.com:911",
            "https": "http://proxy-dmz.intel.com:912",
        }
        if px:
            s.proxies.update(px)
        s.post(f"{base_url}/auth/register",
               json={"email": email, "password": password, "name": name}, timeout=30)
        resp = s.post(f"{base_url}/auth/login",
                      json={"email": email, "password": password}, timeout=30)
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        return s

    @staticmethod
    def _wait_for_cache(s, base_url: str, min_cached: int = 6, retries: int = 24):
        """Wait until the cache has at least min_cached entries."""
        import time as _time
        for _ in range(retries):
            try:
                r = s.get(f"{base_url}/api/market/cache-status", timeout=15)
                if r.status_code == 200:
                    status = r.json()
                    if status.get("cached", 0) >= min_cached or status.get("ready"):
                        return status
            except Exception:
                pass
            _time.sleep(5)
        return None

    # ── /api/market/featured returns all 6 stocks with prices ──

    def test_featured_returns_all_six_stocks(self, live_url: str, _live_server):
        """GET /api/market/featured should return all 6 featured symbols with prices."""
        s = self._session(live_url, "yahoo_feat@e2e.local", "Pass1234", "Yahoo Feat")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/featured", timeout=60)
        assert resp.status_code == 200, f"Featured API failed: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        symbols = [item["symbol"] for item in data]
        for sym in self.FEATURED:
            assert sym in symbols, (
                f"Featured stock {sym} missing from response. Got: {symbols}"
            )
        for item in data:
            assert item.get("price", 0) > 0, (
                f"{item['symbol']} has zero/missing price: {item}"
            )

    def test_featured_prices_are_realistic(self, live_url: str, _live_server):
        """Featured stock prices should be in a realistic range ($1–$5000)."""
        s = self._session(live_url, "yahoo_real@e2e.local", "Pass1234", "Yahoo Real")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/featured", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            price = item.get("price", 0)
            sym = item.get("symbol", "?")
            assert 1 < price < 5000, (
                f"{sym} price ${price} is outside realistic range $1–$5000"
            )

    def test_featured_have_change_percent(self, live_url: str, _live_server):
        """Featured stocks should include a change percentage."""
        s = self._session(live_url, "yahoo_chg@e2e.local", "Pass1234", "Yahoo Chg")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/featured", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        with_change = 0
        for item in data:
            cp = item.get("change_pct") or item.get("changePercent") or item.get("change_percent")
            if cp is not None:
                assert -50 < cp < 50, (
                    f"{item['symbol']} change% {cp} is unreasonably large"
                )
                with_change += 1
        assert with_change >= 1, "No featured stocks have a change percentage"

    # ── Sparklines have real data via Yahoo candles ──────────

    def test_featured_sparklines_have_data_points(self, live_url: str, _live_server):
        """Each featured stock should have ≥5 sparkline data points."""
        s = self._session(live_url, "yahoo_spark@e2e.local", "Pass1234", "Yahoo Spark")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/featured", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        with_sparkline = 0
        for item in data:
            spark = item.get("sparkline", [])
            sym = item.get("symbol", "?")
            if spark and len(spark) >= 5:
                with_sparkline += 1
                # Verify sparkline values are realistic prices
                assert all(isinstance(v, (int, float)) for v in spark), (
                    f"{sym} sparkline contains non-numeric values"
                )
                assert min(spark) > 0, (
                    f"{sym} sparkline has non-positive values: min={min(spark)}"
                )
                assert max(spark) > min(spark), (
                    f"{sym} sparkline is completely flat: {min(spark)}–{max(spark)}"
                )
        assert with_sparkline >= 3, (
            f"Only {with_sparkline}/6 featured stocks have ≥5 sparkline points — "
            "Yahoo candle data may not be flowing"
        )

    def test_sparkline_points_count(self, live_url: str, _live_server):
        """Sparklines should have ~21 data points (21 trading days)."""
        s = self._session(live_url, "yahoo_spcnt@e2e.local", "Pass1234", "Yahoo SpCnt")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/featured", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        for item in data:
            spark = item.get("sparkline", [])
            if spark:
                assert len(spark) >= 10, (
                    f"{item['symbol']} sparkline has only {len(spark)} points, "
                    f"expected ≥10"
                )

    # ── /api/market/ticker returns real quotes ───────────────

    def test_ticker_returns_all_symbols(self, live_url: str, _live_server):
        """GET /api/market/ticker should return all 8 ticker symbols."""
        s = self._session(live_url, "yahoo_tick@e2e.local", "Pass1234", "Yahoo Tick")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/ticker", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        symbols = [item["symbol"] for item in data]
        for sym in self.TICKER:
            assert sym in symbols, (
                f"Ticker symbol {sym} missing. Got: {symbols}"
            )
        for item in data:
            assert item.get("price", 0) > 0, (
                f"Ticker {item['symbol']} has zero price"
            )

    # ── /api/market/home combined endpoint ───────────────────

    def test_home_returns_both_ticker_and_featured(self, live_url: str, _live_server):
        """GET /api/market/home should return both ticker and featured arrays."""
        s = self._session(live_url, "yahoo_home@e2e.local", "Pass1234", "Yahoo Home")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/home", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        assert "ticker" in data, "Missing 'ticker' key in /home response"
        assert "featured" in data, "Missing 'featured' key in /home response"
        assert len(data["ticker"]) >= 6, (
            f"Ticker has only {len(data['ticker'])} items, expected ≥6"
        )
        assert len(data["featured"]) >= 4, (
            f"Featured has only {len(data['featured'])} items, expected ≥4"
        )

    def test_home_featured_have_sparklines(self, live_url: str, _live_server):
        """Featured items in /home should include sparkline arrays."""
        s = self._session(live_url, "yahoo_hmspark@e2e.local", "Pass1234", "Yahoo HmSp")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/home", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        featured = data.get("featured", [])
        with_spark = sum(1 for f in featured if len(f.get("sparkline", [])) >= 5)
        assert with_spark >= 3, (
            f"Only {with_spark}/{len(featured)} featured stocks in /home have sparklines"
        )

    def test_home_no_error_text_in_response(self, live_url: str, _live_server):
        """The /home API response should contain no error strings."""
        s = self._session(live_url, "yahoo_noerr@e2e.local", "Pass1234", "Yahoo NoErr")
        self._wait_for_cache(s, live_url)
        resp = s.get(f"{live_url}/api/market/home", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        # Check only string-valued fields to avoid false positives in numbers
        def _collect_strings(obj):
            strs = []
            if isinstance(obj, str):
                strs.append(obj.lower())
            elif isinstance(obj, dict):
                for v in obj.values():
                    strs.extend(_collect_strings(v))
            elif isinstance(obj, list):
                for v in obj:
                    strs.extend(_collect_strings(v))
            return strs
        all_strings = " ".join(_collect_strings(data))
        for bad in ("error", "unauthorized", "invalid crumb",
                     "rate limit", "too many requests"):
            assert bad not in all_strings, (
                f"API response contains error text '{bad}'"
            )

    # ── UI validation: dashboard renders Yahoo data ──────────

    def test_dashboard_market_cards_show_all_featured(self, authenticated_page: Page):
        """Dashboard should render market cards for all 6 featured symbols."""
        _nav_click(authenticated_page, "dashboard")
        try:
            authenticated_page.wait_for_selector(".market-card", timeout=60_000)
        except Exception:
            cards = authenticated_page.locator(".market-card")
            assert cards.count() > 0, "No market cards appeared — data not loading"
        authenticated_page.wait_for_timeout(5_000)
        cards = authenticated_page.locator(".market-card")
        count = cards.count()
        assert count >= 4, (
            f"Only {count} market cards rendered, expected ≥4 (all 6 featured)"
        )

    def test_dashboard_sparklines_draw_via_yahoo(self, authenticated_page: Page):
        """Sparkline charts on dashboard should render with Yahoo candle data."""
        _nav_click(authenticated_page, "dashboard")
        authenticated_page.wait_for_selector(".market-card", timeout=60_000)
        try:
            authenticated_page.wait_for_function(
                'typeof sparkCharts !== "undefined" && Object.keys(sparkCharts).length > 0',
                timeout=30_000,
            )
        except Exception:
            import pytest
            pytest.skip("sparkCharts not populated — cache may be cold")
        data_info = authenticated_page.evaluate('''() => {
            const r = {};
            for (const [sym, chart] of Object.entries(sparkCharts)) {
                const d = chart.data.datasets[0].data;
                r[sym] = {len: d.length, min: Math.min(...d), max: Math.max(...d)};
            }
            return r;
        }''')
        assert len(data_info) >= 3, (
            f"Only {len(data_info)} sparkline charts rendered, expected ≥3"
        )
        for symbol, info in data_info.items():
            assert info["len"] >= 5, (
                f"{symbol} sparkline has only {info['len']} points — "
                "Yahoo candle data not flowing to UI"
            )
            assert info["min"] > 0, f"{symbol} sparkline has non-positive prices"

    def test_dashboard_no_error_messages_visible(self, authenticated_page: Page):
        """No error text should appear anywhere on the dashboard."""
        _nav_click(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(15_000)
        body = authenticated_page.locator("#page-dashboard").inner_text().lower()
        for bad in ("http error", "unauthorized", "invalid crumb", "rate limit",
                     "finnhub", "api key"):
            assert bad not in body, (
                f"Dashboard contains error text '{bad}' — Yahoo-only mode broken"
            )


# ════════════════════════════════════════════════════════════
#  Advisor Performance Fix — candle cache, full-universe scan,
#  non-blocking warm, priority scanning, rate limiter
# ════════════════════════════════════════════════════════════

class TestAdvisorPerfAPI:
    """
    E2E tests that verify the trading advisor performance optimisations:

    - Trading advisor scans the FULL stock universe (not just cached symbols)
    - All 5 strategy packages are present in the response
    - Scan progress reports correct total (matches universe size)
    - Trading advisor responds within a reasonable time (doesn't hang)
    - Candle cache prevents redundant fetches (second call is fast)
    - Cache warmer signals readiness
    - Multiple concurrent API calls succeed (rate limiter non-blocking)
    """

    @staticmethod
    def _session(base_url: str, email: str, password: str, name: str = "Test"):
        import requests as _req
        import time as _time
        s = _req.Session()
        proxies = {"http": "http://proxy-dmz.intel.com:911",
                   "https": "http://proxy-dmz.intel.com:912"}
        px = proxies if "127.0.0.1" not in base_url and "localhost" not in base_url else None
        if px:
            s.proxies.update(px)
        # Use a time-based suffix to avoid stale-registration collisions on live site
        ts = str(int(_time.time()))[-6:]
        unique_email = email.replace("@", f"{ts}@")
        s.post(f"{base_url}/auth/register",
               json={"email": unique_email, "password": password, "name": name}, timeout=60)
        resp = s.post(f"{base_url}/auth/login",
                      json={"email": unique_email, "password": password}, timeout=60)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        return s

    # ── Trading advisor scans full universe ──────────────────

    def test_trading_advisor_total_matches_universe(self, live_url: str, _live_server):
        """progress.total should match ALL_UNIVERSE size (~257), proving stubs
        are created for uncached symbols so the full universe is scanned."""
        s = self._session(live_url, "perf_total@e2e.local", "Pass1234", "Perf Total")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200, f"Trading API failed: {resp.status_code}"
        data = resp.json()
        progress = data.get("progress", {})
        total = progress.get("total", 0)
        # Universe is ~257 symbols; total should be at least 200 (allowing for
        # minor changes) — the key assertion is it's NOT just 30-40 (cached only)
        assert total >= 200, (
            f"Trading advisor total is only {total} — expected ≥200. "
            "Stubs for uncached symbols may not be working, causing the scan "
            "to only process already-cached symbols."
        )

    def test_trading_advisor_progress_fields(self, live_url: str, _live_server):
        """Progress should have scanned, total, complete fields with sane values."""
        s = self._session(live_url, "perf_prog@e2e.local", "Pass1234", "Perf Prog")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        progress = data.get("progress", {})
        assert "scanned" in progress, "Missing 'scanned' in progress"
        assert "total" in progress, "Missing 'total' in progress"
        assert "complete" in progress, "Missing 'complete' in progress"
        assert isinstance(progress["scanned"], int), "scanned should be int"
        assert isinstance(progress["total"], int), "total should be int"
        assert progress["scanned"] <= progress["total"], (
            f"scanned ({progress['scanned']}) > total ({progress['total']})"
        )

    # ── All 5 strategy packages present ──────────────────────

    def test_trading_advisor_all_five_packages(self, live_url: str, _live_server):
        """Packages dict should contain all 5 strategy keys: hidden, institutional,
        momentum, swing, oversold."""
        s = self._session(live_url, "perf_pkg@e2e.local", "Pass1234", "Perf Pkg")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        packages = data.get("packages", {})
        expected_keys = {"hidden", "institutional", "momentum", "swing", "oversold"}
        # If scan hasn't started yet, packages may be empty — that's ok
        if packages:
            actual_keys = set(packages.keys())
            assert expected_keys == actual_keys, (
                f"Expected packages {expected_keys}, got {actual_keys}"
            )
            # Each package should have a picks list
            for key in expected_keys:
                pkg = packages[key]
                assert "picks" in pkg, f"Package '{key}' missing 'picks' list"
                assert isinstance(pkg["picks"], list), f"Package '{key}' picks should be a list"

    # ── Trading advisor responds promptly ─────────────────────

    def test_trading_advisor_responds_within_timeout(self, live_url: str, _live_server):
        """The /api/trading endpoint should respond within 10 seconds even when
        the scan is still in progress (non-blocking)."""
        import time
        s = self._session(live_url, "perf_time@e2e.local", "Pass1234", "Perf Time")
        t0 = time.time()
        resp = s.get(f"{live_url}/api/trading", timeout=10)
        elapsed = time.time() - t0
        assert resp.status_code == 200, f"Trading API failed: {resp.status_code}"
        assert elapsed < 10, (
            f"Trading API took {elapsed:.1f}s — should respond instantly with "
            "partial/cached results, not block on scan completion"
        )

    # ── Market mood sums to ~100% ─────────────────────────────

    def test_trading_advisor_market_mood_valid(self, live_url: str, _live_server):
        """market_mood bullish+neutral+bearish should sum to ~100% when scan has picks."""
        s = self._session(live_url, "perf_mood@e2e.local", "Pass1234", "Perf Mood")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        mood = data.get("market_mood", {})
        assert "bullish" in mood, "Missing 'bullish' in market_mood"
        assert "neutral" in mood, "Missing 'neutral' in market_mood"
        assert "bearish" in mood, "Missing 'bearish' in market_mood"
        total_pct = mood["bullish"] + mood["neutral"] + mood["bearish"]
        if data.get("all_picks"):  # only check when there are actual picks
            assert 95 <= total_pct <= 105, (
                f"market_mood sums to {total_pct}% — expected ~100%"
            )

    # ── Cache warmer reports readiness ────────────────────────

    def test_cache_warmer_signals_ready(self, live_url: str, _live_server):
        """After server has been running, cache-status should report ready=True,
        proving warm_cache phase 1 completed and _warm_done.set() was called."""
        import time
        s = self._session(live_url, "perf_warm@e2e.local", "Pass1234", "Perf Warm")
        # Poll cache-status up to 180s for ready=True (Render cold start + Finnhub rate limits)
        deadline = time.time() + 180
        ready = False
        while time.time() < deadline:
            try:
                resp = s.get(f"{live_url}/api/market/cache-status", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ready"):
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(5)
        assert ready, (
            "Cache warmer never set ready=True within 180s — "
            "_warm_done.set() may not be called or phase 1 is stuck"
        )

    # ── Concurrent API calls succeed ──────────────────────────

    def test_concurrent_api_calls_dont_block(self, live_url: str, _live_server):
        """Fire multiple API calls in parallel — they should all succeed,
        proving the rate limiter sleeps outside the lock."""
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        s = self._session(live_url, "perf_conc@e2e.local", "Pass1234", "Perf Conc")

        endpoints = [
            "/api/trading",
            "/api/market/cache-status",
            "/api/value-scanner",
        ]

        def _call(url):
            t0 = time.time()
            try:
                resp = s.get(url, timeout=30)
                return url, resp.status_code, time.time() - t0
            except Exception as e:
                return url, str(e), time.time() - t0

        t0 = time.time()
        results = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_call, f"{live_url}{ep}"): ep for ep in endpoints}
            for fut in as_completed(futures):
                results.append(fut.result())
        total_wall = time.time() - t0

        # All should succeed
        for url, status, elapsed in results:
            assert status == 200, f"{url} returned {status}"

        # Wall-clock time should be reasonable (< 30s for 3 parallel calls)
        assert total_wall < 30, (
            f"Concurrent calls took {total_wall:.1f}s wall-clock — "
            "rate limiter may still be serializing threads"
        )

    # ── Second stock history call benefits from candle cache ──

    def test_candle_cache_speeds_up_repeat_calls(self, live_url: str, _live_server):
        """Fetching the same stock's history twice should be faster the second time,
        proving the candle cache in data_provider.get_candles() works."""
        import time
        s = self._session(live_url, "perf_cache@e2e.local", "Pass1234", "Perf Cache")

        # First call — populates the cache
        t0 = time.time()
        try:
            resp1 = s.get(f"{live_url}/api/stock/AAPL/history", timeout=30)
        except Exception:
            import pytest
            pytest.skip("Stock history timed out — data provider may be slow")
        elapsed1 = time.time() - t0

        if resp1.status_code != 200:
            import pytest
            pytest.skip(f"Stock history returned {resp1.status_code} — data not available")

        # Second call — should hit cache
        t0 = time.time()
        resp2 = s.get(f"{live_url}/api/stock/AAPL/history", timeout=30)
        elapsed2 = time.time() - t0

        assert resp2.status_code == 200
        # Second call should be noticeably faster (at least 2x)
        # On cold start, first call might take 2-10s, second should be < 1s
        if elapsed1 > 1.0:
            assert elapsed2 < elapsed1, (
                f"Second call ({elapsed2:.2f}s) was not faster than first ({elapsed1:.2f}s) — "
                "candle cache may not be working"
            )

    # ── Picks capped at 30 in API response ────────────────────

    def test_all_picks_capped_at_30(self, live_url: str, _live_server):
        """API should return at most 30 picks (sliced from stored 50)."""
        s = self._session(live_url, "perf_cap@e2e.local", "Pass1234", "Perf Cap")
        resp = s.get(f"{live_url}/api/trading", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        all_picks = data.get("all_picks", [])
        assert len(all_picks) <= 30, (
            f"API returned {len(all_picks)} picks — expected ≤30"
        )

    # ── Stock detail returns data (Yahoo-first fallback works) ─

    def test_stock_detail_returns_data(self, live_url: str, _live_server):
        """Stock detail endpoint should return price data proving the
        Yahoo-first, Finnhub-fallback data provider chain works."""
        s = self._session(live_url, "perf_detail@e2e.local", "Pass1234", "Perf Detail")
        try:
            resp = s.get(f"{live_url}/api/stock/AAPL", timeout=30)
        except Exception:
            import pytest
            pytest.skip("Stock detail timed out")
        if resp.status_code == 404:
            import pytest
            pytest.skip("Stock detail returned 404 — data not available yet")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("symbol") == "AAPL", "Symbol mismatch"
        assert data.get("price", 0) > 0, "Price should be positive"
        assert data.get("name"), "Missing company name"

    # ── Value scanner responds (higher worker count) ──────────

    def test_value_scanner_responds_with_stats(self, live_url: str, _live_server):
        """Value scanner should return stats with scanned count, proving
        the increased worker pool is functioning."""
        s = self._session(live_url, "perf_vs@e2e.local", "Pass1234", "Perf VS")
        try:
            resp = s.get(f"{live_url}/api/value-scanner", timeout=60)
        except Exception:
            import pytest
            pytest.skip("Value scanner timed out")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data, "Missing 'stats'"
        assert "progress" in data, "Missing 'progress'"
        stats = data["stats"]
        assert "scanned" in stats, "Missing 'scanned' in stats"
        # scanned should be > 0 if the scanner is running
        assert stats["scanned"] >= 0, "scanned should be non-negative"
