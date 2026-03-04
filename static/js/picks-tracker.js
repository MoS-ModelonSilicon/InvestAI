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
        { key: "targets_hit", label: "Tgts Hit" },
        { key: "pnl_pct", label: "P&L %" },
        { key: "status", label: "Status" },
    ];

    let html = '<div class="pk-table-wrap"><table class="pk-table"><thead><tr>';
    headers.forEach(h => {
        const arrow = picksSortCol === h.key ? (picksSortAsc ? " ▲" : " ▼") : "";
        html += `<th class="pk-th-sort" onclick="sortPicks('${h.key}')">${h.label}${arrow}</th>`;
    });
    html += "</tr></thead><tbody>";

    sorted.forEach(p => {
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
        const targetsStr = (p.targets || []).map(t => fmtPrice(t)).join(", ") || "—";
        const entryStr = p.entry != null ? fmtPrice(p.entry) : "—";
        const stopStr = p.stop != null ? fmtPrice(p.stop) : "—";
        const curStr = p.current_price != null ? fmtPrice(p.current_price) : "—";
        const highStr = p.high_after != null ? fmtPrice(p.high_after) : "—";

        html += `<tr class="pk-row" data-symbol="${p.symbol}" data-stock-name="${p.symbol}" onclick="navigateToStock('${p.symbol}')" title="${p.notes || ''}">
            <td>${p.date}</td>
            <td><strong>${p.symbol}</strong></td>
            <td><span class="pk-type pk-type-${p.type}">${p.type}</span></td>
            <td>${entryStr}</td>
            <td class="pk-targets-cell">${targetsStr}</td>
            <td>${stopStr}</td>
            <td>${curStr}</td>
            <td>${highStr}</td>
            <td>${p.targets_hit || 0}/${(p.targets || []).length}</td>
            <td class="${pnlCls}"><strong>${pnlStr}</strong></td>
            <td><span class="pk-status ${statusCls}">${statusLabel}</span></td>
        </tr>`;
    });

    html += "</tbody></table></div>";
    container.innerHTML = html;
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
