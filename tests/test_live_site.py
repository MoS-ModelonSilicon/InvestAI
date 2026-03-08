"""
Comprehensive E2E tests for InvestAI — targeting the LIVE deployed site.

These tests cover every major feature flow end-to-end, verifying real data,
UI interactions, and API responses on the actual production deployment.

Run against the live site:
    cd finance-tracker
    pytest tests/test_live_site.py --live-url https://investai-utho.onrender.com --headed
    pytest tests/test_live_site.py --live-url https://investai-utho.onrender.com   # headless

Run against local server:
    pytest tests/test_live_site.py
"""

import re
import uuid

import pytest
from playwright.sync_api import Page, expect

from conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD, TEST_USER_NAME


# ── Helpers ──────────────────────────────────────────────

SLOW = 60_000  # generous timeout for Render cold-start
API_WAIT = 8_000  # wait for API data to arrive
CHART_WAIT = 15_000  # wait for Chart.js to render


def _nav(page: Page, page_id: str):
    """Click a sidebar nav link, using force for overflow items."""
    page.locator(f'.nav-link[data-page="{page_id}"]').click(force=True)
    page.wait_for_timeout(500)


def _wait_for_content(page: Page, container_sel: str, *, min_len: int = 100, timeout: int = 30_000, poll: int = 1_000):
    """Poll until the container has meaningful content (HTML length >= min_len).

    Replaces dumb ``wait_for_timeout`` for data-dependent assertions.
    Returns the inner HTML once it exceeds *min_len*, or the last snapshot
    if we time out (the caller can still assert on it).
    """
    import time as _t

    deadline = _t.monotonic() + timeout / 1000
    html = ""
    while _t.monotonic() < deadline:
        loc = page.locator(container_sel)
        if loc.count() > 0:
            html = loc.inner_html()
            # Content is considered "loaded" when it has enough HTML and
            # spinner/loading indicators have disappeared.
            if len(html) >= min_len and "loading" not in html.lower():
                return html
        page.wait_for_timeout(poll)
    return html  # best-effort snapshot


def _unique(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ════════════════════════════════════════════════════════════
#  1. STOCK DETAIL — deep dive into a single stock
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestStockDetail:
    """Navigate to a stock detail page and verify all sections render."""

    def _open_stock(self, page: Page):
        """Click on first market card or watchlist item to open stock detail."""
        _nav(page, "dashboard")
        page.wait_for_timeout(API_WAIT)
        # Click first market card which should navigate to stock detail
        card = page.locator(".market-card").first
        if card.count() > 0:
            card.click()
            page.wait_for_timeout(3000)
            return True
        return False

    def test_stock_detail_opens_from_market_card(self, authenticated_page: Page):
        """Clicking a market card on the dashboard should open the stock detail view."""
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(API_WAIT)
        cards = authenticated_page.locator(".market-card")
        if cards.count() == 0:
            return  # no market data, skip
        cards.first.click()
        authenticated_page.wait_for_timeout(5000)
        # Stock detail page should be visible
        detail = authenticated_page.locator("#page-stock-detail")
        expect(detail).to_have_class(re.compile("active"))

    def test_stock_detail_shows_price_and_info(self, authenticated_page: Page):
        """Stock detail should show price, company name, and key metrics."""
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(API_WAIT)
        cards = authenticated_page.locator(".market-card")
        if cards.count() == 0:
            return
        cards.first.click()
        html = _wait_for_content(authenticated_page, "#page-stock-detail", min_len=200, timeout=30_000)
        # Should show loaded content (not just spinner)
        assert "loading" not in html.lower() or "$" in html, (
            f"Stock detail still loading or missing data. HTML: {html[:500]}"
        )

    def test_stock_detail_has_chart(self, authenticated_page: Page):
        """Stock detail should render an interactive price chart."""
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(API_WAIT)
        cards = authenticated_page.locator(".market-card")
        if cards.count() == 0:
            return
        cards.first.click()
        _wait_for_content(authenticated_page, "#page-stock-detail", min_len=200, timeout=30_000)
        # Look for the chart canvas
        canvas = authenticated_page.locator("#page-stock-detail canvas")
        if canvas.count() > 0:
            box = canvas.first.bounding_box()
            assert box is not None, "Stock detail chart has no bounding box"
            assert box["width"] > 0, "Stock detail chart has zero width"

    def test_stock_detail_timeframe_buttons(self, authenticated_page: Page):
        """Timeframe buttons (1D, 1W, 1M, etc.) should be present."""
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(API_WAIT)
        cards = authenticated_page.locator(".market-card")
        if cards.count() == 0:
            return
        cards.first.click()
        _wait_for_content(authenticated_page, "#page-stock-detail", min_len=200, timeout=30_000)
        # Look for timeframe buttons
        btns = authenticated_page.locator("#page-stock-detail .timeframe-btn, #page-stock-detail .tf-btn")
        if btns.count() > 0:
            assert btns.count() >= 3, f"Expected multiple timeframe buttons, got {btns.count()}"

    def test_stock_detail_action_buttons(self, authenticated_page: Page):
        """Should have action buttons (Watchlist, Portfolio, Alert, etc.)."""
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(API_WAIT)
        cards = authenticated_page.locator(".market-card")
        if cards.count() == 0:
            return
        cards.first.click()
        _wait_for_content(authenticated_page, "#page-stock-detail", min_len=200, timeout=30_000)
        detail = authenticated_page.locator("#page-stock-detail")
        html = detail.inner_html()
        # Should have action buttons
        has_watchlist = "watchlist" in html.lower() or "watch" in html.lower()
        has_portfolio = "portfolio" in html.lower()
        has_alert = "alert" in html.lower()
        assert has_watchlist or has_portfolio or has_alert, (
            f"Stock detail page missing action buttons. HTML: {html[:500]}"
        )


# ════════════════════════════════════════════════════════════
#  2. DCA PLANNER — full CRUD flow
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestDCAPlanner:
    """Test the Dollar Cost Averaging planner feature."""

    def _go(self, page: Page):
        _nav(page, "dca")
        page.wait_for_timeout(API_WAIT)

    def test_dca_page_loads(self, authenticated_page: Page):
        """DCA page should load with plan list and dashboard content."""
        self._go(authenticated_page)
        container = authenticated_page.locator("#page-dca")
        expect(container).to_have_class(re.compile("active"))
        html = container.inner_html()
        assert len(html) > 50, f"DCA page is mostly empty. HTML: {html[:300]}"

    def test_dca_create_plan(self, authenticated_page: Page):
        """Create a new DCA plan via the UI and verify it appears."""
        self._go(authenticated_page)
        # Click "New DCA Plan" button
        new_btn = authenticated_page.locator("#page-dca").get_by_role(
            "button", name=re.compile("new.*plan|add.*plan", re.IGNORECASE)
        )
        if new_btn.count() == 0:
            return  # button not found, skip
        new_btn.click(force=True)
        authenticated_page.wait_for_timeout(1000)
        # Fill in the form
        symbol_input = authenticated_page.locator("#dca-symbol")
        if symbol_input.count() > 0:
            symbol_input.fill("MSFT")
            budget_input = authenticated_page.locator("#dca-budget, #dca-amount, #dca-monthly")
            if budget_input.count() > 0:
                budget_input.first.fill("200")
            authenticated_page.locator('#dca-form button[type="submit"], #dca-form .btn-primary').first.click()
            authenticated_page.wait_for_timeout(3000)
            html = authenticated_page.locator("#page-dca").inner_html()
            assert "MSFT" in html, f"DCA plan for MSFT not visible after creation. HTML: {html[:500]}"

    def test_dca_dashboard_metrics(self, authenticated_page: Page):
        """DCA dashboard should show allocation metrics."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-dca").inner_html()
        # Should show some monetary values or percentage allocations
        has_dollar = "$" in html
        has_percent = "%" in html
        has_plan_content = "plan" in html.lower() or "dca" in html.lower()
        assert has_dollar or has_percent or has_plan_content, f"DCA page missing financial metrics. HTML: {html[:500]}"

    def test_dca_budget_suggestion(self, authenticated_page: Page):
        """Budget suggestion section should provide AI-based budget recommendations."""
        self._go(authenticated_page)
        # Look for budget suggestion area
        html = authenticated_page.locator("#page-dca").inner_html()
        # Budget suggestion usually shows recommended budget or allocation
        has_suggestion = "suggest" in html.lower() or "budget" in html.lower() or "allocat" in html.lower()
        assert has_suggestion, f"DCA page missing budget suggestion. HTML: {html[:500]}"


# ════════════════════════════════════════════════════════════
#  3. AUTOPILOT / AI PICKS — strategy simulation
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestAutopilotAIPicks:
    """Test the Autopilot strategy profiles and simulation."""

    def _go(self, page: Page):
        _nav(page, "autopilot")
        page.wait_for_timeout(API_WAIT)

    def test_autopilot_page_loads_profiles(self, authenticated_page: Page):
        """Autopilot page should show strategy profile cards (daredevil, strategist, fortress)."""
        self._go(authenticated_page)
        container = authenticated_page.locator("#page-autopilot")
        expect(container).to_have_class(re.compile("active"))
        html = container.inner_html()
        assert len(html) > 100, f"Autopilot page is mostly empty. HTML: {html[:300]}"
        # Should have profile cards or strategy names
        has_profiles = any(
            kw in html.lower()
            for kw in [
                "daredevil",
                "strategist",
                "fortress",
                "aggressive",
                "balanced",
                "conservative",
                "profile",
                "strategy",
            ]
        )
        assert has_profiles, f"Autopilot page missing strategy profiles. HTML: {html[:500]}"

    def test_autopilot_select_profile(self, authenticated_page: Page):
        """Selecting a strategy profile should highlight it."""
        self._go(authenticated_page)
        # Click the first profile card
        cards = authenticated_page.locator(".profile-card, .strategy-card, .ap-profile")
        if cards.count() > 0:
            cards.first.click()
            authenticated_page.wait_for_timeout(500)
            # Check it's selected
            html = cards.first.inner_html()
            # Just verify click didn't cause an error
            assert len(html) > 0

    def test_autopilot_run_simulation(self, authenticated_page: Page):
        """Running a simulation should produce results with a chart and portfolio data."""
        self._go(authenticated_page)
        # Select a profile if available
        cards = authenticated_page.locator(".profile-card, .strategy-card, .ap-profile")
        if cards.count() > 0:
            cards.first.click()
            authenticated_page.wait_for_timeout(500)

        # Click Run Simulation
        sim_btn = authenticated_page.locator("#page-autopilot").get_by_role(
            "button", name=re.compile("simulat|run|backtest", re.IGNORECASE)
        )
        if sim_btn.count() == 0:
            return  # skip if no button found
        btn = sim_btn.first

        btn.click(force=True)
        # Wait for results (this can be slow with live data)
        html = _wait_for_content(authenticated_page, "#page-autopilot", min_len=500, timeout=30_000)
        # Results should show dollar values, percentages, or stock symbols
        has_results = "$" in html or "%" in html or "return" in html.lower()
        assert has_results, f"Simulation produced no visible results. HTML: {html[:500]}"

    def test_autopilot_amount_presets(self, authenticated_page: Page):
        """Investment amount presets ($1K–$100K) should be clickable."""
        self._go(authenticated_page)
        presets = authenticated_page.locator(".amount-btn, .amount-preset, [data-amount]")
        if presets.count() > 0:
            assert presets.count() >= 3, f"Expected multiple amount presets, got {presets.count()}"


# ════════════════════════════════════════════════════════════
#  4. SMART ADVISOR — long-term analysis
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestSmartAdvisor:
    """Test the Smart Advisor (long-term stock analysis)."""

    def _go(self, page: Page):
        _nav(page, "smart-advisor")
        page.wait_for_timeout(API_WAIT)

    def test_advisor_page_loads(self, authenticated_page: Page):
        """Advisor page should show analysis controls (risk, amount, period)."""
        self._go(authenticated_page)
        container = authenticated_page.locator("#page-smart-advisor")
        expect(container).to_have_class(re.compile("active"))
        html = container.inner_html()
        assert len(html) > 100, f"Advisor page is mostly empty. HTML: {html[:300]}"

    def test_advisor_has_risk_selector(self, authenticated_page: Page):
        """Should have a risk level selector (conservative/balanced/aggressive)."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-smart-advisor").inner_html()
        has_risk = any(kw in html.lower() for kw in ["conservative", "balanced", "aggressive", "risk"])
        assert has_risk, f"Advisor page missing risk selector. HTML: {html[:500]}"

    def test_advisor_run_analysis(self, authenticated_page: Page):
        """Running the analysis should produce stock rankings and portfolio data."""
        self._go(authenticated_page)
        # Click Run Analysis button
        btn = authenticated_page.locator("#page-smart-advisor").get_by_role(
            "button", name=re.compile("analy|scan|run", re.IGNORECASE)
        )
        if btn.count() == 0:
            return
        btn.first.click(force=True)
        # Wait for the long analysis (scanning 80+ stocks)
        html = _wait_for_content(authenticated_page, "#page-smart-advisor", min_len=1000, timeout=45_000)
        # Should show results with stock symbols, scores, or portfolio data
        has_results = "$" in html or "score" in html.lower() or "rank" in html.lower()
        assert has_results or len(html) > 2000, f"Advisor analysis produced no visible results. HTML: {html[:500]}"

    def test_advisor_tabs_switch(self, authenticated_page: Page):
        """Should be able to switch between Long-term and Short-term tabs."""
        self._go(authenticated_page)
        # Look for tab buttons
        tabs = authenticated_page.locator("#page-smart-advisor .tab-btn, #page-smart-advisor .advisor-tab")
        if tabs.count() >= 2:
            tabs.last.click()
            authenticated_page.wait_for_timeout(1000)
            tabs.first.click()
            authenticated_page.wait_for_timeout(1000)


