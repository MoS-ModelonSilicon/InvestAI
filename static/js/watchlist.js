let watchlistLoaded = false;

async function loadWatchlist() {
    const container = document.getElementById("watchlist-container");
    if (!container) return;
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading watchlist...</p></div>';

    try {
        const items = await api.get("/api/screener/watchlist/live");
        if (items.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>Your watchlist is empty. Add stocks from the <a href="#" onclick="navigateTo('screener');return false;" style="color:var(--primary)">Screener</a> or any stock detail page.</p></div>`;
            return;
        }
        renderWatchlist(items);
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
        <div class="watchlist-card" onclick="navigateToStock('${item.symbol}')">
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
            <div class="wl-card-bottom">
                <span class="wl-sector">${item.sector}</span>
                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();removeWatchlistItem(${item.id}, this)">Remove</button>
            </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
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
