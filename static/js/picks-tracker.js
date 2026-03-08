let picksData = null;
let picksFilter = null;
let picksSortCol = "date";
let picksSortAsc = false;

async function loadPicksTracker() {
    const container = document.getElementById("picks-results");
    const statsRow = document.getElementById("picks-stats-row");
    if (!container) return;
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Evaluating picks against real market data...</p></div>';
    if (statsRow) statsRow.innerHTML = "";

    try {
        const url = picksFilter ? `/api/picks?type=${picksFilter}` : "/api/picks";
        picksData = await api.get(url);
        renderPicksStats(picksData.stats);
        renderPicksTable(picksData.picks);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load picks data.</p>';
    }
}

function renderPicksStats(stats) {
    const row = document.getElementById("picks-stats-row");
    if (!row) return;

    const winColor = stats.win_rate >= 50 ? "var(--green)" : "var(--red)";
    const avgColor = stats.avg_pnl_pct >= 0 ? "var(--green)" : "var(--red)";
    const totalColor = stats.total_pnl_pct >= 0 ? "var(--green)" : "var(--red)";
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
            <div class="pk-stat-value" style="color:${totalColor}">${stats.total_pnl_pct > 0 ? "+" : ""}${stats.total_pnl_pct}%</div>
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

    const headers = [
        { key: "date", label: "Date" },
        { key: "symbol", label: "Ticker" },
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

    // Export button
    let html = '<div class="pk-toolbar"><button class="pk-export-btn" onclick="exportPicksCSV()" title="Export to CSV">&#128196; Export CSV</button></div>';
    html += '<div class="pk-table-wrap"><table class="pk-table"><thead><tr>';
    headers.forEach(h => {
        const arrow = picksSortCol === h.key ? (picksSortAsc ? " ▲" : " ▼") : "";
        html += `<th class="pk-th-sort" onclick="sortPicks('${h.key}')">${h.label}${arrow}</th>`;
    });
    html += "</tr></thead><tbody>";

    sorted.forEach((p, idx) => {
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
        const pnlStr = p.pnl_pct != null ? `${p.pnl_pct > 0 ? "+" : ""}${p.pnl_pct}%` : "—";
        const targetsArr = p.targets || [];
        const targetsStr = targetsArr.map(t => fmtPrice(t)).join(", ") || "—";
        const entryStr = p.entry != null ? fmtPrice(p.entry) : "—";
        const stopStr = p.stop != null ? fmtPrice(p.stop) : "—";
        const curStr = p.current_price != null ? fmtPrice(p.current_price) : "—";
        const highStr = p.high_after != null ? fmtPrice(p.high_after) : "—";
        const rrStr = p.risk_reward != null ? `${p.risk_reward}:1` : "—";
        const daysStr = p.days_held != null ? `${p.days_held}d` : "—";

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
            : "—";

        // Notes subtitle
        const noteSub = p.notes ? `<div class="pk-note-sub">${escapeHtml(p.notes)}</div>` : "";

        const rowId = `pk-detail-${idx}`;

        html += `<tr class="pk-row" data-symbol="${p.symbol}" data-stock-name="${p.symbol}" data-detail="${rowId}">
            <td>${p.date}</td>
            <td>
                <div class="pk-ticker-cell">
                    <strong class="pk-ticker-link" onclick="event.stopPropagation();navigateToStock('${p.symbol}')">${p.symbol}</strong>
                    ${noteSub}
                </div>
            </td>
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
        const bestGainStr = p.best_gain_pct != null ? `+${p.best_gain_pct}%` : "—";
        const worstLossStr = p.worst_loss_pct != null ? `${p.worst_loss_pct}%` : "—";
        const lowStr = p.low_after != null ? fmtPrice(p.low_after) : "—";
        const speedStr = p.speed_score != null ? `${p.speed_score} day${p.speed_score !== 1 ? "s" : ""}` : "—";
        const sourceStr = p.source || "—";

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
                        <span class="pk-detail-value">${escapeHtml(p.notes)}</span>
                    </div>` : ""}
                </div>
            </td>
        </tr>`;
    });

    html += "</tbody></table></div>";
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

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function fmtPrice(n) {
    if (n == null) return "—";
    if (n >= 100) return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (n >= 1) return "$" + n.toFixed(2);
    return "$" + n.toFixed(4);
}

function sortPicks(col) {
    if (picksSortCol === col) {
        picksSortAsc = !picksSortAsc;
    } else {
        picksSortCol = col;
        picksSortAsc = col === "date" || col === "symbol";
    }
    if (picksData) renderPicksTable(picksData.picks);
}

function setPicksFilter(type) {
    picksFilter = type || null;
    document.querySelectorAll(".pk-filter-btn").forEach(b => b.classList.remove("active"));
    const active = document.querySelector(`.pk-filter-btn[data-type="${type || "all"}"]`);
    if (active) active.classList.add("active");
    loadPicksTracker();
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
    const q = (query || "").toLowerCase().trim();
    const rows = document.querySelectorAll(".pk-row");
    let visible = 0;
    rows.forEach(row => {
        const symbol = (row.dataset.symbol || "").toLowerCase();
        const type = (row.querySelector(".pk-type")?.textContent || "").toLowerCase();
        const match = !q || symbol.includes(q) || type.includes(q);
        row.style.display = match ? "" : "none";
        // Also hide/show the corresponding detail row
        const detailId = row.dataset.detail;
        if (detailId) {
            const detail = document.getElementById(detailId);
            if (detail && !match) detail.style.display = "none";
        }
        if (match) visible++;
    });
    let noRes = document.getElementById("picks-no-results");
    if (!q || visible > 0) {
        if (noRes) noRes.remove();
    } else {
        if (!noRes) {
            noRes = document.createElement("div");
            noRes.id = "picks-no-results";
            noRes.className = "search-no-results";
            const container = document.getElementById("picks-results");
            if (container) container.appendChild(noRes);
        }
        noRes.textContent = `No picks matching "${query}"`;
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