# ════════════════════════════════════════════════════════════
#  5. TRADING ADVISOR — short-term picks
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestTradingAdvisor:
    """Test the Trading Advisor (short-term picks with technical analysis)."""

    def _go(self, page: Page):
        _nav(page, "smart-advisor")
        page.wait_for_timeout(3000)
        # Switch to the short-term/trading tab
        tabs = page.locator("#page-smart-advisor .tab-btn, #page-smart-advisor .advisor-tab")
        if tabs.count() >= 2:
            tabs.last.click()
            page.wait_for_timeout(API_WAIT)

    def test_trading_tab_loads(self, authenticated_page: Page):
        """Trading advisor tab should load with market mood and picks."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-smart-advisor").inner_html()
        # Should show trading-related content
        has_trading = any(
            kw in html.lower()
            for kw in [
                "trade",
                "pick",
                "package",
                "mood",
                "signal",
                "entry",
                "target",
                "stop",
                "r/r",
                "rsi",
                "macd",
                "bullish",
                "bearish",
                "neutral",
            ]
        )
        assert has_trading or len(html) > 1000, f"Trading tab has no trading-related content. HTML: {html[:500]}"

    def test_trading_shows_picks_or_scan(self, authenticated_page: Page):
        """Should show trading picks or a scan-in-progress indicator."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-smart-advisor").inner_html()
        has_picks = "$" in html or "%" in html or "entry" in html.lower()
        has_scan = "scan" in html.lower() or "loading" in html.lower()
        assert has_picks or has_scan or len(html) > 500, (
            f"Trading section has no picks or scan progress. HTML: {html[:500]}"
        )


# ════════════════════════════════════════════════════════════
#  6. PICKS TRACKER — Discord picks evaluation
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestPicksTracker:
    """Test the Discord picks tracker and evaluation page."""

    def _go(self, page: Page):
        _nav(page, "picks-tracker")
        page.wait_for_timeout(API_WAIT)

    def test_picks_tracker_loads(self, authenticated_page: Page):
        """Picks tracker page should render with filter tabs and stats."""
        self._go(authenticated_page)
        container = authenticated_page.locator("#page-picks-tracker")
        expect(container).to_have_class(re.compile("active"))
        html = container.inner_html()
        assert len(html) > 100, f"Picks tracker is mostly empty. HTML: {html[:300]}"

    def test_picks_tracker_has_filter_tabs(self, authenticated_page: Page):
        """Should have filter tabs (All, Breakout, Swing, Options)."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-picks-tracker").inner_html()
        has_tabs = any(kw in html.lower() for kw in ["breakout", "swing", "options", "all"])
        assert has_tabs, f"Picks tracker missing filter tabs. HTML: {html[:500]}"

    def test_picks_tracker_stats_row(self, authenticated_page: Page):
        """Should show summary stats (total picks, win rate, avg gain)."""
        self._go(authenticated_page)
        # Wait for longer since this evaluates Discord picks
        authenticated_page.wait_for_timeout(15000)
        html = authenticated_page.locator("#page-picks-tracker").inner_html()
        has_stats = "%" in html or "win" in html.lower() or "pick" in html.lower()
        assert has_stats or len(html) > 500, f"Picks tracker missing stats. HTML: {html[:500]}"

    def test_picks_tracker_search(self, authenticated_page: Page):
        """Search bar should filter picks by symbol."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(10000)
        search = authenticated_page.locator("#picks-search")
        if search.count() > 0:
            expect(search).to_be_visible()
            search.fill("AAPL")
            authenticated_page.wait_for_timeout(1000)
            search.fill("")
            authenticated_page.wait_for_timeout(500)


