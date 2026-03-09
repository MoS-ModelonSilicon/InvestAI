let watchlistLoaded = false;
let _watchlistItems = [];
let _wlEditMode = false;
let _wlSelected = new Set();

async function loadWatchlist() {
    const container = document.getElementById("watchlist-container");
    if (!container) return;
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading watchlist...</p></div>';

    try {
        const items = await api.get("/api/screener/watchlist/live");
        _wlEditMode = false;
        _wlSelected.clear();
        _updateManageBtn("wl");
        if (items.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>Your watchlist is empty. Add stocks from the <a href="#" onclick="navigateTo('screener');return false;" style="color:var(--primary)">Screener</a> or any stock detail page.</p></div>`;
            const manageBtn = document.getElementById("wl-manage-btn");
            if (manageBtn) manageBtn.style.display = "none";
            return;
        }
        const manageBtn = document.getElementById("wl-manage-btn");
        if (manageBtn) manageBtn.style.display = "";
        renderWatchlist(items);
        _watchlistItems = items;
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load watchlist.</p>';
    }
}

function renderWatchlist(items) {
    const container = document.getElementById("watchlist-container");
    const count = document.getElementById("watchlist-count");
    if (count) count.textContent = `${items.length} stocks`;

    let html = '<div class="watchlist-grid">';
    items.forEach(item => {
        const ycSign = (item.year_change || 0) >= 0 ? "+" : "";
        const ycCls = (item.year_change || 0) >= 0 ? "stock-up" : "stock-down";
        html += `
        <div class="watchlist-card" data-id="${item.id}" data-symbol="${item.symbol}" data-stock-name="${(item.name||"").replace(/"/g,'&quot;')}" data-stock-price="${item.price}" onclick="wlCardClick(event, ${item.id}, '${item.symbol}')">
            <div class="em-card-checkbox" style="display:none;"><label class="em-checkbox" onclick="event.stopPropagation()"><input type="checkbox" data-id="${item.id}" data-symbol="${item.symbol}" onchange="wlToggleSelect(${item.id})"><span class="em-checkmark"></span></label></div>
            <div class="wl-card-top">
                <div>
                    <div class="wl-symbol">${item.symbol}</div>
                    <div class="wl-name">${item.name}</div>
                </div>
                <div class="wl-price-col">
                    <div class="wl-price">${fmt(item.price)}</div>
                    ${item.year_change != null ? `<div class="wl-change ${ycCls}">${ycSign}${item.year_change.toFixed(1)}% 1Y</div>` : ""}
                </div>
            </div>
            <div class="wl-metrics">
                <div><span class="metric-label">Mkt Cap</span><span class="metric-value">${item.market_cap_fmt}</span></div>
                <div><span class="metric-label">P/E</span><span class="metric-value">${item.pe_ratio != null ? item.pe_ratio.toFixed(1) : "—"}</span></div>
                <div><span class="metric-label">Div %</span><span class="metric-value">${item.dividend_yield != null ? item.dividend_yield.toFixed(2) + "%" : "—"}</span></div>
                <div><span class="metric-label">Beta</span><span class="metric-value">${item.beta != null ? item.beta.toFixed(2) : "—"}</span></div>
            </div>
            <div class="wl-card-bottom em-actions-row">
                <span class="wl-sector">${item.sector}</span>
                <span style="display:flex;gap:6px;">
                    <button class="btn btn-sm" onclick="event.stopPropagation();openAddHoldingModal('${item.symbol}','${(item.name||"").replace(/'/g,"\\'")}',${item.price})" title="Add to portfolio">+ Buy</button>
                    <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();removeWatchlistItem(${item.id}, this)">Remove</button>
                </span>
            </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
    if (_wlEditMode) _applyWlEditMode(true);
}

/* ── Watchlist Edit Mode ─────────────────────── */

function wlCardClick(event, id, symbol) {
    if (_wlEditMode) {
        wlToggleSelect(id);
        const cb = document.querySelector(`.watchlist-card[data-id="${id}"] input[type="checkbox"]`);
        if (cb) cb.checked = _wlSelected.has(id);
        return;
    }
    navigateToStock(symbol);
}

