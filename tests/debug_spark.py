"""Quick debug script to check sparkline canvas rendering."""
import os
os.environ['NO_PROXY'] = '127.0.0.1,localhost'
os.environ['no_proxy'] = '127.0.0.1,localhost'

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        args=['--proxy-bypass-list=127.0.0.1;localhost;<-loopback>'],
    )
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 1024},
        proxy={'server': 'http://proxy-dmz.intel.com:912', 'bypass': '127.0.0.1,localhost'},
    )
    page = ctx.new_page()

    errors = []
    page.on('console', lambda msg: errors.append(f'{msg.type}: {msg.text}') if msg.type == 'error' else None)

    page.goto('http://127.0.0.1:8091/login', wait_until='domcontentloaded')
    page.fill('#access-key', 'intel2026')
    page.click('#login-btn')
    page.wait_for_url('http://127.0.0.1:8091/', timeout=15000)
    page.wait_for_timeout(6000)

    # Check canvas elements
    canvases = page.query_selector_all('canvas[id^="spark-"]')
    print(f'Found {len(canvases)} spark canvases')

    for c in canvases:
        cid = c.get_attribute('id')
        box = c.bounding_box()
        dims = c.evaluate(
            'el => ({w: el.width, h: el.height, cw: el.clientWidth, ch: el.clientHeight, '
            'pw: el.parentElement.clientWidth, ph: el.parentElement.clientHeight})'
        )
        print(f'  {cid}: boundingBox={box}, dims={dims}')

    # Check Chart.js
    chart_loaded = page.evaluate('typeof Chart !== "undefined"')
    print(f'Chart.js loaded: {chart_loaded}')

    # Check sparkCharts object
    spark_keys = page.evaluate('typeof sparkCharts !== "undefined" ? Object.keys(sparkCharts) : "not defined"')
    print(f'sparkCharts keys: {spark_keys}')

    # Check the market grid HTML
    grid_html = page.evaluate('document.getElementById("market-grid").innerHTML.substring(0, 500)')
    print(f'Market grid HTML (first 500): {grid_html}')

    # Check actual sparkline data from the API response
    spark_data = page.evaluate('''() => {
        // Try to get the chart data from sparkCharts
        const result = {};
        for (const [sym, chart] of Object.entries(sparkCharts)) {
            const data = chart.data.datasets[0].data;
            result[sym] = {len: data.length, min: Math.min(...data), max: Math.max(...data), first: data[0], last: data[data.length-1]};
        }
        return result;
    }''')
    print(f'Sparkline data ranges:')
    for sym, info in spark_data.items():
        print(f'  {sym}: {info}')

    # Check if canvas has pixel data (non-empty)
    for c in canvases[:2]:
        cid = c.get_attribute('id')
        has_pixels = c.evaluate('''el => {
            const ctx = el.getContext("2d");
            const data = ctx.getImageData(0, 0, el.width, el.height).data;
            let nonZero = 0;
            for (let i = 0; i < data.length; i += 4) {
                if (data[i] > 0 || data[i+1] > 0 || data[i+2] > 0 || data[i+3] > 0) nonZero++;
            }
            return {total: el.width * el.height, nonZero: nonZero};
        }''')
        print(f'  {cid} pixels: {has_pixels}')

    # Take screenshot of market grid
    page.locator('#market-grid').screenshot(path='tests/market_grid.png')
    print('Screenshot saved to tests/market_grid.png')

    if errors:
        print(f'Console errors ({len(errors)}):')
        for e in errors:
            print(f'  {e}')
    else:
        print('No console errors')

    browser.close()