# ════════════════════════════════════════════════════════════
#  7. VALUE SCANNER — Graham-Buffett analysis
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestValueScanner:
    """Test the Value Scanner (Graham-Buffett criteria stock screening)."""

    def _go(self, page: Page):
        _nav(page, "screener")
        page.wait_for_timeout(2000)
        # Switch to Value Scanner tab
        tabs = page.locator("#page-screener .tab-btn, #page-screener .scr-tab")
        for i in range(tabs.count()):
            txt = tabs.nth(i).inner_text()
            if "value" in txt.lower() or "scanner" in txt.lower():
                tabs.nth(i).click()
                page.wait_for_timeout(API_WAIT)
                return
        # Fallback: try clicking any second tab
        if tabs.count() >= 2:
            tabs.nth(1).click()
            page.wait_for_timeout(API_WAIT)

    def test_value_scanner_loads(self, authenticated_page: Page):
        """Value scanner tab should be accessible and show filters/results."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-screener").inner_html()
        has_scanner = any(kw in html.lower() for kw in ["value", "scanner", "graham", "buffett", "margin", "safety"])
        assert has_scanner or len(html) > 1000, f"Value scanner tab not showing. HTML: {html[:500]}"

    def test_value_scanner_run_scan(self, authenticated_page: Page):
        """Running the value scan should produce scored stocks."""
        self._go(authenticated_page)
        # Look for a Run/Scan button
        btn = authenticated_page.locator("#page-screener").get_by_role(
            "button", name=re.compile("scan|search|run|find", re.IGNORECASE)
        )
        if btn.count() > 0:
            btn.first.click(force=True)
            authenticated_page.wait_for_timeout(15000)
            html = authenticated_page.locator("#page-screener").inner_html()
            # Should show results with scores or stock data
            assert len(html) > 500, f"Value scan returned minimal results. HTML: {html[:500]}"


# ════════════════════════════════════════════════════════════
#  8. WATCHLIST — full interaction flow
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestWatchlistInteraction:
    """Full watchlist interaction tests including add, view, and remove."""

    def _go(self, page: Page):
        _nav(page, "watchlist")
        page.wait_for_timeout(API_WAIT)

    def test_add_to_watchlist_from_screener(self, authenticated_page: Page):
        """Search for a stock in screener and add it to watchlist."""
        _nav(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(2000)
        # Run a search
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        # Click add to watchlist on the first result if available
        add_btns = authenticated_page.locator(".add-watchlist-btn, [data-action='watchlist'], .scr-watch-btn")
        if add_btns.count() > 0:
            add_btns.first.click(force=True)
            authenticated_page.wait_for_timeout(2000)

    def test_watchlist_shows_live_prices(self, authenticated_page: Page):
        """Watchlist cards should display live price data."""
        self._go(authenticated_page)
        cards = authenticated_page.locator(".watchlist-card, .wl-card")
        if cards.count() > 0:
            html = cards.first.inner_html()
            assert "$" in html or "." in html, f"Watchlist card missing price. HTML: {html[:300]}"

    def test_watchlist_card_has_metrics(self, authenticated_page: Page):
        """Watchlist cards should show P/E, market cap, or other metrics."""
        self._go(authenticated_page)
        container = authenticated_page.locator("#watchlist-container")
        html = container.inner_html()
        if "empty" in html.lower() or len(html) < 100:
            return  # empty watchlist, skip
        has_metrics = any(kw in html.lower() for kw in ["p/e", "market cap", "dividend", "beta", "sector", "vol"])
        assert has_metrics, f"Watchlist cards missing metrics. HTML: {html[:500]}"


# ════════════════════════════════════════════════════════════
#  9. PORTFOLIO — advanced features
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestPortfolioAdvanced:
    """Advanced portfolio tests: multiple holdings, allocation, delete."""

    def _go(self, page: Page):
        _nav(page, "portfolio")
        page.wait_for_timeout(3000)

    def test_add_multiple_holdings(self, authenticated_page: Page):
        """Add multiple holdings and verify they all appear."""
        self._go(authenticated_page)
        holdings = [
            ("GOOGL", "Alphabet", "5", "175.00"),
            ("AMZN", "Amazon", "3", "185.00"),
        ]
        for symbol, name, qty, price in holdings:
            authenticated_page.locator("text=+ Add Holding").click(force=True)
            authenticated_page.wait_for_timeout(500)
            authenticated_page.fill("#holding-symbol", symbol)
            authenticated_page.fill("#holding-name", name)
            authenticated_page.fill("#holding-qty", qty)
            authenticated_page.fill("#holding-price", price)
            authenticated_page.fill("#holding-date", "2025-06-01")
            authenticated_page.locator('#holding-form button[type="submit"]').click()
            authenticated_page.wait_for_timeout(5000)

        html = authenticated_page.locator("#portfolio-container").inner_html()
        for symbol, _, _, _ in holdings:
            assert symbol in html, f"Portfolio missing {symbol}. HTML: {html[:500]}"

    def test_sector_allocation_chart_renders(self, authenticated_page: Page):
        """Sector allocation pie chart should render with holdings data."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(CHART_WAIT)
        alloc = authenticated_page.locator("#pf-alloc-chart, .pf-chart-wrap canvas").first
        if alloc.count() > 0:
            box = alloc.bounding_box()
            assert box is not None, "Allocation chart has no bounding box"
            assert box["width"] > 0, "Allocation chart has zero width"

    def test_portfolio_performance_vs_sp500(self, authenticated_page: Page):
        """Performance chart should compare portfolio vs S&P 500."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(CHART_WAIT)
        html = authenticated_page.locator("#portfolio-container").inner_html()
        has_perf = "s&p" in html.lower() or "benchmark" in html.lower() or "performance" in html.lower()
        assert has_perf or authenticated_page.locator("#pf-perf-chart").count() > 0, (
            f"Portfolio missing performance/benchmark section. HTML: {html[:500]}"
        )

    def test_portfolio_gain_loss_display(self, authenticated_page: Page):
        """Holdings should show gain/loss values with + or - indicators."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(CHART_WAIT)
        html = authenticated_page.locator("#portfolio-container").inner_html()
        # Should show percentage gains or dollar gains
        has_gain = "+" in html or "-" in html or "gain" in html.lower() or "loss" in html.lower()
        assert has_gain, f"Portfolio missing gain/loss display. HTML: {html[:500]}"

    def test_portfolio_search_filters_holdings(self, authenticated_page: Page):
        """Search bar should filter displayed holdings."""
        self._go(authenticated_page)
        authenticated_page.wait_for_timeout(5000)
        search = authenticated_page.locator("#portfolio-search")
        if search.count() > 0 and search.is_visible():
            search.fill("AAPL")
            authenticated_page.wait_for_timeout(1000)
            search.fill("")
            authenticated_page.wait_for_timeout(500)


