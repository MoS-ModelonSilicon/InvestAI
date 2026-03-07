"""Debug sparkline rendering on live Render site."""

import requests
from playwright.sync_api import sync_playwright

BASE = "https://investai-utho.onrender.com"

# Register + login via API (through proxy for remote)
s = requests.Session()
# Need proxy to reach Render from Intel network
r = s.post(f"{BASE}/auth/register", json={"email": "spark-live@e2e.local", "password": "TestPass123"}, timeout=60)
print(f"Register: {r.status_code}")
r = s.post(f"{BASE}/auth/login", json={"email": "spark-live@e2e.local", "password": "TestPass123"}, timeout=60)
print(f"Login: {r.status_code}")
cookie = s.cookies.get("investai_session")
if not cookie:
    print(f"Login failed! cookies: {dict(s.cookies)}")
    exit(1)
print(f"Session cookie: {cookie[:20]}...")

# Check API directly
print("\n=== API check ===")
r = s.get(f"{BASE}/api/market/featured", timeout=120)
print(f"Featured status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    for stock in data:
        sp = stock.get("sparkline", [])
        sym = stock.get("symbol", "?")
        print(f"  {sym}: sparkline_points={len(sp)}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    # Set proxy for network requests from browser
    domain = "investai-utho.onrender.com"
    ctx.add_cookies([{"name": "investai_session", "value": cookie, "domain": domain, "path": "/"}])
    page = ctx.new_page()

    # Capture console messages
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

    # Capture network failures
    failed_requests = []
    page.on("requestfailed", lambda req: failed_requests.append(f"{req.url} => {req.failure}"))

    print("\n=== Loading live site ===")
    page.goto(f"{BASE}/", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(10000)  # wait for market data to load

    # Check if market cards exist
    cards = page.query_selector_all(".market-card")
    print(f"Market cards found: {len(cards)}")

    # Check Chart.js loaded
    chart_loaded = page.evaluate("typeof Chart !== 'undefined'")
    print(f"Chart.js loaded: {chart_loaded}")

    # Check spark canvases
    spark_canvases = page.query_selector_all("[id^='spark-']")
    print(f"Spark canvases found: {len(spark_canvases)}")

    for canvas in spark_canvases:
        cid = canvas.get_attribute("id")
        info = page.evaluate(
            """(canvasId) => {
            const c = document.getElementById(canvasId);
            if (!c) return {exists: false};
            const rect = c.getBoundingClientRect();
            const chartInstance = (typeof Chart !== 'undefined') ? Chart.getChart(c) : null;
            const hasChart = !!chartInstance;
            const chartData = hasChart ? chartInstance.data.datasets[0].data.length : 0;
            return {
                exists: true,
                width: c.width,
                height: c.height,
                rectWidth: rect.width,
                rectHeight: rect.height,
                hasChart: hasChart,
                chartDataPoints: chartData,
                parentWidth: c.parentElement.offsetWidth,
                parentHeight: c.parentElement.offsetHeight,
            };
        }""",
            cid,
        )
        print(f"  {cid}: {info}")

    # Check for failed network requests
    if failed_requests:
        print(f"\nFailed network requests:")
        for fr in failed_requests:
            print(f"  {fr}")

    # Check console errors
    errors = [m for m in console_msgs if m.startswith("[error")]
    if errors:
        print(f"\nConsole errors:")
        for e in errors[:10]:
            print(f"  {e}")

    # sparkCharts object
    spark_info = page.evaluate("""() => {
        if (typeof sparkCharts === 'undefined') return 'sparkCharts not defined';
        return {count: Object.keys(sparkCharts).length, symbols: Object.keys(sparkCharts)};
    }""")
    print(f"\nsparkCharts: {spark_info}")

    page.screenshot(path="tests/sparkline_live_debug.png", full_page=True)
    print("\nScreenshot saved to tests/sparkline_live_debug.png")

    browser.close()
