let picksData = null;
let picksFilter = null;
let picksSourceFilter = null;
let picksSortCol = "date";
let picksSortAsc = false;
let picksPage = 1;
let picksSearchQuery = "";
const PICKS_PER_PAGE = 100;

async function loadPicksTracker() {
    const container = document.getElementById("picks-results");
    const statsRow = document.getElementById("picks-stats-row");
    if (!container) return;
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Evaluating picks against real market data...</p></div>';
    if (statsRow) statsRow.innerHTML = "";

    try {
        let url = "/api/picks";
        const params = [];
        if (picksFilter) params.push(`type=${picksFilter}`);
        if (picksSourceFilter) params.push(`source=${picksSourceFilter}`);
        if (params.length) url += "?" + params.join("&");
        picksData = await api.get(url);
        renderPicksStats(picksData.stats);
        renderPicksTable(_getFilteredPicks());
        loadSourceInfo();
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load picks data.</p>';
    }
}

async function loadSourceInfo() {
    try {
        const info = await api.get("/api/picks/sources");
        const el = document.getElementById("pk-source-info");
        if (!el) return;
        const parts = [];
        if (info.total) parts.push(`<span class="pk-src-total">${info.total} total picks</span>`);
        for (const [src, count] of Object.entries(info)) {
            if (src === "total" || src === "last_refresh") continue;
            const icon = {discord: "💬", reddit: "🤖", tradingview: "📈", finviz: "🔍", Nick: "👤"}[src] || "📊";
            parts.push(`<span class="pk-src-badge">${icon} ${src}: ${count}</span>`);
        }
        if (info.last_refresh) {
            const dt = new Date(info.last_refresh + "Z");
            parts.push(`<span class="pk-src-refresh">Last refresh: ${dt.toLocaleString()}</span>`);
        }
        el.innerHTML = parts.join(" ");
    } catch (e) { /* ignore */ }
}

function renderPicksStats(stats) {
    const row = document.getElementById("picks-stats-row");
    if (!row) return;

    const winColor = stats.win_rate >= 50 ? "var(--green)" : "var(--red)";
    const avgColor = stats.avg_pnl_pct >= 0 ? "var(--green)" : "var(--red)";
    const totalColor = (stats.total_pnl_pct || 0) >= 0 ? "var(--green)" : "var(--red)";
    const pfColor = (stats.profit_factor || 0) >= 1.5 ? "var(--green)" : (stats.profit_factor || 0) >= 1 ? "var(--yellow)" : "var(--red)";

    row.innerHTML = `
        <div class="pk-stat-card">
            <div class="pk-stat-value">${stats.total_picks}</div>
            <div class="pk-stat-label">Total Picks</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:${winColor}">${stats.win_rate}%</div>
            <div class="pk-stat-label">Win Rate</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:var(--green)">${stats.winners}</div>
            <div class="pk-stat-label">Winners</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:var(--red)">${stats.stopped}</div>
            <div class="pk-stat-label">Stopped Out</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:var(--yellow)">${stats.open}</div>
            <div class="pk-stat-label">Open</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:var(--green)">+${stats.avg_win_pct}%</div>
            <div class="pk-stat-label">Avg Win</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:var(--red)">${stats.avg_loss_pct}%</div>
            <div class="pk-stat-label">Avg Loss</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:${avgColor}">${stats.avg_pnl_pct > 0 ? "+" : ""}${stats.avg_pnl_pct}%</div>
            <div class="pk-stat-label">Avg P&L</div>
        </div>
        <div class="pk-stat-card">
            <div class="pk-stat-value" style="color:${totalColor}">${(stats.total_pnl_pct || 0) > 0 ? "+" : ""}${stats.total_pnl_pct || 0}%</div>
            <div class="pk-stat-label">Total P&L</div>
        </div>
        ${stats.profit_factor != null ? `<div class="pk-stat-card">
            <div class="pk-stat-value" style="color:${pfColor}">${stats.profit_factor}x</div>
            <div class="pk-stat-label">Profit Factor</div>
        </div>` : ""}
        ${stats.avg_risk_reward != null ? `<div class="pk-stat-card">
            <div class="pk-stat-value">${stats.avg_risk_reward}:1</div>
            <div class="pk-stat-label">Avg R/R</div>
        </div>` : ""}
        ${stats.avg_days_held != null ? `<div class="pk-stat-card">
            <div class="pk-stat-value">${stats.avg_days_held}d</div>
            <div class="pk-stat-label">Avg Hold</div>
        </div>` : ""}
    `;
}

function _getFilteredPicks() {
    if (!picksData || !picksData.picks) return [];
    const q = picksSearchQuery.toLowerCase().trim();
    if (!q) return picksData.picks;
    return picksData.picks.filter(p => {
        const sym = (p.symbol || "").toLowerCase();
        const type = (p.type || "").toLowerCase();
        const src = (p.source || "").toLowerCase();
        const notes = (p.notes || "").toLowerCase();
        return sym.includes(q) || type.includes(q) || src.includes(q) || notes.includes(q);
    });
}

