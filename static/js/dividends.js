/* Dividend Analysis — A–F grading page */
/* global api, navigateTo */

let _divData = null;
let _divSortKey = "overall";
let _divSortAsc = false;

const GRADE_COLORS = {
    A: "#22c55e",
    B: "#84cc16",
    C: "#eab308",
    D: "#f97316",
    F: "#ef4444",
    "N/A": "#6b7280",
};

/* ── public entry ─────────────────────── */
// eslint-disable-next-line no-unused-vars
async function loadDividends() {
    const ctr = document.getElementById("div-container");
    if (!ctr) return;
    ctr.innerHTML = '<div class="loading-spinner"></div>';

    const searchInput = document.getElementById("div-search");
    if (searchInput) searchInput.value = "";

    try {
        const data = await api.get("/api/dividends");
        _divData = data.items || [];
        _renderDividendTable(_divData);
    } catch (e) {
        ctr.innerHTML = '<p class="empty-state">Failed to load dividend data.</p>';
    }
}

/* ── search handler ───────────────────── */
function _divSearch() {
    const q = (document.getElementById("div-search")?.value || "").toUpperCase().trim();
    if (!_divData) return;
    if (!q) { _renderDividendTable(_divData); return; }

    // If user types a specific symbol, fetch it live
    if (q.length >= 1 && q.length <= 6 && /^[A-Z.]+$/.test(q)) {
        const filtered = _divData.filter(
            (d) => d.symbol.includes(q) || (d.name || "").toUpperCase().includes(q)
        );
        if (filtered.length > 0) {
            _renderDividendTable(filtered);
            return;
        }
        // Try fetching the specific symbol
        _fetchSingleDividend(q);
        return;
    }
    const filtered = _divData.filter(
        (d) => d.symbol.includes(q) || (d.name || "").toUpperCase().includes(q)
    );
    _renderDividendTable(filtered);
}

async function _fetchSingleDividend(symbol) {
    const ctr = document.getElementById("div-container");
    try {
        const data = await api.get(`/api/dividends/${symbol}`);
        if (data && !data.error) {
            _renderDividendDetail(data);
        } else {
            ctr.innerHTML = `<p class="empty-state">No dividend data for ${symbol}</p>`;
        }
    } catch {
        ctr.innerHTML = `<p class="empty-state">Could not fetch data for ${symbol}</p>`;
    }
}

/* ── sort ──────────────────────────────── */
function sortDividends(key) {
    if (!_divData) return;
    if (_divSortKey === key) _divSortAsc = !_divSortAsc;
    else { _divSortKey = key; _divSortAsc = false; }

    const sorted = [..._divData].sort((a, b) => {
        let va, vb;
        if (key === "overall") {
            va = a.overall?.score ?? -1;
            vb = b.overall?.score ?? -1;
        } else if (key === "yield") {
            va = a.dividend_yield ?? -1;
            vb = b.dividend_yield ?? -1;
        } else if (key === "safety" || key === "growth" || key === "consistency") {
            va = a.grades?.[key]?.score ?? -1;
            vb = b.grades?.[key]?.score ?? -1;
        } else if (key === "symbol") {
            va = a.symbol; vb = b.symbol;
            return _divSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        } else {
            va = a[key] ?? -1; vb = b[key] ?? -1;
        }
        return _divSortAsc ? va - vb : vb - va;
    });
    _renderDividendTable(sorted);
}