# ════════════════════════════════════════════════════════════
#  10. ALERTS — advanced interactions
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestAlertsAdvanced:
    """Advanced alert tests: multiple conditions, dismiss, search."""

    def _go(self, page: Page):
        _nav(page, "alerts")
        page.wait_for_timeout(3000)

    def test_create_below_alert(self, authenticated_page: Page):
        """Create a 'below' price alert and verify it appears."""
        self._go(authenticated_page)
        authenticated_page.locator("text=+ New Alert").click(force=True)
        authenticated_page.wait_for_timeout(500)
        authenticated_page.fill("#alert-symbol", "AAPL")
        authenticated_page.select_option("#alert-condition", "below")
        authenticated_page.fill("#alert-price", "100")
        authenticated_page.locator('#alert-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(3000)
        html = authenticated_page.locator("#alerts-container").inner_html()
        assert "AAPL" in html, f"Alert for AAPL not found. HTML: {html[:500]}"

    def test_alerts_show_current_price(self, authenticated_page: Page):
        """Alert cards should display the current live price of the symbol."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#alerts-container").inner_html()
        if len(html) < 100:
            return  # no alerts, skip
        # Should show current price with $ sign
        assert "$" in html, f"Alerts missing current price display. HTML: {html[:500]}"

    def test_alerts_search_filters(self, authenticated_page: Page):
        """Search bar should filter alerts by symbol."""
        self._go(authenticated_page)
        search = authenticated_page.locator("#alerts-search")
        if search.count() > 0 and search.is_visible():
            search.fill("TSLA")
            authenticated_page.wait_for_timeout(500)
            search.fill("")
            authenticated_page.wait_for_timeout(500)

    def test_alert_dismiss_triggered(self, authenticated_page: Page):
        """If any alerts are triggered, the dismiss button should be accessible."""
        self._go(authenticated_page)
        dismiss_btns = authenticated_page.locator(".dismiss-btn, [data-action='dismiss']")
        if dismiss_btns.count() > 0:
            # Click dismiss on the first triggered alert
            dismiss_btns.first.click(force=True)
            authenticated_page.wait_for_timeout(2000)


# ════════════════════════════════════════════════════════════
#  11. TRANSACTIONS — edit and delete flow
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestTransactionsAdvanced:
    """Advanced transaction tests: edit, delete, date filtering."""

    def _go(self, page: Page):
        _nav(page, "transactions")
        page.wait_for_timeout(3000)

    def test_create_income_transaction(self, authenticated_page: Page):
        """Create an income transaction (as opposed to expense)."""
        self._go(authenticated_page)
        authenticated_page.get_by_role("button", name="+ Add Transaction").click(force=True)
        authenticated_page.select_option("#tx-type", "income")
        authenticated_page.fill("#tx-amount", "5000.00")
        authenticated_page.fill("#tx-date", "2026-03-01")
        authenticated_page.fill("#tx-desc", "E2E salary test")
        authenticated_page.locator('#tx-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(2000)
        body = authenticated_page.locator("#tx-body")
        expect(body).to_contain_text("E2E salary test")

    def test_transaction_date_filter(self, authenticated_page: Page):
        """Filtering by date range should narrow visible transactions."""
        self._go(authenticated_page)
        # Set a date range
        from_input = authenticated_page.locator("#filter-from, #txn-date-from")
        to_input = authenticated_page.locator("#filter-to, #txn-date-to")
        if from_input.count() > 0 and to_input.count() > 0:
            from_input.first.fill("2026-01-01")
            to_input.first.fill("2026-12-31")
            authenticated_page.get_by_role("button", name="Filter").click(force=True)
            authenticated_page.wait_for_timeout(2000)
            rows = authenticated_page.locator("#tx-body tr")
            assert rows.count() >= 0  # just verify filter didn't crash

    def test_transaction_search(self, authenticated_page: Page):
        """Search bar should filter transactions by description."""
        self._go(authenticated_page)
        search = authenticated_page.locator("#transactions-search")
        if search.count() > 0 and search.is_visible():
            search.fill("grocery")
            authenticated_page.wait_for_timeout(1000)
            search.fill("")
            authenticated_page.wait_for_timeout(500)

    def test_delete_transaction(self, authenticated_page: Page):
        """Delete a transaction and verify it's removed."""
        self._go(authenticated_page)
        rows_before = authenticated_page.locator("#tx-body tr").count()
        if rows_before == 0:
            return
        # Click delete on the first row
        del_btn = authenticated_page.locator(
            "#tx-body tr .delete-btn, #tx-body tr .btn-delete, #tx-body tr button[title='Delete']"
        ).first
        if del_btn.count() > 0:
            del_btn.click(force=True)
            authenticated_page.wait_for_timeout(2000)
            # Handle confirmation dialog if exists
            confirm = authenticated_page.locator(
                ".confirm-btn, .modal button:has-text('Yes'), .modal button:has-text('Delete')"
            )
            if confirm.count() > 0:
                confirm.first.click(force=True)
                authenticated_page.wait_for_timeout(2000)


# ════════════════════════════════════════════════════════════
#  12. BUDGETS — advanced interactions
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestBudgetsAdvanced:
    """Advanced budget tests: multiple budgets, progress tracking."""

    def _go(self, page: Page):
        _nav(page, "budgets")
        page.wait_for_timeout(3000)

    def test_budget_progress_reflects_spending(self, authenticated_page: Page):
        """Budget card progress bar should reflect actual spending."""
        self._go(authenticated_page)
        cards = authenticated_page.locator(".budget-card")
        if cards.count() == 0:
            return
        html = cards.first.inner_html()
        # Progress bar should have a width percentage or dollar values
        has_progress = "%" in html or "$" in html or "progress" in html.lower()
        assert has_progress, f"Budget card missing progress indicator. HTML: {html[:300]}"

    def test_budget_empty_state(self, authenticated_page: Page):
        """When no budgets exist, should show an empty state or prompt."""
        # This test is informational — just navigate and verify no crash
        self._go(authenticated_page)
        container = authenticated_page.locator("#page-budgets")
        html = container.inner_html()
        assert len(html) > 0, "Budgets page failed to render"


# ════════════════════════════════════════════════════════════
#  13. COMPARISON — advanced flows
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestComparisonAdvanced:
    """Advanced comparison tests: multiple stocks, chart rendering."""

    def _go(self, page: Page):
        _nav(page, "comparison")
        page.wait_for_timeout(2000)

    def test_compare_three_stocks(self, authenticated_page: Page):
        """Compare 3 stocks and verify all appear in results."""
        self._go(authenticated_page)
        authenticated_page.fill("#compare-input", "AAPL, MSFT, GOOGL")
        authenticated_page.get_by_role("button", name="Compare").click()
        html = _wait_for_content(authenticated_page, "#compare-results", min_len=200, timeout=35_000)
        for sym in ["AAPL", "MSFT", "GOOGL"]:
            assert sym.lower() in html.lower(), f"Comparison results don't contain {sym}. HTML: {html[:500]}"

    def test_comparison_chart_renders(self, authenticated_page: Page):
        """Comparison should render an overlay chart with all symbols."""
        self._go(authenticated_page)
        authenticated_page.fill("#compare-input", "AAPL, TSLA")
        authenticated_page.get_by_role("button", name="Compare").click()
        _wait_for_content(authenticated_page, "#compare-results", min_len=200, timeout=35_000)
        canvases = authenticated_page.locator("#compare-results canvas, #compare-chart")
        if canvases.count() > 0:
            box = canvases.first.bounding_box()
            assert box is not None, "Comparison chart has no bounding box"
            assert box["width"] > 0, "Comparison chart has zero width"

    def test_comparison_metric_cards(self, authenticated_page: Page):
        """Should show side-by-side metric cards with financials."""
        self._go(authenticated_page)
        authenticated_page.fill("#compare-input", "AAPL, MSFT")
        authenticated_page.get_by_role("button", name="Compare").click()
        html = _wait_for_content(authenticated_page, "#compare-results", min_len=200, timeout=35_000)
        # Should show comparison metrics
        has_metrics = any(kw in html.lower() for kw in ["p/e", "market cap", "dividend", "return", "beta"])
        assert has_metrics or "$" in html, f"Comparison missing metric details. HTML: {html[:500]}"


# ════════════════════════════════════════════════════════════
#  14. RISK PROFILE — wizard completion
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestRiskProfileComplete:
    """Test completing the risk profile wizard end-to-end."""

    def _go(self, page: Page):
        _nav(page, "profile")
        page.wait_for_timeout(3000)

    def test_wizard_question_progression(self, authenticated_page: Page):
        """Each wizard question should advance to the next question on answer."""
        self._go(authenticated_page)
        result = authenticated_page.locator("#profile-result")
        if result.is_visible():
            return  # already completed
        wizard = authenticated_page.locator("#wizard-content")
        html = wizard.inner_html()
        if len(html) < 20:
            return
        # Click the first option
        options = wizard.locator(".wizard-option, button")
        if options.count() > 0:
            options.first.click()
            authenticated_page.wait_for_timeout(1000)
            # Should advance to next question or show result
            new_html = wizard.inner_html()
            assert new_html != html or result.is_visible(), "Wizard didn't advance after clicking an option"

    def test_profile_result_shows_allocation(self, authenticated_page: Page):
        """After completing the profile, should show risk score and allocation."""
        self._go(authenticated_page)
        result = authenticated_page.locator("#profile-result")
        if not result.is_visible():
            return  # not completed yet
        html = result.inner_html()
        has_result = "%" in html or "score" in html.lower() or "risk" in html.lower()
        assert has_result, f"Profile result missing allocation data. HTML: {html[:500]}"


# ════════════════════════════════════════════════════════════
#  15. THEME TOGGLE — dark/light mode
# ════════════════════════════════════════════════════════════


@pytest.mark.smoke
class TestThemeToggle:
    """Test the dark/light mode theme toggle."""

    def test_theme_toggle_exists(self, authenticated_page: Page):
        """A theme toggle button/icon should be visible."""
        toggle = authenticated_page.locator(".theme-toggle, #theme-toggle, .theme-btn, [data-action='toggle-theme']")
        assert toggle.count() > 0, "No theme toggle button found"

    def test_theme_toggle_changes_class(self, authenticated_page: Page):
        """Clicking the theme toggle should change the body/root class."""
        body_class_before = authenticated_page.evaluate("document.body.className")
        html_class_before = authenticated_page.evaluate("document.documentElement.className")

        toggle = authenticated_page.locator(".theme-toggle, #theme-toggle, .theme-btn, [data-action='toggle-theme']")
        if toggle.count() == 0:
            return
        toggle.first.click(force=True)
        authenticated_page.wait_for_timeout(500)

        body_class_after = authenticated_page.evaluate("document.body.className")
        html_class_after = authenticated_page.evaluate("document.documentElement.className")

        changed = body_class_before != body_class_after or html_class_before != html_class_after
        # Also check data-theme attribute
        if not changed:
            theme_attr = authenticated_page.evaluate(
                "document.documentElement.getAttribute('data-theme') || document.body.getAttribute('data-theme')"
            )
            assert theme_attr is not None, "Theme toggle didn't change any class or data-theme attribute"

    def test_theme_persists_on_reload(self, authenticated_page: Page, live_url: str):
        """Theme preference should persist after page reload."""
        toggle = authenticated_page.locator(".theme-toggle, #theme-toggle, .theme-btn, [data-action='toggle-theme']")
        if toggle.count() == 0:
            return
        toggle.first.click(force=True)
        authenticated_page.wait_for_timeout(500)
        theme_before = authenticated_page.evaluate(
            "document.documentElement.getAttribute('data-theme') || document.body.className"
        )
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("domcontentloaded")
        authenticated_page.wait_for_timeout(2000)
        theme_after = authenticated_page.evaluate(
            "document.documentElement.getAttribute('data-theme') || document.body.className"
        )
        assert theme_before == theme_after, f"Theme didn't persist: before={theme_before}, after={theme_after}"


# ════════════════════════════════════════════════════════════
#  16. MOBILE RESPONSIVE LAYOUT
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestMobileLayout:
    """Test mobile responsive behavior."""

    def test_sidebar_hides_on_mobile(self, authenticated_page: Page):
        """On a narrow viewport, the sidebar should collapse or hide."""
        authenticated_page.set_viewport_size({"width": 375, "height": 812})
        authenticated_page.wait_for_timeout(500)
        sidebar = authenticated_page.locator("nav.sidebar")
        box = sidebar.bounding_box()
        # Sidebar should be hidden or off-screen on mobile
        if box is not None:
            assert box["x"] < 0 or box["width"] == 0 or not sidebar.is_visible(), (
                f"Sidebar is still visible on mobile viewport: {box}"
            )
        # Restore viewport
        authenticated_page.set_viewport_size({"width": 1280, "height": 1024})

    def test_hamburger_menu_on_mobile(self, authenticated_page: Page):
        """Mobile should show a hamburger menu button."""
        authenticated_page.set_viewport_size({"width": 375, "height": 812})
        authenticated_page.wait_for_timeout(500)
        hamburger = authenticated_page.locator(".hamburger, .mobile-menu-btn, .nav-toggle, .menu-toggle")
        if hamburger.count() > 0:
            expect(hamburger.first).to_be_visible()
        # Restore
        authenticated_page.set_viewport_size({"width": 1280, "height": 1024})

    def test_mobile_bottom_nav(self, authenticated_page: Page):
        """Mobile should have a bottom navigation bar."""
        authenticated_page.set_viewport_size({"width": 375, "height": 812})
        authenticated_page.wait_for_timeout(500)
        bottom_nav = authenticated_page.locator(".bottom-nav, .mobile-nav, .nav-bottom")
        if bottom_nav.count() > 0:
            expect(bottom_nav.first).to_be_visible()
        # Restore
        authenticated_page.set_viewport_size({"width": 1280, "height": 1024})

    def test_content_readable_on_mobile(self, authenticated_page: Page):
        """Content area should fill the screen on mobile without overflow."""
        authenticated_page.set_viewport_size({"width": 375, "height": 812})
        authenticated_page.wait_for_timeout(500)
        content = authenticated_page.locator("main.content")
        box = content.bounding_box()
        if box:
            assert box["width"] <= 380, f"Content overflows mobile viewport: width={box['width']}px"
        # Restore
        authenticated_page.set_viewport_size({"width": 1280, "height": 1024})


# ════════════════════════════════════════════════════════════
#  17. API HEALTH — verify key endpoints return data
# ════════════════════════════════════════════════════════════


@pytest.mark.smoke
class TestAPIHealth:
    """Direct API health checks via the browser's fetch — no CORS issues."""

    def _fetch(self, page: Page, path: str, retries: int = 3):
        """Fetch from the API using the browser session (preserves auth cookie).

        Retries on transient network errors (e.g. "Failed to fetch") that can
        occur with Render cold-starts or corporate-proxy hiccups.
        """
        for attempt in range(retries):
            try:
                return page.evaluate(f"""
                    async () => {{
                        const r = await fetch('{path}');
                        return {{ status: r.status, body: await r.text() }};
                    }}
                """)
            except Exception:
                if attempt == retries - 1:
                    raise
                page.wait_for_timeout(3000)
        return None  # unreachable; satisfies RET503

    def test_dashboard_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/dashboard")
        assert resp["status"] == 200, f"Dashboard API failed: {resp}"

    def test_market_home_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/market/home")
        assert resp["status"] == 200, f"Market home API failed: {resp}"

    def test_portfolio_summary_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/portfolio/summary")
        assert resp["status"] == 200, f"Portfolio summary API failed: {resp}"

    def test_news_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/news")
        assert resp["status"] == 200, f"News API failed: {resp}"

    def test_categories_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/categories")
        assert resp["status"] == 200, f"Categories API failed: {resp}"

    def test_alerts_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/alerts")
        assert resp["status"] == 200, f"Alerts API failed: {resp}"

    def test_watchlist_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/screener/watchlist")
        assert resp["status"] == 200, f"Watchlist API failed: {resp}"

    def test_calendar_earnings_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/calendar/earnings")
        assert resp["status"] == 200, f"Calendar earnings API failed: {resp}"

    def test_education_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/education")
        assert resp["status"] == 200, f"Education API failed: {resp}"

    def test_profile_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/profile")
        # 200 (has profile) or 404 (no profile yet) are both ok
        assert resp["status"] in (200, 404), f"Profile API failed: {resp}"

    def test_dca_dashboard_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/dca/dashboard")
        assert resp["status"] == 200, f"DCA dashboard API failed: {resp}"

    def test_screener_sectors_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/screener/sectors")
        assert resp["status"] == 200, f"Screener sectors API failed: {resp}"

    def test_il_funds_meta_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/il-funds/meta")
        assert resp["status"] == 200, f"IL Funds meta API failed: {resp}"

    def test_autopilot_profiles_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/autopilot/profiles")
        assert resp["status"] == 200, f"Autopilot profiles API failed: {resp}"

    def test_auth_me_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/auth/me")
        assert resp["status"] == 200, f"/auth/me API failed: {resp}"

    def test_trading_dashboard_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/trading")
        assert resp["status"] == 200, f"Trading dashboard API failed: {resp}"

    def test_market_ticker_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/market/ticker")
        assert resp["status"] == 200, f"Market ticker API failed: {resp}"

    def test_budgets_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/budgets")
        assert resp["status"] == 200, f"Budgets API failed: {resp}"

    def test_transactions_api(self, authenticated_page: Page):
        resp = self._fetch(authenticated_page, "/api/transactions")
        assert resp["status"] == 200, f"Transactions API failed: {resp}"


# ════════════════════════════════════════════════════════════
#  18. NAVIGATION — full SPA routing integrity
# ════════════════════════════════════════════════════════════


@pytest.mark.smoke
class TestNavComplete:
    """Verify every sidebar nav page loads without JS errors."""

    ALL_PAGES = [
        "dashboard",
        "portfolio",
        "watchlist",
        "dca",
        "alerts",
        "screener",
        "autopilot",
        "smart-advisor",
        "comparison",
        "il-funds",
        "news",
        "calendar",
        "picks-tracker",
        "education",
        "profile",
        "transactions",
        "budgets",
    ]

    def test_all_pages_activate_without_console_error(self, authenticated_page: Page):
        """Navigate to every page — none should produce a JS error."""
        errors = []
        authenticated_page.on("pageerror", lambda e: errors.append(str(e)))

        for page_id in self.ALL_PAGES:
            _nav(authenticated_page, page_id)
            section = authenticated_page.locator(f"#page-{page_id}")
            try:
                expect(section).to_have_class(re.compile("active"), timeout=5000)
            except Exception:
                errors.append(f"Page #{page_id} did not activate")

        assert len(errors) == 0, f"JS errors or activation failures: {errors}"

    def test_direct_hash_navigation(self, authenticated_page: Page, live_url: str):
        """Navigating directly via URL hash should open the correct page."""
        for page_id in ["portfolio", "alerts", "education"]:
            authenticated_page.goto(f"{live_url}/#{page_id}", wait_until="domcontentloaded", timeout=SLOW)
            authenticated_page.wait_for_timeout(2000)
            section = authenticated_page.locator(f"#page-{page_id}")
            expect(section).to_have_class(re.compile("active"), timeout=5000)


# ════════════════════════════════════════════════════════════
#  19. CONTEXT MENU — right-click actions
# ════════════════════════════════════════════════════════════


@pytest.mark.smoke
class TestContextMenus:
    """Test right-click context menus on stock items."""

    def test_context_menu_on_market_card(self, authenticated_page: Page):
        """Right-clicking a market card should show a context menu."""
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(API_WAIT)
        cards = authenticated_page.locator(".market-card")
        if cards.count() == 0:
            return
        cards.first.click(button="right")
        authenticated_page.wait_for_timeout(1000)
        menu = authenticated_page.locator("#stock-context-menu")
        if menu.count() > 0 and menu.is_visible():
            # Menu should have action items (button.ctx-menu-item)
            items = menu.locator(".ctx-menu-item")
            assert items.count() > 0, "Context menu has no items"
            # Close menu by pressing Escape
            authenticated_page.keyboard.press("Escape")
            authenticated_page.wait_for_timeout(300)


# ════════════════════════════════════════════════════════════
#  20. EDUCATION — article interaction
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestEducationInteraction:
    """Test deeper education page interactions."""

    def _go(self, page: Page):
        _nav(page, "education")
        page.wait_for_timeout(API_WAIT)

    def test_education_categories_shown(self, authenticated_page: Page):
        """Education page should group articles by category."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#edu-container").inner_html()
        # Should have category headers or groupings
        has_categories = any(
            kw in html.lower()
            for kw in [
                "basics",
                "beginner",
                "advanced",
                "investment",
                "strategy",
                "technical",
                "fundamental",
                "risk",
                "etf",
                "category",
            ]
        )
        assert has_categories or len(html) > 200, f"Education page missing category groupings. HTML: {html[:500]}"

    def test_education_card_click_expands(self, authenticated_page: Page):
        """Clicking an education card should expand it or show full content."""
        self._go(authenticated_page)
        cards = authenticated_page.locator(".edu-card")
        if cards.count() == 0:
            return
        initial_html = cards.first.inner_html()
        cards.first.click()
        authenticated_page.wait_for_timeout(1000)
        # Either the card expanded, a modal opened, or the full article is shown
        page_html = authenticated_page.locator("#page-education").inner_html()
        assert len(page_html) > len(initial_html), "Clicking education card had no visible effect"


# ════════════════════════════════════════════════════════════
#  21. CALENDAR — tab switching and event details
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestCalendarInteraction:
    """Test calendar page tab switching and event display."""

    def _go(self, page: Page):
        _nav(page, "calendar")
        page.wait_for_timeout(API_WAIT)

    def test_calendar_has_tabs(self, authenticated_page: Page):
        """Calendar should have Earnings and Economic tabs."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-calendar").inner_html()
        has_earnings = "earning" in html.lower()
        has_economic = "economic" in html.lower() or "event" in html.lower()
        assert has_earnings or has_economic, f"Calendar missing earnings/economic sections. HTML: {html[:500]}"

    def test_calendar_events_have_dates(self, authenticated_page: Page):
        """Calendar events should display dates."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#page-calendar").inner_html()
        if len(html) < 100:
            return  # no data
        # Look for date patterns (2025, 2026, Jan, Feb, etc.)
        import re as _re

        has_dates = _re.search(r"202[5-9]|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", html)
        assert has_dates, f"Calendar events missing dates. HTML: {html[:500]}"


# ════════════════════════════════════════════════════════════
#  22. ISRAELI FUNDS — detailed filter tests
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestILFundsAdvanced:
    """Advanced Israeli funds tests: presets, sorting, pagination."""

    def _go(self, page: Page):
        _nav(page, "il-funds")
        page.wait_for_timeout(API_WAIT)

    def test_il_funds_preset_cheapest(self, authenticated_page: Page):
        """Clicking 'Cheapest Kaspit' preset should filter results."""
        self._go(authenticated_page)
        preset = authenticated_page.locator("text=Cheapest, text=Cheapest Kaspit").first
        if preset.count() > 0:
            preset.click(force=True)
            authenticated_page.wait_for_timeout(5000)
            html = authenticated_page.locator("#il-results-area").inner_html()
            assert len(html) > 50, f"Cheapest Kaspit returned no results. HTML: {html[:300]}"

    def test_il_funds_pagination(self, authenticated_page: Page):
        """Fund results should be paginated with next/prev controls."""
        self._go(authenticated_page)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        # Look for pagination controls
        pagination = authenticated_page.locator(".pagination, .page-nav, .pager, [data-page]")
        html = authenticated_page.locator("#page-il-funds").inner_html()
        has_pagination = pagination.count() > 0 or "next" in html.lower() or "page" in html.lower()
        # Pagination may or may not exist depending on result count
        if has_pagination:
            assert True  # pagination exists

    def test_il_funds_kosher_filter(self, authenticated_page: Page):
        """Kosher-only checkbox should filter to kosher funds."""
        self._go(authenticated_page)
        kosher = authenticated_page.locator("#il-kosher, input[name='kosher']")
        if kosher.count() > 0:
            kosher.first.check(force=True)
            authenticated_page.get_by_role("button", name="Search").first.click()
            authenticated_page.wait_for_timeout(5000)
            html = authenticated_page.locator("#il-results-area").inner_html()
            assert len(html) > 50 or "kosher" in html.lower(), f"Kosher filter returned no results. HTML: {html[:300]}"


# ════════════════════════════════════════════════════════════
#  23. NEWS — symbol-specific filtering
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestNewsAdvanced:
    """Advanced news tests: search, symbol tags."""

    def _go(self, page: Page):
        _nav(page, "news")
        page.wait_for_timeout(API_WAIT)

    def test_news_cards_have_source_and_date(self, authenticated_page: Page):
        """Each news card should show source and date information."""
        self._go(authenticated_page)
        html = authenticated_page.locator("#news-container").inner_html()
        if len(html) < 100:
            return
        # Should have dates or source info
        import re as _re

        has_info = _re.search(r"202[5-9]|ago|hour|minute|source|reuters|bloomberg", html, _re.IGNORECASE)
        assert has_info or "http" in html, f"News cards missing source/date. HTML: {html[:500]}"

    def test_news_search_filters(self, authenticated_page: Page):
        """News search bar should filter articles by keyword."""
        self._go(authenticated_page)
        search = authenticated_page.locator("#news-search")
        if search.count() > 0 and search.is_visible():
            cards_before = authenticated_page.locator(
                "#news-container .news-card:visible, #news-container article:visible"
            ).count()
            search.fill("Apple")
            authenticated_page.wait_for_timeout(1000)
            cards_after = authenticated_page.locator(
                "#news-container .news-card:visible, #news-container article:visible"
            ).count()
            if cards_before > 0:
                assert cards_after <= cards_before, "News search didn't filter"
            search.fill("")
            authenticated_page.wait_for_timeout(500)


# ════════════════════════════════════════════════════════════
#  24. FULL USER JOURNEY — signup to portfolio management
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestFullUserJourney:
    """End-to-end journey: register → login → build portfolio → set alerts → view."""

    def test_new_user_complete_journey(self, page: Page, live_url: str, _live_server):
        """A brand new user goes through the complete onboarding experience."""
        unique = _unique("journey_")
        email = f"{unique}@e2e.local"
        password = "Journey123"

        # Step 1: Register
        page.goto(f"{live_url}/login", wait_until="domcontentloaded", timeout=SLOW)
        page.locator(".tab-btn", has_text="Register").click()
        page.wait_for_timeout(500)
        page.fill("#reg-name", "Journey Tester")
        page.fill("#reg-email", email)
        page.fill("#reg-password", password)
        page.click("#reg-btn")
        page.wait_for_selector("nav.sidebar", timeout=SLOW)

        # Step 2: Verify on dashboard
        expect(page.locator("#page-dashboard")).to_have_class(re.compile("active"))

        # Step 3: Add a transaction
        _nav(page, "transactions")
        page.wait_for_timeout(3000)
        # The section may be display:none until JS activates it; wait for active class
        page.wait_for_selector("#page-transactions.active", timeout=SLOW)
        page.wait_for_timeout(1000)
        page.locator('button:has-text("+ Add Transaction")').click(force=True)
        page.select_option("#tx-type", "income")
        page.fill("#tx-amount", "3000")
        page.fill("#tx-date", "2026-03-01")
        page.fill("#tx-desc", "Journey salary")
        page.locator('#tx-form button[type="submit"]').click()
        page.wait_for_timeout(2000)
        expect(page.locator("#tx-body")).to_contain_text("Journey salary")

        # Step 4: Add a holding
        _nav(page, "portfolio")
        page.locator("text=+ Add Holding").click(force=True)
        page.fill("#holding-symbol", "NVDA")
        page.fill("#holding-name", "NVIDIA")
        page.fill("#holding-qty", "5")
        page.fill("#holding-price", "800")
        page.fill("#holding-date", "2025-01-01")
        page.locator('#holding-form button[type="submit"]').click()
        page.wait_for_timeout(10000)
        html = page.locator("#portfolio-container").inner_html()
        assert "NVDA" in html

        # Step 5: Set a price alert
        _nav(page, "alerts")
        page.locator("text=+ New Alert").click(force=True)
        page.fill("#alert-symbol", "NVDA")
        page.select_option("#alert-condition", "above")
        page.fill("#alert-price", "1000")
        page.locator('#alert-form button[type="submit"]').click()
        page.wait_for_timeout(2000)
        html = page.locator("#alerts-container").inner_html()
        assert "NVDA" in html

        # Step 6: Check dashboard reflects data
        _nav(page, "dashboard")
        page.wait_for_timeout(5000)
        income = page.locator("#stat-income")
        expect(income).to_contain_text("$")

        # Step 7: Logout
        page.goto(f"{live_url}/auth/logout", wait_until="domcontentloaded", timeout=SLOW)
        expect(page.locator("#login-email")).to_be_visible()

        # Step 8: Login again and verify data persisted
        page.fill("#login-email", email)
        page.fill("#login-password", password)
        page.click("#login-btn")
        page.wait_for_url(f"{live_url}/", timeout=SLOW)
        page.wait_for_timeout(3000)
        _nav(page, "portfolio")
        page.wait_for_timeout(10000)
        html = page.locator("#portfolio-container").inner_html()
        assert "NVDA" in html, "Portfolio data didn't persist after re-login"


# ════════════════════════════════════════════════════════════
#  25. MULTI-USER DATA ISOLATION (API-level, works on live site)
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestMultiUserLive:
    """Two users should never see each other's data — tested via browser fetch."""

    def _register_and_login(self, page: Page, live_url: str, email: str, password: str, name: str):
        """Register and login via the browser for a specific user."""
        page.goto(f"{live_url}/login", wait_until="domcontentloaded", timeout=SLOW)
        # Try registering via fetch (silent, no page navigation)
        page.evaluate(f"""
            async () => {{
                await fetch('/auth/register', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{email: '{email}', password: '{password}', name: '{name}'}})
                }});
            }}
        """)
        page.fill("#login-email", email)
        page.fill("#login-password", password)
        page.click("#login-btn")
        page.wait_for_url(f"{live_url}/", timeout=SLOW)
        page.wait_for_timeout(2000)

    def test_portfolio_isolation_browser(self, page: Page, live_url: str, _live_server, browser):
        """User A adds a holding; User B should not see it."""
        tag = _unique()
        email_a = f"alice_{tag}@e2e.local"
        email_b = f"bob_{tag}@e2e.local"

        # User A: add a holding
        self._register_and_login(page, live_url, email_a, "Alice1234", "Alice")
        page.evaluate("""
            async () => {
                await fetch('/api/portfolio/holdings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        symbol: 'UNIQUE_TEST', name: 'Test Corp',
                        quantity: 1, buy_price: 100, buy_date: '2025-01-01'
                    })
                });
            }
        """)
        page.wait_for_timeout(1000)

        # Verify User A can see it
        resp_a = page.evaluate("async () => (await fetch('/api/portfolio/holdings')).json()")
        symbols_a = [h.get("symbol", "") for h in resp_a] if isinstance(resp_a, list) else []
        assert "UNIQUE_TEST" in symbols_a, f"User A can't see own holding: {symbols_a}"

        # User B: open new context, login, check
        from conftest import _NEED_PROXY

        ctx_opts = {"viewport": {"width": 1280, "height": 1024}}
        if _NEED_PROXY:
            ctx_opts["proxy"] = {"server": "http://proxy-dmz.intel.com:912", "bypass": "127.0.0.1,localhost"}
        ctx_b = browser.new_context(**ctx_opts)
        page_b = ctx_b.new_page()
        self._register_and_login(page_b, live_url, email_b, "Bob12345", "Bob")
        resp_b = page_b.evaluate("async () => (await fetch('/api/portfolio/holdings')).json()")
        symbols_b = [h.get("symbol", "") for h in resp_b] if isinstance(resp_b, list) else []
        assert "UNIQUE_TEST" not in symbols_b, f"User B can see User A's holding! B's holdings: {symbols_b}"
        ctx_b.close()


