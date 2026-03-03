let compChart = null;

async function loadComparison() {
    // Don't auto-load, wait for user to search
}

async function runComparison() {
    const input = document.getElementById("compare-input").value.trim();
    if (!input) return;

    const container = document.getElementById("compare-results");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Comparing stocks...</p></div>';

    try {
        const data = await api.get(`/api/compare?symbols=${encodeURIComponent(input)}`);
        renderComparison(data);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to compare. Check symbols and try again.</p>';
    }
}

function renderComparison(data) {
    const container = document.getElementById("compare-results");
    if (!data.stocks || data.stocks.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No data found for those symbols.</p></div>';
        return;
    }

    const metrics = [
        { key: "price", label: "Price", fmt: v => fmt(v) },
        { key: "market_cap_fmt", label: "Market Cap", fmt: v => v || "N/A" },
        { key: "pe_ratio", label: "P/E Ratio", fmt: v => v != null ? v.toFixed(1) : "—" },
        { key: "forward_pe", label: "Forward P/E", fmt: v => v != null ? v.toFixed(1) : "—" },
        { key: "dividend_yield", label: "Div Yield", fmt: v => v != null ? v.toFixed(2) + "%" : "—" },
        { key: "beta", label: "Beta", fmt: v => v != null ? v.toFixed(2) : "—" },
        { key: "year_change", label: "1Y Change", fmt: v => v != null ? `${v > 0 ? "+" : ""}${v.toFixed(1)}%` : "—" },
        { key: "profit_margin", label: "Profit Margin", fmt: v => v != null ? v.toFixed(1) + "%" : "—" },
        { key: "revenue_growth", label: "Revenue Growth", fmt: v => v != null ? `${v > 0 ? "+" : ""}${v.toFixed(1)}%` : "—" },
        { key: "debt_to_equity", label: "Debt/Equity", fmt: v => v != null ? v.toFixed(0) + "%" : "—" },
        { key: "return_on_equity", label: "ROE", fmt: v => v != null ? v.toFixed(1) + "%" : "—" },
        { key: "sector", label: "Sector", fmt: v => v || "N/A" },
    ];

    let html = `<div class="comp-chart-section"><h3>Normalized Price (1Y)</h3><canvas id="comp-chart" height="250"></canvas></div>`;

    const cols = data.stocks.length + 1;
    const gridCols = `200px repeat(${data.stocks.length}, 1fr)`;

    html += `<div class="comp-table"><div class="comp-header" style="grid-template-columns:${gridCols}"><span class="comp-label">Metric</span>`;
    data.stocks.forEach(s => {
        html += `<span class="comp-sym" onclick="navigateToStock('${s.symbol}')" style="cursor:pointer">${s.symbol}<br><small class="text-muted">${s.name}</small></span>`;
    });
    html += `</div>`;

    metrics.forEach(m => {
        html += `<div class="comp-row" style="grid-template-columns:${gridCols}"><span class="comp-label">${m.label}</span>`;
        let vals = data.stocks.map(s => s[m.key]);
        let bestIdx = -1;
        if (["year_change", "dividend_yield", "profit_margin", "revenue_growth", "return_on_equity"].includes(m.key)) {
            let max = -Infinity;
            vals.forEach((v, i) => { if (v != null && v > max) { max = v; bestIdx = i; } });
        }
        if (m.key === "pe_ratio" || m.key === "forward_pe") {
            let min = Infinity;
            vals.forEach((v, i) => { if (v != null && v > 0 && v < min) { min = v; bestIdx = i; } });
        }
        if (m.key === "debt_to_equity") {
            let min = Infinity;
            vals.forEach((v, i) => { if (v != null && v < min) { min = v; bestIdx = i; } });
        }

        data.stocks.forEach((s, i) => {
            const cls = i === bestIdx ? "comp-best" : "";
            html += `<span class="${cls}">${m.fmt(s[m.key])}</span>`;
        });
        html += `</div>`;
    });
    html += `</div>`;

    container.innerHTML = html;

    if (data.histories && Object.keys(data.histories).length > 0) {
        renderCompChart(data.histories);
    }
}

function renderCompChart(histories) {
    const canvas = document.getElementById("comp-chart");
    if (!canvas) return;
    if (compChart) compChart.destroy();

    const colors = ["#6366f1", "#22c55e", "#ef4444", "#eab308"];
    const datasets = [];
    let labels = [];

    Object.entries(histories).forEach(([sym, data], i) => {
        if (data.dates.length > labels.length) labels = data.dates;
        datasets.push({
            label: sym,
            data: data.normalized,
            borderColor: colors[i % colors.length],
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.2,
        });
    });

    compChart = new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "top", labels: { color: "#8b8fa3", font: { size: 12 } } },
                tooltip: { mode: "index", intersect: false, callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y > 0 ? "+" : ""}${ctx.parsed.y.toFixed(1)}%` } },
            },
            scales: {
                x: { ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 6 }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => (v > 0 ? "+" : "") + v + "%" }, grid: { color: "rgba(42,45,62,0.3)" } },
            },
        },
    });
}
