/* ETF Deep Analysis — holdings, overlap, comparison, screening */
/* global fetchAPI, navigateTo, Chart */

let _etfData = null;
let _etfSortKey = "market_cap";
let _etfSortAsc = false;
let _etfActiveFilters = {};
let _compareChart = null;
let _sectorChart = null;
let _geoChart = null;

const ETF_TYPE_COLORS = {
    Equity: "#6366f1", Bond: "#22c55e", Sector: "#f59e0b",
    Thematic: "#ec4899", Commodity: "#f97316", Factor: "#8b5cf6",
    "Real Estate": "#14b8a6", Alternative: "#ef4444",
};

/* ── public entry ────────────────────── */
// eslint-disable-next-line no-unused-vars
async function loadEtfAnalysis() {
    const ctr = document.getElementById("etf-container");
    if (!ctr) return;
    ctr.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const data = await fetchAPI("/api/etf-analysis");
        _etfData = data.items || [];
        _renderEtfList(_etfData);
        _updateEtfStats(_etfData);
    } catch (e) {
        ctr.innerHTML = '<p class="empty-state">Failed to load ETF data.</p>';
    }
}

/* ── filter chips ─────────────────────── */
function _etfToggleFilter(key, value) {
    if (_etfActiveFilters[key] === value) {
        delete _etfActiveFilters[key];
    } else {
        _etfActiveFilters[key] = value;
    }
    _applyEtfFilters();

    // Update chip active states
    document.querySelectorAll(".etf-chip").forEach((chip) => {
        const ck = chip.dataset.key;
        const cv = chip.dataset.value;
        chip.classList.toggle("active", _etfActiveFilters[ck] === cv);
    });
}

function _applyEtfFilters() {
    if (!_etfData) return;
    let filtered = [..._etfData];

    const q = (document.getElementById("etf-search")?.value || "").toUpperCase().trim();
    if (q) {
        filtered = filtered.filter(
            (d) => d.symbol.includes(q) || (d.name || "").toUpperCase().includes(q)
                || (d.category || "").toUpperCase().includes(q)
        );
    }

    if (_etfActiveFilters.type) {
        filtered = filtered.filter((d) => d.type === _etfActiveFilters.type);
    }
    if (_etfActiveFilters.region) {
        filtered = filtered.filter((d) => d.region === _etfActiveFilters.region);
    }

    _renderEtfList(filtered);
    _updateEtfStats(filtered);
}

/* ── search ───────────────────────────── */
function _etfSearch() {
    _applyEtfFilters();
}

/* ── sort ──────────────────────────────── */
function sortEtfs(key) {
    if (!_etfData) return;
    if (_etfSortKey === key) _etfSortAsc = !_etfSortAsc;
    else { _etfSortKey = key; _etfSortAsc = false; }

    const ctr = document.getElementById("etf-container");
    const rows = ctr?.querySelectorAll("tbody tr");
    if (!rows) return;

    const arr = Array.from(rows);
    arr.sort((a, b) => {
        const va = parseFloat(a.dataset[key] || "-999999");
        const vb = parseFloat(b.dataset[key] || "-999999");
        if (key === "symbol" || key === "name") {
            const sa = a.dataset[key] || "";
            const sb = b.dataset[key] || "";
            return _etfSortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
        }
        return _etfSortAsc ? va - vb : vb - va;
    });

    const tbody = ctr.querySelector("tbody");
    if (tbody) arr.forEach((r) => tbody.appendChild(r));

    // Update sort arrows
    ctr.querySelectorAll("th.etf-sortable").forEach((th) => {
        const k = th.dataset.sort;
        th.classList.toggle("sort-active", k === key);
        th.dataset.dir = k === key ? (_etfSortAsc ? "asc" : "desc") : "";
    });
}

/* ── stats bar ────────────────────────── */
function _updateEtfStats(items) {
    const el = document.getElementById("etf-stats");
    if (!el) return;
    const avgExp = items.reduce((s, d) => s + (d.expense_ratio || 0), 0) / (items.length || 1);
    el.textContent = `${items.length} ETFs  •  Avg ER: ${(avgExp).toFixed(2)}%`;
}