/* ── render table ─────────────────────── */
function _renderDividendTable(items) {
    const ctr = document.getElementById("div-container");
    if (!ctr) return;

    if (!items || items.length === 0) {
        ctr.innerHTML = '<p class="empty-state">No dividend-paying stocks found.</p>';
        return;
    }

    const arrow = (k) => _divSortKey === k ? (_divSortAsc ? " ▲" : " ▼") : "";

    let html = `<div class="div-table-wrap"><table class="div-table">
    <thead><tr>
        <th class="div-sortable" onclick="sortDividends('symbol')">Symbol${arrow("symbol")}</th>
        <th>Name</th>
        <th>Sector</th>
        <th class="div-sortable" onclick="sortDividends('yield')">Yield${arrow("yield")}</th>
        <th class="div-sortable" onclick="sortDividends('overall')">Overall${arrow("overall")}</th>
        <th class="div-sortable" onclick="sortDividends('safety')">Safety${arrow("safety")}</th>
        <th class="div-sortable" onclick="sortDividends('growth')">Growth${arrow("growth")}</th>
        <th class="div-sortable" onclick="sortDividends('consistency')">Consistency${arrow("consistency")}</th>
    </tr></thead><tbody>`;

    for (const item of items) {
        const ov = item.overall || {};
        const g = item.grades || {};
        html += `<tr class="div-row" onclick="_showDivDetail('${item.symbol}')">
            <td class="div-symbol">${item.symbol}</td>
            <td class="div-name">${_esc(item.name || "")}</td>
            <td class="div-sector">${_esc(item.sector || "N/A")}</td>
            <td>${item.dividend_yield != null ? item.dividend_yield.toFixed(2) + "%" : "—"}</td>
            <td>${_gradeBadge(ov.grade, ov.score)}</td>
            <td>${_gradeBadge(g.safety?.grade, g.safety?.score)}</td>
            <td>${_gradeBadge(g.growth?.grade, g.growth?.score)}</td>
            <td>${_gradeBadge(g.consistency?.grade, g.consistency?.score)}</td>
        </tr>`;
    }
    html += "</tbody></table></div>";
    ctr.innerHTML = html;
}

/* ── detail view for a single stock ───── */
function _showDivDetail(symbol) {
    const item = (_divData || []).find((d) => d.symbol === symbol);
    if (item) { _renderDividendDetail(item); return; }
    _fetchSingleDividend(symbol);
}

function _renderDividendDetail(item) {
    const ctr = document.getElementById("div-container");
    if (!ctr) return;

    const ov = item.overall || {};
    const g = item.grades || {};

    let html = `<div class="div-detail">
        <button class="div-back-btn" onclick="loadDividends()">← Back to list</button>
        <div class="div-detail-header">
            <h2>${_esc(item.symbol)} — ${_esc(item.name || "")}</h2>
            <span class="div-sector-tag">${_esc(item.sector || "N/A")}</span>
            ${item.price ? `<span class="div-price">$${item.price.toFixed(2)}</span>` : ""}
            ${item.dividend_yield ? `<span class="div-yield-tag">Yield: ${item.dividend_yield.toFixed(2)}%</span>` : ""}
        </div>
        <div class="div-overall-card">
            <div class="div-overall-badge">${_gradeBadgeLarge(ov.grade, ov.score)}</div>
            <div class="div-overall-label">Overall Dividend Grade</div>
        </div>
        <div class="div-grades-grid">
            ${_gradeCard("Safety", "🛡️", g.safety)}
            ${_gradeCard("Growth", "📈", g.growth)}
            ${_gradeCard("Yield", "💰", g.yield)}
            ${_gradeCard("Consistency", "🔄", g.consistency)}
        </div>
        <button class="btn btn-secondary div-view-stock" onclick="navigateTo('stock-detail'); window._stockSymbol='${item.symbol}';">
            View Full Stock Detail →
        </button>
    </div>`;

    ctr.innerHTML = html;
}

function _gradeCard(label, icon, grade) {
    if (!grade) return "";
    return `<div class="div-grade-card">
        <div class="div-grade-card-head">
            <span class="div-grade-icon">${icon}</span>
            <span class="div-grade-label">${label}</span>
            ${_gradeBadge(grade.grade, grade.score)}
        </div>
        <ul class="div-grade-details">
            ${(grade.details || []).map((d) => `<li>${_esc(d)}</li>`).join("")}
        </ul>
    </div>`;
}

/* ── helpers ───────────────────────────── */
function _gradeBadge(grade, score) {
    if (!grade) return '<span class="div-badge" style="background:#6b7280">N/A</span>';
    const c = GRADE_COLORS[grade] || "#6b7280";
    return `<span class="div-badge" style="background:${c}">${grade}${score != null ? ` (${score})` : ""}</span>`;
}

function _gradeBadgeLarge(grade, score) {
    if (!grade) return "";
    const c = GRADE_COLORS[grade] || "#6b7280";
    return `<span class="div-badge-lg" style="background:${c}">${grade}</span>
            <span class="div-score-lg">${score ?? "—"}/100</span>`;
}

function _esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// Expose to global for onclick handlers
window.loadDividends = loadDividends;
window.sortDividends = sortDividends;
window._showDivDetail = _showDivDetail;