function renderPicksTable(picks) {
    const container = document.getElementById("picks-results");
    if (!container) return;

    const sorted = [...picks].sort((a, b) => {
        let va = a[picksSortCol], vb = b[picksSortCol];
        if (va == null) va = "";
        if (vb == null) vb = "";
        if (typeof va === "string") {
            return picksSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        }
        return picksSortAsc ? va - vb : vb - va;
    });

    // Pagination
    const totalItems = sorted.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / PICKS_PER_PAGE));
    if (picksPage > totalPages) picksPage = totalPages;
    if (picksPage < 1) picksPage = 1;
    const startIdx = (picksPage - 1) * PICKS_PER_PAGE;
    const pageItems = sorted.slice(startIdx, startIdx + PICKS_PER_PAGE);

    const headers = [
        { key: "date", label: "Date" },
        { key: "symbol", label: "Ticker" },
        { key: "source", label: "Source" },
        { key: "type", label: "Type" },
        { key: "entry", label: "Entry" },
        { key: "targets", label: "Targets" },
        { key: "stop", label: "Stop" },
        { key: "current_price", label: "Current" },
        { key: "high_after", label: "High" },
        { key: "targets_hit", label: "Progress" },
        { key: "risk_reward", label: "R/R" },
        { key: "days_held", label: "Days" },
        { key: "pnl_pct", label: "P&L %" },
        { key: "status", label: "Status" },
    ];

    // Toolbar with export + page info
    let html = `<div class="pk-toolbar">
        <span class="pk-page-info">Showing ${startIdx + 1}–${Math.min(startIdx + PICKS_PER_PAGE, totalItems)} of ${totalItems} picks</span>
        <button class="pk-export-btn" onclick="exportPicksCSV()" title="Export to CSV">&#128196; Export CSV</button>
    </div>`;
    html += '<div class="pk-table-wrap"><table class="pk-table"><thead><tr>';
    headers.forEach(h => {
        const arrow = picksSortCol === h.key ? (picksSortAsc ? " \u25b2" : " \u25bc") : "";
        html += `<th class="pk-th-sort" onclick="sortPicks('${h.key}')">${h.label}${arrow}</th>`;
    });
    html += "</tr></thead><tbody>";

    pageItems.forEach((p, rawIdx) => {
        const idx = startIdx + rawIdx;
        const statusCls = {
            winner: "pk-status-win",
            stopped: "pk-status-stop",
            open: "pk-status-open",
            no_data: "pk-status-nodata",
            no_entry: "pk-status-nodata",
            error: "pk-status-nodata",
            loser: "pk-status-stop",
            unknown: "pk-status-nodata",
        }[p.status] || "pk-status-nodata";

        const statusLabel = {
            winner: "Winner",
            stopped: "Stopped",
            open: "Open",
            no_data: "No Data",
            no_entry: "No Entry",
            error: "Error",
            loser: "Loss",
            unknown: "Unknown",
        }[p.status] || p.status;

        const pnlCls = (p.pnl_pct || 0) >= 0 ? "stock-up" : "stock-down";
        const pnlStr = p.pnl_pct != null ? `${p.pnl_pct > 0 ? "+" : ""}${p.pnl_pct}%` : "\u2014";
        const targetsArr = p.targets || [];
        const targetsStr = targetsArr.map(t => fmtPrice(t, p.currency)).join(", ") || "\u2014";
        const entryStr = p.entry != null ? fmtPrice(p.entry, p.currency) : "\u2014";
        const stopStr = p.stop != null ? fmtPrice(p.stop, p.currency) : "\u2014";
        const curStr = p.current_price != null ? fmtPrice(p.current_price, p.currency) : "\u2014";
        const highStr = p.high_after != null ? fmtPrice(p.high_after, p.currency) : "\u2014";
        const rrStr = p.risk_reward != null ? `${p.risk_reward}:1` : "\u2014";
        const daysStr = p.days_held != null ? `${p.days_held}d` : "\u2014";

        // Target progress bar
        const tHit = p.targets_hit || 0;
        const tTotal = targetsArr.length;
        const progressPct = tTotal > 0 ? Math.round((tHit / tTotal) * 100) : 0;
        const progressColor = tHit === tTotal && tTotal > 0 ? "var(--green)" : tHit > 0 ? "var(--yellow)" : "var(--text-muted)";
        const progressHtml = tTotal > 0
            ? `<div class="pk-progress-wrap">
                <div class="pk-progress-bar" style="width:${progressPct}%;background:${progressColor}"></div>
               </div>
               <span class="pk-progress-label">${tHit}/${tTotal}</span>`
            : "\u2014";

        // Notes subtitle
        const noteSub = p.notes ? `<div class="pk-note-sub">${_pkEsc(p.notes)}</div>` : "";

        // Source badge
        const rawSource = p.source || "unknown";
        const baseSource = rawSource.includes("/") ? rawSource.split("/")[0] : rawSource;
        const srcIcon = {discord: "💬", reddit: "🤖", tradingview: "📈", finviz: "🔍", Nick: "👤"}[baseSource] || "📊";
        const srcBadge = `<span class="pk-src pk-src-${baseSource.toLowerCase()}">${srcIcon} ${baseSource}</span>`;

        const rowId = `pk-detail-${idx}`;

        html += `<tr class="pk-row" data-symbol="${p.symbol}" data-stock-name="${p.symbol}" data-detail="${rowId}">
            <td>${p.date}</td>
            <td>
                <div class="pk-ticker-cell">
                    <strong class="pk-ticker-link" onclick="event.stopPropagation();navigateToStock('${p.symbol}')">${p.symbol}</strong>
                    ${noteSub}
                </div>
            </td>
            <td>${srcBadge}</td>
            <td><span class="pk-type pk-type-${p.type}">${p.type}</span></td>
            <td>${entryStr}</td>
            <td class="pk-targets-cell">${targetsStr}</td>
            <td>${stopStr}</td>
            <td>${curStr}</td>
            <td>${highStr}</td>
            <td class="pk-progress-cell">${progressHtml}</td>
            <td>${rrStr}</td>
            <td>${daysStr}</td>
            <td class="${pnlCls}"><strong>${pnlStr}</strong></td>
            <td><span class="pk-status ${statusCls}">${statusLabel}</span></td>
        </tr>`;

        // Expandable detail row
        const bestGainStr = p.best_gain_pct != null ? `+${p.best_gain_pct}%` : "\u2014";
        const worstLossStr = p.worst_loss_pct != null ? `${p.worst_loss_pct}%` : "\u2014";
        const lowStr = p.low_after != null ? fmtPrice(p.low_after) : "\u2014";
        const speedStr = p.speed_score != null ? `${p.speed_score} day${p.speed_score !== 1 ? "s" : ""}` : "\u2014";
        const sourceStr = p.source || "\u2014";

        html += `<tr class="pk-detail-row" id="${rowId}" style="display:none">
            <td colspan="${headers.length}">
                <div class="pk-detail-grid">
                    <div class="pk-detail-item">
                        <span class="pk-detail-label">Best Gain</span>
                        <span class="pk-detail-value stock-up">${bestGainStr}</span>
                    </div>
                    <div class="pk-detail-item">
                        <span class="pk-detail-label">Max Drawdown</span>
                        <span class="pk-detail-value stock-down">${worstLossStr}</span>
                    </div>
                    <div class="pk-detail-item">
                        <span class="pk-detail-label">Low After Entry</span>
                        <span class="pk-detail-value">${lowStr}</span>
                    </div>
                    <div class="pk-detail-item">
                        <span class="pk-detail-label">Speed to Target</span>
                        <span class="pk-detail-value">${speedStr}</span>
                    </div>
                    <div class="pk-detail-item">
                        <span class="pk-detail-label">Source</span>
                        <span class="pk-detail-value">${sourceStr}</span>
                    </div>
                    ${p.notes ? `<div class="pk-detail-item pk-detail-notes">
                        <span class="pk-detail-label">Notes</span>
                        <span class="pk-detail-value">${_pkEsc(p.notes)}</span>
                    </div>` : ""}
                </div>
            </td>
        </tr>`;
    });

    html += "</tbody></table></div>";

    // Pagination controls
    if (totalPages > 1) {
        html += '<div class="pk-pagination">';
        html += `<button class="pk-page-btn" onclick="goPicksPage(1)" ${picksPage === 1 ? 'disabled' : ''}>&laquo;</button>`;
        html += `<button class="pk-page-btn" onclick="goPicksPage(${picksPage - 1})" ${picksPage === 1 ? 'disabled' : ''}>&lsaquo; Prev</button>`;

        // Show page numbers with ellipsis
        const pages = _pkPageRange(picksPage, totalPages);
        pages.forEach(pg => {
            if (pg === '...') {
                html += '<span class="pk-page-ellipsis">&hellip;</span>';
            } else {
                html += `<button class="pk-page-btn ${pg === picksPage ? 'pk-page-active' : ''}" onclick="goPicksPage(${pg})">${pg}</button>`;
            }
        });

        html += `<button class="pk-page-btn" onclick="goPicksPage(${picksPage + 1})" ${picksPage === totalPages ? 'disabled' : ''}>Next &rsaquo;</button>`;
        html += `<button class="pk-page-btn" onclick="goPicksPage(${totalPages})" ${picksPage === totalPages ? 'disabled' : ''}>&raquo;</button>`;
        html += '</div>';
    }

    container.innerHTML = html;

    // Toggle detail rows on click
    container.querySelectorAll(".pk-row").forEach(row => {
        row.addEventListener("click", () => {
            const detailId = row.dataset.detail;
            const detail = document.getElementById(detailId);
            if (detail) {
                const isOpen = detail.style.display !== "none";
                detail.style.display = isOpen ? "none" : "table-row";
                row.classList.toggle("pk-row-expanded", !isOpen);
            }
        });
    });
}