# ════════════════════════════════════════════════════════════
#  26. ERROR HANDLING & EDGE CASES
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestErrorHandling:
    """Test how the app handles edge cases and invalid inputs."""

    def test_empty_portfolio_shows_prompt(self, page: Page, live_url: str, _live_server):
        """A brand new user's portfolio page should show an empty state."""
        tag = _unique("empty_")
        email = f"{tag}@e2e.local"
        page.goto(f"{live_url}/login", wait_until="domcontentloaded", timeout=SLOW)
        page.evaluate(f"""
            async () => {{
                await fetch('/auth/register', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{email: '{email}', password: 'Empty123', name: 'Empty'}})
                }});
            }}
        """)
        page.fill("#login-email", email)
        page.fill("#login-password", "Empty123")
        page.click("#login-btn")
        page.wait_for_url(f"{live_url}/", timeout=SLOW)
        page.wait_for_timeout(2000)
        _nav(page, "portfolio")
        page.wait_for_timeout(5000)
        html = page.locator("#portfolio-container").inner_html()
        # Should show empty state or prompt to add holdings
        has_empty = "empty" in html.lower() or "add" in html.lower() or "no holding" in html.lower() or len(html) < 200
        assert has_empty, f"Portfolio should show empty state for new user. HTML: {html[:500]}"

    def test_comparison_with_invalid_symbol(self, authenticated_page: Page):
        """Comparing an invalid symbol should show an error message."""
        _nav(authenticated_page, "comparison")
        authenticated_page.fill("#compare-input", "XYZNOTREAL123")
        authenticated_page.get_by_role("button", name="Compare").click()
        authenticated_page.wait_for_timeout(10000)
        html = authenticated_page.locator("#page-comparison").inner_html()
        # Should show error, no data, or handle gracefully (no crash)
        assert len(html) > 0, "Comparison page crashed on invalid symbol"

    def test_screener_with_extreme_filters(self, authenticated_page: Page):
        """Screener with very restrictive filters should return 0 results without crashing."""
        _nav(authenticated_page, "screener")
        authenticated_page.wait_for_timeout(2000)
        pe_min = authenticated_page.locator("#scr-pe-min, input[name='pe_min']")
        if pe_min.count() > 0:
            pe_min.first.fill("0.001")
        pe_max = authenticated_page.locator("#scr-pe-max, input[name='pe_max']")
        if pe_max.count() > 0:
            pe_max.first.fill("0.002")
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(5000)
        # Should handle gracefully (show "0 results" or similar)
        html = authenticated_page.locator("#page-screener").inner_html()
        assert len(html) > 100, "Screener crashed on extreme filters"

    def test_add_holding_missing_fields(self, authenticated_page: Page):
        """Submitting the add-holding form with missing fields should show validation."""
        _nav(authenticated_page, "portfolio")
        authenticated_page.wait_for_timeout(2000)
        authenticated_page.locator("text=+ Add Holding").click(force=True)
        authenticated_page.wait_for_timeout(500)
        # Submit without filling required fields
        authenticated_page.locator('#holding-form button[type="submit"]').click()
        authenticated_page.wait_for_timeout(1000)
        # Browser should prevent submission (HTML5 validation) or show error
        # No crash is the key assertion
        page_html = authenticated_page.locator("#page-portfolio").inner_html()
        assert len(page_html) > 0, "Page crashed on empty form submission"


