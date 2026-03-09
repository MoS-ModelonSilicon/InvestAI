let tickerInterval = null;
let marketInterval = null;
let sparkCharts = {};
let previousPrices = {};

// ── localStorage offline-first cache for instant market rendering ──
const MARKET_CACHE_KEY = "investai_market_home";
const MARKET_CACHE_MAX_AGE = 30 * 60 * 1000; // 30 min — stale but still useful

function saveMarketCache(data) {
    try {
        localStorage.setItem(MARKET_CACHE_KEY, JSON.stringify({ ts: Date.now(), data }));
    } catch (_) { /* quota exceeded — ignore */ }
}

function loadMarketCache() {
    try {
        const raw = localStorage.getItem(MARKET_CACHE_KEY);
        if (!raw) return null;
        const { ts, data } = JSON.parse(raw);
        if (Date.now() - ts > MARKET_CACHE_MAX_AGE) {
            localStorage.removeItem(MARKET_CACHE_KEY);
            return null;
        }
        return data;
    } catch (_) { return null; }
}

async function loadTicker() {
    try {
        const data = await api.get("/api/market/ticker");
        renderTicker(data);
    } catch (e) {
        document.getElementById("ticker-strip").innerHTML =
            '<span class="ticker-loading">Loading market data...</span>';
    }
}

function renderTicker(quotes) {
    const strip = document.getElementById("ticker-strip");
    const singleSet = quotes.map((q) => {
        const up = q.change >= 0;
        const arrow = up ? "▲" : "▼";
        const cls = up ? "ticker-up" : "ticker-down";

        let flash = "";
        const prev = previousPrices[q.symbol];
        if (prev !== undefined && prev !== q.price) {
            flash = q.price > prev ? "flash-green" : "flash-red";
        }
        previousPrices[q.symbol] = q.price;

        return `<div class="ticker-item ${cls} ${flash}" data-symbol="${q.symbol}" data-stock-name="${q.symbol}" data-stock-price="${q.price}">
            <span class="ticker-symbol">${q.symbol}</span>
            <span class="ticker-price">${currSym(q.currency)}${q.price.toFixed(2)}</span>
            <span class="ticker-change">${arrow} ${Math.abs(q.change_pct).toFixed(2)}%</span>
        </div>`;
    }).join("");

    // Measure one set's width to ensure content fills the viewport
    strip.style.animation = "none";
    strip.innerHTML = singleSet;
    const oneSetWidth = strip.scrollWidth;
    const viewWidth = strip.parentElement.offsetWidth || window.innerWidth;

    // Repeat enough times so each "half" is at least as wide as the viewport
    const repeats = Math.max(1, Math.ceil(viewWidth / oneSetWidth) + 1);
    const halfContent = new Array(repeats).fill(singleSet).join("");

    // Double the half so translateX(-50%) scrolls exactly one half seamlessly
    strip.innerHTML = halfContent + halfContent;

    // Adjust speed proportionally: base 60s for 2 repeats
    const duration = 30 * repeats;
    strip.style.animation = `ticker-scroll ${duration}s linear infinite`;
}

async function loadFeaturedStocks() {
    const container = document.getElementById("market-grid");
    container.innerHTML = `<div class="market-loading"><div class="spinner"></div><span>Loading live market data...</span></div>`;

    try {
        const data = await api.get("/api/market/featured");
        renderFeaturedStocks(data);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:20px;">Unable to load market data.</p>';
    }
}

