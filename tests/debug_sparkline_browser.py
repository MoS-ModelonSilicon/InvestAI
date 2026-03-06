"""Debug: check sparkline canvas rendering in the actual browser."""
import requests
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8091"

# Register + login via API
s = requests.Session()
s.proxies = {"http": None, "https": None}
s.trust_env = False
s.post(f"{BASE}/auth/register", json={"email": "spark-browser@e2e.local", "password": "TestPass123"})
r = s.post(f"{BASE}/auth/login", json={"email": "spark-browser@e2e.local", "password": "TestPass123"})
cookie = s.cookies.get("investai_session")
if not cookie:
    print(f"Login failed! Status: {r.status_code}, cookies: {dict(s.cookies)}")
    exit(1)
print(f"Session cookie: {cookie[:20]}...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    ctx.add_cookies([{"name": "investai_session", "value": cookie, "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()

    # Capture console messages
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

    page.goto(f"{BASE}/", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(5000)  # wait for market data to load

    # Check if market cards exist
    cards = page.query_selector_all(".market-card")
    print(f"\nMarket cards found: {len(cards)}")

    # Check if spark canvases exist
    spark_canvases = page.query_selector_all("[id^='spark-']")
    print(f"Spark canvases found: {len(spark_canvases)}")

    for canvas in spark_canvases:
        cid = canvas.get_attribute("id")
        bbox = canvas.bounding_box()
        # Check canvas dimensions and whether Chart.js drew anything
        info = page.evaluate("""(canvasId) => {
            const c = document.getElementById(canvasId);
            if (!c) return {exists: false};
            const ctx = c.getContext('2d');
            const rect = c.getBoundingClientRect();
            const w = c.width;
            const h = c.height;

            // Check if canvas has any non-transparent pixels
            let pixelCount = 0;
            try {
                const imgData = ctx.getImageData(0, 0, w, h);
                for (let i = 3; i < imgData.data.length; i += 4) {
                    if (imgData.data[i] > 0) pixelCount++;
                }
            } catch(e) {
                // Chart.js might have replaced context
            }

            // Check if Chart.js instance exists
            const chartInstance = Chart.getChart(c);
            const hasChart = !!chartInstance;
            const chartData = hasChart ? chartInstance.data.datasets[0].data.length : 0;

            return {
                exists: true,
                width: w,
                height: h,
                rectWidth: rect.width,
                rectHeight: rect.height,
                pixelCount: pixelCount,
                hasChart: hasChart,
                chartDataPoints: chartData,
                display: window.getComputedStyle(c).display,
                visibility: window.getComputedStyle(c).visibility,
                parentDisplay: window.getComputedStyle(c.parentElement).display,
                parentWidth: c.parentElement.offsetWidth,
                parentHeight: c.parentElement.offsetHeight,
            };
        }""", cid)
        print(f"  {cid}: {info}")

    # Check for JS errors
    errors = [m for m in console_msgs if "error" in m.lower() or "fail" in m.lower()]
    if errors:
        print(f"\nConsole errors: {errors[:10]}")
    else:
        print(f"\nNo console errors (total msgs: {len(console_msgs)})")

    # Check Chart.js loaded
    chart_loaded = page.evaluate("typeof Chart !== 'undefined'")
    print(f"Chart.js loaded: {chart_loaded}")

    # Check sparkCharts object
    spark_charts_info = page.evaluate("""() => {
        if (typeof sparkCharts === 'undefined') return 'sparkCharts not defined';
        const keys = Object.keys(sparkCharts);
        return {count: keys.length, symbols: keys};
    }""")
    print(f"sparkCharts: {spark_charts_info}")

    # Screenshot for visual inspection
    page.screenshot(path="tests/sparkline_debug.png", full_page=True)
    print("\nScreenshot saved to tests/sparkline_debug.png")

    browser.close()
