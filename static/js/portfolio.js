let portfolioChart = null;
let perfChart = null;

async function loadPortfolio() {
    const container = document.getElementById("portfolio-container");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Calculating portfolio...</p></div>';

    try {
        const data = await api.get("/api/portfolio/summary");
        renderPortfolio(data);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load portfolio.</p>';
    }
}

function renderPortfolio(data) {
    const container = document.getElementById("portfolio-container");

    if (data.holdings.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No holdings yet. Add stocks from the <a href="#" onclick="navigateTo('screener');return false;" style="color:var(--primary)">Screener</a> or any stock detail page.</p></div>`;
        return;
    }

    const glCls = data.total_gain_loss >= 0 ? "stock-up" : "stock-down";
    const glSign = data.total_gain_loss >= 0 ? "+" : "";

    let html = `
    <div class="pf-stats">
        <div class="pf-stat-card">
            <div class="pf-stat-label">Total Value</div>
            <div class="pf-stat-value">${fmt(data.total_value)}</div>
        </div>
        <div class="pf-stat-card">
            <div class="pf-stat-label">Total Invested</div>
            <div class="pf-stat-value">${fmt(data.total_invested)}</div>
        </div>
        <div class="pf-stat-card">
            <div class="pf-stat-label">Total Gain/Loss</div>
            <div class="pf-stat-value ${glCls}">${glSign}${fmt(data.total_gain_loss)} (${glSign}${data.total_gain_loss_pct.toFixed(1)}%)</div>
        </div>
    </div>

    <div class="pf-grid-2col">
        <div class="pf-section">
            <h3>Sector Allocation</h3>
            <canvas id="pf-alloc-chart" height="200"></canvas>
        </div>
        <div class="pf-section">
            <h3>Performance vs S&P 500</h3>
            <canvas id="pf-perf-chart" height="200"></canvas>
            <div class="pf-perf-loading" id="pf-perf-loading" style="display:none;"><div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> Loading performance data...</div>
        </div>
    </div>

    <div class="pf-section">
        <h3>Holdings</h3>
        <div class="pf-holdings-table">
            <div class="pf-h-header">
                <span>Symbol</span><span>Qty</span><span>Buy Price</span><span>Current</span><span>Cost Basis</span><span>Value</span><span>Gain/Loss</span><span></span>
            </div>`;

    data.holdings.forEach(h => {
        const hcls = h.gain_loss >= 0 ? "stock-up" : "stock-down";
        const hsign = h.gain_loss >= 0 ? "+" : "";
        html += `
            <div class="pf-h-row" data-symbol="${h.symbol}" data-stock-name="${(h.name||"").replace(/"/g,'&quot;')}" data-stock-price="${h.current_price}" onclick="navigateToStock('${h.symbol}')">
                <span class="pf-h-symbol">${h.symbol}<br><small class="text-muted">${h.name}</small></span>
                <span>${h.quantity}</span>
                <span>${fmt(h.buy_price)}</span>
                <span>${fmt(h.current_price)}</span>
                <span>${fmt(h.cost_basis)}</span>
                <span>${fmt(h.current_value)}</span>
                <span class="${hcls}">${hsign}${fmt(h.gain_loss)}<br><small>${hsign}${h.gain_loss_pct.toFixed(1)}%</small></span>
                <span><button class="btn btn-sm btn-danger" onclick="event.stopPropagation();removeHolding(${h.id})">×</button></span>
            </div>`;
    });

    html += `</div></div>`;
    container.innerHTML = html;

    renderAllocPie(data.sector_allocation);
    loadPerformanceChart();
}

function renderAllocPie(allocation) {
    const canvas = document.getElementById("pf-alloc-chart");
    if (!canvas) return;
    if (portfolioChart) portfolioChart.destroy();

    const colors = ["#6366f1", "#22c55e", "#eab308", "#ef4444", "#3b82f6", "#ec4899", "#8b5cf6", "#14b8a6", "#f97316", "#06b6d4"];

    portfolioChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: allocation.map(a => `${a.sector} (${a.pct}%)`),
            datasets: [{ data: allocation.map(a => a.value), backgroundColor: colors.slice(0, allocation.length), borderWidth: 0 }],
        },
        options: {
            responsive: true,
            cutout: "55%",
            plugins: { legend: { position: "bottom", labels: { color: "#8b8fa3", font: { size: 11 }, padding: 12 } } },
        },
    });
}

async function loadPerformanceChart() {
    const loadEl = document.getElementById("pf-perf-loading");
    if (loadEl) loadEl.style.display = "flex";

    try {
        const data = await api.get("/api/portfolio/performance");
        if (data.dates && data.dates.length > 0) {
            renderPerfChart(data);
        }
    } catch (e) { /* ignore */ }
    if (loadEl) loadEl.style.display = "none";
}

function renderPerfChart(data) {
    const canvas = document.getElementById("pf-perf-chart");
    if (!canvas) return;
    if (perfChart) perfChart.destroy();

    perfChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: "Your Portfolio",
                    data: data.portfolio,
                    borderColor: "#6366f1",
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.2,
                },
                {
                    label: "S&P 500",
                    data: data.benchmark,
                    borderColor: "#8b8fa3",
                    borderWidth: 1.5,
                    borderDash: [4, 3],
                    pointRadius: 0,
                    fill: false,
                    tension: 0.2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "top", labels: { color: "#8b8fa3", font: { size: 11 } } },
                tooltip: { mode: "index", intersect: false, callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y > 0 ? "+" : ""}${ctx.parsed.y.toFixed(1)}%` } },
            },
            scales: {
                x: { ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 6 }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => (v > 0 ? "+" : "") + v + "%" }, grid: { color: "rgba(42,45,62,0.3)" } },
            },
        },
    });
}

async function removeHolding(id) {
    if (!confirm("Remove this holding?")) return;
    try {
        await api.del(`/api/portfolio/holdings/${id}`);
        loadPortfolio();
    } catch (e) {
        alert("Failed to remove holding");
    }
}

function openAddHoldingModal(symbol, name, price) {
    const overlay = document.getElementById("holding-modal-overlay");
    document.getElementById("holding-symbol").value = symbol || "";
    document.getElementById("holding-name").value = name || "";
    document.getElementById("holding-qty").value = "";
    document.getElementById("holding-price").value = price ? price.toFixed(2) : "";
    document.getElementById("holding-date").value = new Date().toISOString().split("T")[0];
    document.getElementById("holding-notes").value = "";
    overlay.classList.add("open");
}

function closeHoldingModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("holding-modal-overlay").classList.remove("open");
}

async function submitHolding(e) {
    e.preventDefault();
    const payload = {
        symbol: document.getElementById("holding-symbol").value.toUpperCase(),
        name: document.getElementById("holding-name").value,
        quantity: parseFloat(document.getElementById("holding-qty").value),
        buy_price: parseFloat(document.getElementById("holding-price").value),
        buy_date: document.getElementById("holding-date").value,
        notes: document.getElementById("holding-notes").value,
    };

    try {
        await api.post("/api/portfolio/holdings", payload);
        closeHoldingModal();
        if (typeof showToast === "function") showToast(`${payload.symbol} added to portfolio`);
        loadPortfolio();
    } catch (e) {
        alert("Failed to add holding");
    }
}