function renderFeaturedStocks(stocks) {
    const container = document.getElementById("market-grid");

    container.innerHTML = stocks.map((s) => {
        const up = s.change >= 0;
        const cls = up ? "stock-up" : "stock-down";
        const arrow = up ? "▲" : "▼";
        const sign = up ? "+" : "";
        const volFmt = s.volume > 1e6 ? (s.volume / 1e6).toFixed(1) + "M" : (s.volume / 1e3).toFixed(0) + "K";

        return `<div class="market-card ${cls}" data-symbol="${s.symbol}" data-stock-name="${s.name}" data-stock-price="${s.price}" onclick="navigateToStock('${s.symbol}')">
            <div class="market-card-top">
                <div>
                    <div class="market-card-symbol">${s.symbol}</div>
                    <div class="market-card-name">${s.name}</div>
                </div>
                <div class="market-card-price-group">
                    <div class="market-card-price">${currSym(s.currency)}${s.price.toFixed(2)}</div>
                    <div class="market-card-change ${cls}">${arrow} ${sign}${s.change.toFixed(2)} (${sign}${s.change_pct.toFixed(2)}%)</div>
                </div>
            </div>
            <div class="market-card-chart">
                <canvas id="spark-${s.symbol}" height="60"></canvas>
            </div>
            <div class="market-card-footer">
                <span data-help="day_range">H: ${currSym(s.currency)}${(s.day_high || s.price).toFixed(2)}</span>
                <span data-help="day_range">L: ${currSym(s.currency)}${(s.day_low || s.price).toFixed(2)}</span>
                <span data-help="volume">Vol: ${volFmt}</span>
            </div>
        </div>`;
    }).join("");

    stocks.forEach((s) => {
        if (s.sparkline && s.sparkline.length > 1) {
            renderSparkline(s.symbol, s.sparkline, s.change >= 0);
        }
    });
}

function renderSparkline(symbol, data, isUp) {
    const canvas = document.getElementById(`spark-${symbol}`);
    if (!canvas) return;

    // Destroy old Chart.js instance if it exists (backward compat)
    if (sparkCharts[symbol]) { sparkCharts[symbol].destroy(); sparkCharts[symbol] = null; }

    // Lightweight canvas sparkline — no Chart.js overhead
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const color = isUp ? "rgba(34, 197, 94, 1)" : "rgba(239, 68, 68, 1)";
    const bgColor = isUp ? "rgba(34, 197, 94, 0.08)" : "rgba(239, 68, 68, 0.08)";

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 2;

    ctx.beginPath();
    data.forEach((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = pad + (1 - (v - min) / range) * (h - 2 * pad);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.stroke();

    // Fill area
    const lastX = w;
    ctx.lineTo(lastX, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = bgColor;
    ctx.fill();
}

async function loadHome() {
    try {
        const data = await api.get("/api/market/home");
        renderTicker(data.ticker);
        renderFeaturedStocks(data.featured);
        saveMarketCache(data);
        // Remove stale indicator once fresh data arrives
        document.querySelectorAll(".market-stale-badge").forEach(el => el.remove());
    } catch (e) {
        loadTicker();
        loadFeaturedStocks();
    }
}

function _renderCachedMarket() {
    const cached = loadMarketCache();
    if (!cached) return false;
    try {
        if (cached.ticker) renderTicker(cached.ticker);
        if (cached.featured) renderFeaturedStocks(cached.featured);
        // Add a subtle "Updating..." badge so users know fresh data is coming
        const grid = document.getElementById("market-grid");
        if (grid && !grid.querySelector(".market-stale-badge")) {
            const badge = document.createElement("div");
            badge.className = "market-stale-badge";
            badge.textContent = "Updating…";
            grid.prepend(badge);
        }
        return true;
    } catch (_) { return false; }
}

function startMarketRefresh() {
    if (tickerInterval) clearInterval(tickerInterval);
    if (marketInterval) clearInterval(marketInterval);

    // Instant render from localStorage cache, then fetch fresh in background
    _renderCachedMarket();
    loadHome();

    marketInterval = setInterval(loadHome, 120000);
}

function stopMarketRefresh() {
    if (tickerInterval) { clearInterval(tickerInterval); tickerInterval = null; }
    if (marketInterval) { clearInterval(marketInterval); marketInterval = null; }
}