/* ── render table ─────────────────────── */
function _renderEtfList(items) {
    const ctr = document.getElementById("etf-container");
    if (!ctr) return;

    if (!items || items.length === 0) {
        ctr.innerHTML = '<p class="empty-state">No ETFs match your criteria.</p>';
        return;
    }

    const arrow = (k) => _etfSortKey === k ? (_etfSortAsc ? " ▲" : " ▼") : "";

    let html = `<div class="etf-table-wrap"><table class="etf-table">
    <thead><tr>
        <th class="etf-sortable" data-sort="symbol" onclick="sortEtfs('symbol')">Symbol${arrow("symbol")}</th>
        <th>Name</th>
        <th class="etf-sortable" data-sort="expense_ratio" onclick="sortEtfs('expense_ratio')">ER%${arrow("expense_ratio")}</th>
        <th class="etf-sortable" data-sort="price" onclick="sortEtfs('price')">Price${arrow("price")}</th>
        <th class="etf-sortable" data-sort="dividend_yield" onclick="sortEtfs('dividend_yield')">Yield${arrow("dividend_yield")}</th>
        <th class="etf-sortable" data-sort="market_cap" onclick="sortEtfs('market_cap')">AUM${arrow("market_cap")}</th>
        <th>Type</th>
        <th>Category</th>
        <th class="etf-sortable" data-sort="pct_from_high" onclick="sortEtfs('pct_from_high')">vs 52w H${arrow("pct_from_high")}</th>
    </tr></thead><tbody>`;

    for (const d of items) {
        const er = d.expense_ratio != null ? d.expense_ratio.toFixed(2) + "%" : "—";
        const price = d.price != null ? "$" + d.price.toFixed(2) : "—";
        const yld = d.dividend_yield != null ? (d.dividend_yield * 100).toFixed(2) + "%" : "—";
        const aum = d.market_cap ? _fmtAum(d.market_cap) : "—";
        const pctH = d.pct_from_high != null ? d.pct_from_high.toFixed(1) + "%" : "—";
        const pctCls = d.pct_from_high != null ? (d.pct_from_high >= -5 ? "text-green" : d.pct_from_high >= -15 ? "text-yellow" : "text-red") : "";
        const typeBadge = `<span class="etf-type-badge" style="background:${ETF_TYPE_COLORS[d.type] || '#6b7280'}20;color:${ETF_TYPE_COLORS[d.type] || '#6b7280'}">${d.type || "—"}</span>`;

        html += `<tr onclick="_showEtfDetail('${d.symbol}')" style="cursor:pointer"
            data-symbol="${d.symbol}" data-name="${(d.name || '').replace(/"/g, '&quot;')}"
            data-expense_ratio="${d.expense_ratio ?? -1}" data-price="${d.price ?? -1}"
            data-dividend_yield="${d.dividend_yield ?? -1}" data-market_cap="${d.market_cap ?? -1}"
            data-pct_from_high="${d.pct_from_high ?? -999}">
            <td class="etf-sym">${d.symbol}</td>
            <td class="etf-name">${d.name || "—"}</td>
            <td>${er}</td>
            <td>${price}</td>
            <td>${yld}</td>
            <td>${aum}</td>
            <td>${typeBadge}</td>
            <td>${d.category || "—"}</td>
            <td class="${pctCls}">${pctH}</td>
        </tr>`;
    }
    html += "</tbody></table></div>";
    ctr.innerHTML = html;
}

function _fmtAum(v) {
    if (v >= 1e12) return "$" + (v / 1e12).toFixed(1) + "T";
    if (v >= 1e9) return "$" + (v / 1e9).toFixed(1) + "B";
    if (v >= 1e6) return "$" + (v / 1e6).toFixed(0) + "M";
    return "$" + v.toLocaleString();
}