function toggleWlEditMode() {
    _wlEditMode = !_wlEditMode;
    _wlSelected.clear();
    _applyWlEditMode(_wlEditMode);
    _updateManageBtn("wl");
    _updateBulkToolbar("wl");
}

function _applyWlEditMode(on) {
    document.querySelectorAll(".watchlist-card .em-card-checkbox").forEach(el => el.style.display = on ? "" : "none");
    document.querySelectorAll(".watchlist-card .em-actions-row > span:last-child").forEach(el => el.style.display = on ? "none" : "");
    document.querySelectorAll(".watchlist-card").forEach(card => card.classList.toggle("em-mode", on));
    document.querySelectorAll(".watchlist-card").forEach(card => card.classList.remove("em-selected"));
    document.querySelectorAll(".watchlist-card input[type='checkbox']").forEach(cb => cb.checked = false);
    const toolbar = document.getElementById("bulk-toolbar-wl");
    if (toolbar) toolbar.classList.toggle("open", on);
}

function wlToggleSelect(id) {
    if (_wlSelected.has(id)) _wlSelected.delete(id); else _wlSelected.add(id);
    const card = document.querySelector(`.watchlist-card[data-id="${id}"]`);
    if (card) card.classList.toggle("em-selected", _wlSelected.has(id));
    _updateBulkToolbar("wl");
}

function wlSelectAll() {
    const cards = document.querySelectorAll(".watchlist-card");
    const allSelected = _wlSelected.size === cards.length;
    _wlSelected.clear();
    cards.forEach(c => {
        const id = parseInt(c.dataset.id);
        if (!allSelected) _wlSelected.add(id);
        c.classList.toggle("em-selected", !allSelected);
        const cb = c.querySelector("input[type='checkbox']");
        if (cb) cb.checked = !allSelected;
    });
    _updateBulkToolbar("wl");
}

async function wlBulkDelete() {
    if (_wlSelected.size === 0) return;
    const symbols = [];
    _wlSelected.forEach(id => {
        const card = document.querySelector(`.watchlist-card[data-id="${id}"]`);
        if (card) symbols.push(card.dataset.symbol);
    });
    openBulkDeleteModal("watchlist", symbols, async () => {
        try {
            const result = await api.delBulk("/api/screener/watchlist/bulk-delete", { ids: Array.from(_wlSelected) });
            _wlEditMode = false;
            _wlSelected.clear();
            _updateManageBtn("wl");
            const toolbar = document.getElementById("bulk-toolbar-wl");
            if (toolbar) toolbar.classList.remove("open");
            if (typeof showToast === "function") showToast(`${result.deleted} item${result.deleted !== 1 ? "s" : ""} removed from watchlist`);
            loadWatchlist();
        } catch (e) {
            alert("Failed to remove items");
        }
    });
}

async function removeWatchlistItem(id, btn) {
    try {
        await api.del(`/api/screener/watchlist/${id}`);
        btn.closest(".watchlist-card").remove();
        const grid = document.querySelector(".watchlist-grid");
        if (grid && grid.children.length === 0) {
            loadWatchlist();
        }
    } catch (e) {
        alert("Failed to remove item");
    }
}

function filterWatchlist(query) {
    const q = (query || "").toLowerCase().trim();
    const cards = document.querySelectorAll(".watchlist-card");
    let visible = 0;
    cards.forEach(card => {
        const symbol = (card.dataset.symbol || "").toLowerCase();
        const name = (card.dataset.stockName || "").toLowerCase();
        const sector = (card.querySelector(".wl-sector")?.textContent || "").toLowerCase();
        const match = !q || symbol.includes(q) || name.includes(q) || sector.includes(q);
        card.style.display = match ? "" : "none";
        if (match) visible++;
    });
    let noRes = document.getElementById("watchlist-no-results");
    if (!q || visible > 0) {
        if (noRes) noRes.remove();
    } else {
        if (!noRes) {
            noRes = document.createElement("div");
            noRes.id = "watchlist-no-results";
            noRes.className = "search-no-results";
            const container = document.getElementById("watchlist-container");
            if (container) container.appendChild(noRes);
        }
        noRes.textContent = `No stocks matching "${query}"`;
    }
}