function _pkEsc(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function fmtPrice(n, currency) {
    if (n == null) return "—";
    const cs = currSym(currency);
    if (n >= 100) return cs + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (n >= 1) return cs + n.toFixed(2);
    return cs + n.toFixed(4);
}

function goPicksPage(page) {
    picksPage = page;
    if (picksData) renderPicksTable(_getFilteredPicks());
    // Scroll to top of table
    const el = document.getElementById("picks-results");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

function _pkPageRange(current, total) {
    const delta = 2;
    const pages = [];
    const rangeStart = Math.max(2, current - delta);
    const rangeEnd = Math.min(total - 1, current + delta);
    pages.push(1);
    if (rangeStart > 2) pages.push('...');
    for (let i = rangeStart; i <= rangeEnd; i++) pages.push(i);
    if (rangeEnd < total - 1) pages.push('...');
    if (total > 1) pages.push(total);
    return pages;
}

function sortPicks(col) {
    if (picksSortCol === col) {
        picksSortAsc = !picksSortAsc;
    } else {
        picksSortCol = col;
        picksSortAsc = col === "date" || col === "symbol";
    }
    picksPage = 1;
    if (picksData) renderPicksTable(_getFilteredPicks());
}

function setPicksFilter(type) {
    picksFilter = type || null;
    picksPage = 1;
    document.querySelectorAll(".pk-filter-btn").forEach(b => b.classList.remove("active"));
    const active = document.querySelector(`.pk-filter-btn[data-type="${type || "all"}"]`);
    if (active) active.classList.add("active");
    loadPicksTracker();
}

function setPicksSource(source) {
    picksSourceFilter = source || null;
    picksPage = 1;
    document.querySelectorAll(".pk-source-btn").forEach(b => b.classList.remove("active"));
    const active = document.querySelector(`.pk-source-btn[data-source="${source || "all"}"]`);
    if (active) active.classList.add("active");
    loadPicksTracker();
}

async function refreshPicksSources() {
    const btn = document.getElementById("pk-refresh-btn");
    if (btn) { btn.disabled = true; btn.textContent = "⏳ Refreshing..."; }
    try {
        await api.post("/api/picks/refresh", {});
        if (btn) btn.textContent = "✅ Refresh started — reload in ~60s";
        setTimeout(() => { if (btn) { btn.disabled = false; btn.textContent = "🔄 Refresh Sources"; } }, 5000);
    } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = "❌ Failed — Retry"; }
    }
}