/* ── detail view ──────────────────────── */
async function _showEtfDetail(symbol) {
    const ctr = document.getElementById("etf-container");
    if (!ctr) return;
    ctr.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const data = await fetchAPI(`/api/etf-analysis/${symbol}`);
        if (data.error) {
            ctr.innerHTML = `<p class="empty-state">${data.error}</p>`;
            return;
        }
        _renderEtfDetail(data);
    } catch {
        ctr.innerHTML = `<p class="empty-state">Failed to load ETF details.</p>`;
    }
}

function _renderEtfDetail(d) {
    const ctr = document.getElementById("etf-container");
    if (!ctr) return;

    const er = d.expense_ratio != null ? d.expense_ratio.toFixed(2) + "%" : "N/A";
    const yld = d.dividend_yield != null ? (d.dividend_yield * 100).toFixed(2) + "%" : "N/A";
    const price = d.price != null ? "$" + d.price.toFixed(2) : "N/A";
    const pctH = d.pct_from_high != null ? d.pct_from_high.toFixed(1) + "%" : "N/A";
    const beta = d.beta != null ? d.beta.toFixed(2) : "N/A";
    const pe = d.pe_ratio != null ? d.pe_ratio.toFixed(1) : "N/A";

    let html = `
    <button class="btn btn-ghost etf-back-btn" onclick="loadEtfAnalysis()">← Back to ETF List</button>
    <div class="etf-detail-header">
        <div>
            <h2 class="etf-detail-title">${d.symbol} <span class="etf-detail-name">${d.name || ""}</span></h2>
            <div class="etf-detail-badges">
                <span class="etf-type-badge" style="background:${ETF_TYPE_COLORS[d.type] || '#6b7280'}20;color:${ETF_TYPE_COLORS[d.type] || '#6b7280'}">${d.type || "—"}</span>
                <span class="etf-cat-badge">${d.category || ""}</span>
                <span class="etf-region-badge">${d.region || ""}</span>
            </div>
        </div>
        <div class="etf-detail-price">${price}</div>
    </div>

    <div class="etf-detail-grid">
        <div class="etf-metric-card">
            <div class="etf-metric-label">Expense Ratio</div>
            <div class="etf-metric-value">${er}</div>
        </div>
        <div class="etf-metric-card">
            <div class="etf-metric-label">Dividend Yield</div>
            <div class="etf-metric-value">${yld}</div>
        </div>
        <div class="etf-metric-card">
            <div class="etf-metric-label">Beta</div>
            <div class="etf-metric-value">${beta}</div>
        </div>
        <div class="etf-metric-card">
            <div class="etf-metric-label">P/E Ratio</div>
            <div class="etf-metric-value">${pe}</div>
        </div>
        <div class="etf-metric-card">
            <div class="etf-metric-label">vs 52w High</div>
            <div class="etf-metric-value ${d.pct_from_high != null && d.pct_from_high >= -5 ? 'text-green' : 'text-red'}">${pctH}</div>
        </div>
        <div class="etf-metric-card">
            <div class="etf-metric-label">Top-5 Weight</div>
            <div class="etf-metric-value">${d.top5_concentration}%</div>
        </div>
    </div>`;

    // Holdings table
    if (d.holdings && d.holdings.length > 0) {
        html += `<div class="card etf-section">
            <h3>Top Holdings</h3>
            <table class="etf-holdings-table">
                <thead><tr><th>#</th><th>Symbol</th><th>Name</th><th>Weight</th><th>Bar</th></tr></thead>
                <tbody>`;
        const maxW = Math.max(...d.holdings.map((h) => h.weight));
        d.holdings.forEach((h, i) => {
            const barPct = maxW > 0 ? (h.weight / maxW * 100) : 0;
            html += `<tr>
                <td>${i + 1}</td>
                <td class="etf-sym">${h.symbol}</td>
                <td>${h.name}</td>
                <td>${h.weight.toFixed(1)}%</td>
                <td><div class="etf-bar-wrap"><div class="etf-bar" style="width:${barPct}%"></div></div></td>
            </tr>`;
        });
        html += `</tbody></table></div>`;
    }

    // Sector allocation chart
    if (d.sector_allocation && Object.keys(d.sector_allocation).length > 0) {
        html += `<div class="card etf-section"><h3>Sector Allocation</h3><div class="etf-chart-wrap"><canvas id="etf-sector-chart"></canvas></div></div>`;
    }

    // Geography allocation chart
    if (d.geography_allocation && Object.keys(d.geography_allocation).length > 0) {
        html += `<div class="card etf-section"><h3>Geography Allocation</h3><div class="etf-chart-wrap"><canvas id="etf-geo-chart"></canvas></div></div>`;
    }

    ctr.innerHTML = html;

    // Render charts after DOM is ready
    requestAnimationFrame(() => {
        _renderSectorChart(d.sector_allocation);
        _renderGeoChart(d.geography_allocation);
    });
}

