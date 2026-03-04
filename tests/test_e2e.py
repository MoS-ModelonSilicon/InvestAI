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