async function seedWatchlistFromPicks() {
    const btn = document.getElementById("pk-seed-btn");
    if (btn) { btn.disabled = true; btn.textContent = "Adding..."; }
    try {
        const result = await api.post("/api/picks/seed-watchlist", {});
        if (btn) btn.textContent = `Added ${result.added}, ${result.skipped} already existed`;
        setTimeout(() => { if (btn) { btn.disabled = false; btn.textContent = "Add All to Watchlist"; } }, 3000);
    } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = "Failed — Retry"; }
    }
}

function filterPicks(query) {
    picksSearchQuery = query || "";
    picksPage = 1;
    if (picksData) {
        const filtered = _getFilteredPicks();
        renderPicksTable(filtered);
        if (filtered.length === 0 && picksSearchQuery) {
            const container = document.getElementById("picks-results");
            if (container) container.innerHTML += `<div class="search-no-results">No picks matching "${_pkEsc(picksSearchQuery)}"</div>`;
        }
    }
}

function exportPicksCSV() {
    if (!picksData || !picksData.picks) return;
    const cols = ["date", "symbol", "type", "entry", "stop", "current_price", "high_after", "low_after",
                  "targets_hit", "risk_reward", "days_held", "pnl_pct", "best_gain_pct", "worst_loss_pct",
                  "speed_score", "status", "source", "notes"];
    const header = cols.join(",");
    const rows = picksData.picks.map(p => {
        return cols.map(c => {
            let v = p[c];
            if (v == null) return "";
            if (Array.isArray(v)) v = v.join(";");
            if (typeof v === "string" && (v.includes(",") || v.includes('"'))) {
                v = '"' + v.replace(/"/g, '""') + '"';
            }
            return v;
        }).join(",");
    });
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `picks-tracker-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}