function _renderSectorChart(sectors) {
    const canvas = document.getElementById("etf-sector-chart");
    if (!canvas || !sectors || Object.keys(sectors).length === 0) return;
    if (_sectorChart) { _sectorChart.destroy(); _sectorChart = null; }

    const labels = Object.keys(sectors);
    const values = Object.values(sectors);
    const colors = [
        "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#ec4899",
        "#14b8a6", "#8b5cf6", "#f97316", "#06b6d4", "#84cc16",
        "#a855f7",
    ];

    _sectorChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { color: "var(--text-primary)", font: { size: 12 } } },
                tooltip: {
                    callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed.toFixed(1)}%` },
                },
            },
        },
    });
}

function _renderGeoChart(geo) {
    const canvas = document.getElementById("etf-geo-chart");
    if (!canvas || !geo || Object.keys(geo).length === 0) return;
    if (_geoChart) { _geoChart.destroy(); _geoChart = null; }

    const labels = Object.keys(geo);
    const values = Object.values(geo);
    const colors = [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
        "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    ];

    _geoChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { color: "var(--text-primary)", font: { size: 12 } } },
                tooltip: {
                    callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed.toFixed(1)}%` },
                },
            },
        },
    });
}

/* ── compare tool ─────────────────────── */
async function _etfCompare() {
    const input = document.getElementById("etf-compare-input");
    if (!input) return;
    const val = input.value.trim().toUpperCase();
    if (!val) return;

    const symbols = val.split(",").map((s) => s.trim()).filter(Boolean);
    if (symbols.length < 2) {
        document.getElementById("etf-compare-result").innerHTML =
            '<p class="empty-state">Enter at least 2 ETF symbols separated by commas.</p>';
        return;
    }

    const resultEl = document.getElementById("etf-compare-result");
    resultEl.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const data = await fetchAPI(`/api/etf-analysis/compare?symbols=${symbols.join(",")}`);
        _renderCompareResult(data);
    } catch {
        resultEl.innerHTML = '<p class="empty-state">Failed to compare ETFs.</p>';
    }
}

