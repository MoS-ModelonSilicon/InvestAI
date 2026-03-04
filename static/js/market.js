let tickerInterval = null;
let marketInterval = null;
let sparkCharts = {};
let previousPrices = {};

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
    const items = quotes.map((q) => {
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
            <span class="ticker-price">$${q.price.toFixed(2)}</span>
            <span class="ticker-change">${arrow} ${Math.abs(q.change_pct).toFixed(2)}%</span>
        </div>`;
    }).join("");

    strip.innerHTML = items + items;
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
                    <div class="market-card-price">$${s.price.toFixed(2)}</div>
                    <div class="market-card-change ${cls}">${arrow} ${sign}${s.change.toFixed(2)} (${sign}${s.change_pct.toFixed(2)}%)</div>
                </div>
            </div>
            <div class="market-card-chart">
                <canvas id="spark-${s.symbol}" height="60"></canvas>
            </div>
            <div class="market-card-footer">
                <span data-help="day_range">H: $${(s.day_high || s.price).toFixed(2)}</span>
                <span data-help="day_range">L: $${(s.day_low || s.price).toFixed(2)}</span>
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

    if (sparkCharts[symbol]) sparkCharts[symbol].destroy();

    const color = isUp ? "rgba(34, 197, 94, 1)" : "rgba(239, 68, 68, 1)";
    const bgColor = isUp ? "rgba(34, 197, 94, 0.08)" : "rgba(239, 68, 68, 0.08)";

    sparkCharts[symbol] = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                data: data,
                borderColor: color,
                borderWidth: 2,
                fill: true,
                backgroundColor: bgColor,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: color,
                tension: 0.4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    mode: "index",
                    intersect: false,
                    callbacks: { label: (ctx) => "$" + ctx.parsed.y.toFixed(2) },
                    backgroundColor: "rgba(20,22,34,0.95)",
                    titleColor: "#8b8fa3",
                    bodyColor: "#e4e4e7",
                    borderColor: "rgba(42,45,62,0.8)",
                    borderWidth: 1,
                    padding: 8,
                },
            },
            scales: {
                x: { display: false },
                y: { display: false },
            },
            interaction: { mode: "index", intersect: false },
        },
    });
}

async function loadHome() {
    try {
        const data = await api.get("/api/market/home");
        renderTicker(data.ticker);
        renderFeaturedStocks(data.featured);
    } catch (e) {
        loadTicker();
        loadFeaturedStocks();
    }
}

function startMarketRefresh() {
    if (tickerInterval) clearInterval(tickerInterval);
    if (marketInterval) clearInterval(marketInterval);

    loadHome();

    marketInterval = setInterval(loadHome, 120000);
}

function stopMarketRefresh() {
    if (tickerInterval) { clearInterval(tickerInterval); tickerInterval = null; }
    if (marketInterval) { clearInterval(marketInterval); marketInterval = null; }
}