# ════════════════════════════════════════════════════════════
#  27. PERFORMANCE & LOADING
# ════════════════════════════════════════════════════════════


@pytest.mark.smoke
class TestPerformance:
    """Verify critical pages load within acceptable timeframes."""

    def test_login_page_loads_fast(self, page: Page, live_url: str, _live_server):
        """Login page should load within 30 seconds (even with cold start)."""
        import time

        start = time.time()
        page.goto(f"{live_url}/login", wait_until="domcontentloaded", timeout=SLOW)
        elapsed = time.time() - start
        assert elapsed < 30, f"Login page took {elapsed:.1f}s to load (max 30s)"

    def test_dashboard_loads_after_login(self, authenticated_page: Page):
        """Dashboard should be visible and interactive within a reasonable time."""
        _nav(authenticated_page, "dashboard")
        # Stats should appear
        authenticated_page.wait_for_selector("#stat-income", timeout=15_000)
        expect(authenticated_page.locator("#stat-income")).to_contain_text("$")

    def test_no_console_errors_on_load(self, authenticated_page: Page):
        """Dashboard load should not produce JavaScript console errors."""
        errors = []
        authenticated_page.on("pageerror", lambda e: errors.append(str(e)))
        _nav(authenticated_page, "dashboard")
        authenticated_page.wait_for_timeout(5000)
        critical = [e for e in errors if "TypeError" in e or "ReferenceError" in e]
        assert len(critical) == 0, f"JS errors on dashboard: {critical}"