function _renderCompareResult(data) {
    const el = document.getElementById("etf-compare-result");
    if (!el || !data.items || data.items.length === 0) return;

    let html = `<table class="etf-compare-table"><thead><tr>
        <th>Metric</th>`;
    for (const etf of data.items) {
        html += `<th>${etf.symbol}</th>`;
    }
    html += `</tr></thead><tbody>`;

    const rows = [
        { label: "Name", key: "name", fmt: (v) => v || "—" },
        { label: "Price", key: "price", fmt: (v) => v != null ? "$" + v.toFixed(2) : "—" },
        { label: "Expense Ratio", key: "expense_ratio", fmt: (v) => v != null ? v.toFixed(2) + "%" : "—" },
        { label: "Dividend Yield", key: "dividend_yield", fmt: (v) => v != null ? (v * 100).toFixed(2) + "%" : "—" },
        { label: "Beta", key: "beta", fmt: (v) => v != null ? v.toFixed(2) : "—" },
        { label: "P/E Ratio", key: "pe_ratio", fmt: (v) => v != null ? v.toFixed(1) : "—" },
        { label: "vs 52w High", key: "pct_from_high", fmt: (v) => v != null ? v.toFixed(1) + "%" : "—" },
        { label: "Category", key: "category", fmt: (v) => v || "—" },
        { label: "Type", key: "type", fmt: (v) => v || "—" },
        { label: "Region", key: "region", fmt: (v) => v || "—" },
    ];

    for (const row of rows) {
        html += `<tr><td class="compare-label">${row.label}</td>`;
        // Find best value for highlighting
        const vals = data.items.map((d) => d[row.key]);
        for (let i = 0; i < data.items.length; i++) {
            const v = data.items[i][row.key];
            let cls = "";
            if (row.key === "expense_ratio" && v != null) {
                const minV = Math.min(...vals.filter((x) => x != null));
                if (v === minV) cls = "text-green";
            }
            if (row.key === "dividend_yield" && v != null) {
                const maxV = Math.max(...vals.filter((x) => x != null));
                if (v === maxV) cls = "text-green";
            }
            html += `<td class="${cls}">${row.fmt(v)}</td>`;
        }
        html += `</tr>`;
    }

    // Top holdings row
    html += `<tr><td class="compare-label">Top 5 Holdings</td>`;
    for (const etf of data.items) {
        const holdings = (etf.top_holdings || []).map((h) => `${h.symbol} (${h.weight.toFixed(1)}%)`).join(", ");
        html += `<td class="compare-holdings">${holdings || "—"}</td>`;
    }
    html += `</tr>`;

    html += `</tbody></table>`;
    el.innerHTML = html;
}

/* ── overlap tool ─────────────────────── */
async function _etfOverlap() {
    const inA = document.getElementById("etf-overlap-a");
    const inB = document.getElementById("etf-overlap-b");
    if (!inA || !inB) return;

    const a = inA.value.trim().toUpperCase();
    const b = inB.value.trim().toUpperCase();
    if (!a || !b) return;

    const resultEl = document.getElementById("etf-overlap-result");
    resultEl.innerHTML = '<div class="loading-spinner"></div>';

    try {
        const data = await fetchAPI(`/api/etf-analysis/overlap?a=${a}&b=${b}`);
        _renderOverlapResult(data);
    } catch {
        resultEl.innerHTML = '<p class="empty-state">Failed to compute overlap.</p>';
    }
}

function _renderOverlapResult(data) {
    const el = document.getElementById("etf-overlap-result");
    if (!el) return;

    let html = `<div class="etf-overlap-summary">
        <div class="etf-overlap-venn">
            <div class="venn-circle venn-a"><span>${data.etf_a}</span><small>${data.total_a} holdings</small></div>
            <div class="venn-overlap"><span>${data.overlap_count}</span><small>shared</small></div>
            <div class="venn-circle venn-b"><span>${data.etf_b}</span><small>${data.total_b} holdings</small></div>
        </div>
        <p class="overlap-pct">${data.overlap_pct_a}% of ${data.etf_a} overlaps with ${data.etf_b}</p>
    </div>`;

    if (data.common_holdings && data.common_holdings.length > 0) {
        html += `<table class="etf-overlap-table"><thead><tr>
            <th>Symbol</th><th>Name</th>
            <th>${data.etf_a} Weight</th><th>${data.etf_b} Weight</th>
        </tr></thead><tbody>`;
        for (const h of data.common_holdings) {
            html += `<tr>
                <td class="etf-sym">${h.symbol}</td>
                <td>${h.name}</td>
                <td>${h.weight_a.toFixed(1)}%</td>
                <td>${h.weight_b.toFixed(1)}%</td>
            </tr>`;
        }
        html += `</tbody></table>`;
    } else {
        html += `<p class="empty-state">No overlapping holdings found in top positions.</p>`;
    }

    el.innerHTML = html;
}