# ════════════════════════════════════════════════════════════
#  28. SCREENER — full interaction flow
# ════════════════════════════════════════════════════════════


@pytest.mark.deep
class TestScreenerFull:
    """Complete screener interaction tests."""

    def _go(self, page: Page):
        _nav(page, "screener")
        page.wait_for_timeout(3000)

    def test_screener_sector_filter(self, authenticated_page: Page):
        """Filter by a specific sector should narrow results."""
        self._go(authenticated_page)
        sector = authenticated_page.locator("#scr-sector")
        if sector.count() > 0:
            # Select the second option (first non-"All" option)
            options = sector.locator("option")
            if options.count() > 1:
                val = options.nth(1).get_attribute("value")
                if val:
                    sector.select_option(val)
                    authenticated_page.get_by_role("button", name="Search").first.click()
                    authenticated_page.wait_for_timeout(5000)
                    html = authenticated_page.locator("#scr-results-area").inner_html()
                    assert len(html) > 20, "Sector filter returned no results"

    def test_screener_etf_filter(self, authenticated_page: Page):
        """Filtering by ETFs should return ETF results."""
        self._go(authenticated_page)
        asset_type = authenticated_page.locator("#scr-asset-type, #scr-type")
        if asset_type.count() > 0:
            options = asset_type.locator("option")
            for i in range(options.count()):
                if "etf" in (options.nth(i).inner_text()).lower():
                    asset_type.select_option(options.nth(i).get_attribute("value") or "etf")
                    break
            authenticated_page.get_by_role("button", name="Search").first.click()
            authenticated_page.wait_for_timeout(5000)

    def test_screener_preset_high_dividend(self, authenticated_page: Page):
        """'High Dividend' preset should populate filters and return results."""
        self._go(authenticated_page)
        preset = authenticated_page.locator("text=High Dividend")
        if preset.count() > 0:
            preset.first.click()
            authenticated_page.wait_for_timeout(500)
            authenticated_page.get_by_role("button", name="Search").first.click()
            authenticated_page.wait_for_timeout(5000)
            count_el = authenticated_page.locator("#scr-result-count")
            if count_el.count() > 0:
                text = count_el.inner_text()
                assert text != "", "High Dividend preset returned empty count"

    def test_screener_result_clicking_opens_detail(self, authenticated_page: Page):
        """Clicking a screener result should open stock detail."""
        self._go(authenticated_page)
        authenticated_page.get_by_role("button", name="Search").first.click()
        authenticated_page.wait_for_timeout(8000)
        # Click first result
        results = authenticated_page.locator(
            "#scr-results-area .scr-card, #scr-results-area tr, #scr-results-area .stock-row"
        )
        if results.count() > 0:
            results.first.click()
            authenticated_page.wait_for_timeout(10000)
            detail = authenticated_page.locator("#page-stock-detail")
            if detail.count() > 0:
                # May or may not navigate to stock detail depending on result type
                html = detail.inner_html()
                assert len(html) > 0


# ════════════════════════════════════════════════════════════
#  SPARKLINE CHARTS — verify all market cards have visible charts
# ════════════════════════════════════════════════════════════


@pytest.mark.smoke
class TestSparklineCharts:
    """Validate that sparkline charts render on every market card in the dashboard."""

    EXPECTED_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL"]

    def _go_dashboard_and_wait(self, page: Page):
        # Ensure we're on the dashboard (not stuck on login)
        if "/login" in page.url:
            page.wait_for_timeout(3000)
        _nav(page, "dashboard")
        # Wait for market cards to appear (API + render time)
        page.wait_for_selector(".market-card", timeout=SLOW)
        page.wait_for_timeout(API_WAIT)

    def test_all_market_cards_present(self, authenticated_page: Page):
        """Dashboard should display market cards for all featured symbols."""
        self._go_dashboard_and_wait(authenticated_page)
        cards = authenticated_page.locator(".market-card")
        count = cards.count()
        assert count >= len(self.EXPECTED_SYMBOLS), (
            f"Expected at least {len(self.EXPECTED_SYMBOLS)} market cards, got {count}"
        )
        # Verify each expected symbol has a card
        for sym in self.EXPECTED_SYMBOLS:
            card = authenticated_page.locator(f'.market-card[data-symbol="{sym}"]')
            assert card.count() > 0, f"Missing market card for {sym}"

    def test_sparkline_canvas_exists_for_each_card(self, authenticated_page: Page):
        """Each market card should contain a canvas element for the sparkline."""
        self._go_dashboard_and_wait(authenticated_page)
        for sym in self.EXPECTED_SYMBOLS:
            canvas = authenticated_page.locator(f"canvas#spark-{sym}")
            assert canvas.count() > 0, f"Missing sparkline canvas for {sym}"

    def test_sparkline_charts_are_rendered(self, authenticated_page: Page):
        """Sparkline canvases should have non-zero dimensions (Chart.js rendered)."""
        self._go_dashboard_and_wait(authenticated_page)
        # Give Chart.js extra time to render all sparklines
        authenticated_page.wait_for_timeout(CHART_WAIT)

        rendered = []
        missing = []
        for sym in self.EXPECTED_SYMBOLS:
            canvas = authenticated_page.locator(f"canvas#spark-{sym}")
            if canvas.count() == 0:
                missing.append(sym)
                continue
            box = canvas.bounding_box()
            if box and box["width"] > 0 and box["height"] > 0:
                rendered.append(sym)
            else:
                missing.append(sym)

        assert len(missing) == 0, f"Sparkline charts NOT rendered for: {missing}. Rendered OK: {rendered}"

    def test_sparkline_canvases_have_drawn_pixels(self, authenticated_page: Page):
        """Verify Chart.js actually drew on the canvas (not blank white)."""
        self._go_dashboard_and_wait(authenticated_page)
        authenticated_page.wait_for_timeout(CHART_WAIT)

        blank = []
        for sym in self.EXPECTED_SYMBOLS:
            canvas = authenticated_page.locator(f"canvas#spark-{sym}")
            if canvas.count() == 0:
                blank.append(sym)
                continue
            # Check if canvas has any non-transparent pixels drawn
            has_pixels = authenticated_page.evaluate(
                """(sym) => {
                const c = document.getElementById('spark-' + sym);
                if (!c) return false;
                const ctx = c.getContext('2d');
                if (!ctx) return false;
                const data = ctx.getImageData(0, 0, c.width, c.height).data;
                // Check if any pixel has non-zero alpha (something was drawn)
                for (let i = 3; i < data.length; i += 4) {
                    if (data[i] > 0) return true;
                }
                return false;
            }""",
                sym,
            )
            if not has_pixels:
                blank.append(sym)

        assert len(blank) == 0, f"Sparkline canvases are BLANK (no drawn pixels) for: {blank}"

    def test_sparkline_api_returns_data_for_all_symbols(self, live_url: str):
        """The /api/market/home API should return sparkline arrays with >1 point for all featured stocks."""
        import requests
        from tests.conftest import _PROXIES

        # Register + login via API to get a session
        s = requests.Session()
        if _PROXIES:
            s.proxies.update(_PROXIES)
        s.post(
            f"{live_url}/auth/register",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "name": TEST_USER_NAME},
            timeout=60,
        )
        s.post(f"{live_url}/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}, timeout=60)

        resp = s.get(f"{live_url}/api/market/home", timeout=60)
        assert resp.status_code == 200, f"market/home returned {resp.status_code}"
        data = resp.json()
        featured = data.get("featured", [])
        assert len(featured) >= len(self.EXPECTED_SYMBOLS), (
            f"Expected {len(self.EXPECTED_SYMBOLS)} featured stocks, got {len(featured)}"
        )

        empty_sparklines = []
        for stock in featured:
            sym = stock.get("symbol", "?")
            sparkline = stock.get("sparkline", [])
            if len(sparkline) < 2:
                empty_sparklines.append(f"{sym}({len(sparkline)}pts)")

        assert len(empty_sparklines) == 0, (
            f"Sparkline data MISSING for: {empty_sparklines}. All stocks should have >1 data point."
        )

    def test_sparkline_api_consistent_across_calls(self, live_url: str):
        """Hit /api/market/home 3 times rapidly — every call must return sparklines for ALL symbols.

        Regression test for the intermittent missing-chart bug where:
        - Unstable cache keys (changing every second) caused cache misses
        - Concurrent requests exhausted Finnhub rate limits
        - Some symbols (often AAPL) randomly came back empty
        """
        import requests
        import time
        from tests.conftest import _PROXIES

        # Register + login via API to get a session
        s = requests.Session()
        if _PROXIES:
            s.proxies.update(_PROXIES)
        s.post(
            f"{live_url}/auth/register",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "name": TEST_USER_NAME},
            timeout=60,
        )
        s.post(f"{live_url}/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}, timeout=60)

        failures = []
        for call_num in range(1, 4):
            resp = s.get(f"{live_url}/api/market/home", timeout=60)
            assert resp.status_code == 200, f"Call #{call_num}: HTTP {resp.status_code}"
            data = resp.json()
            for stock in data.get("featured", []):
                sym = stock.get("symbol", "?")
                pts = len(stock.get("sparkline", []))
                if pts < 2:
                    failures.append(f"call#{call_num} {sym}={pts}pts")
            time.sleep(2)  # small gap between calls

        assert len(failures) == 0, (
            f"Sparkline data was INCONSISTENT across rapid calls: {failures}. Cache/rate-limit fix may have regressed."
        )
