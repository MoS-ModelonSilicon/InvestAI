let allocChart = null;
let _recsData = null;

async function loadRecommendations() {
    const container = document.getElementById("recs-container");
    const noProfile = document.getElementById("recs-no-profile");

    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Generating personalized recommendations...</p></div>';
    noProfile.style.display = "none";

    try {
        const data = await api.get("/api/recommendations");
        renderRecommendations(data);
    } catch (err) {
        container.innerHTML = "";
        noProfile.style.display = "block";
    }
}

function renderRecommendations(data) {
    const container = document.getElementById("recs-container");
    _recsData = data;

    const allocHtml = `
        <div class="recs-top">
            <div class="alloc-card chart-card">
                <h3>Recommended Allocation</h3>
                <div class="alloc-profile">
                    <span class="badge badge-${data.profile_label.toLowerCase().replace(" ", "-")}">${data.profile_label}</span>
                    <span class="text-muted">Risk Score: ${data.risk_score}/10</span>
                </div>
                <canvas id="chart-alloc" width="250" height="250"></canvas>
            </div>
            <div class="alloc-summary chart-card">
                <h3>Portfolio Split</h3>
                <div class="alloc-row"><div class="alloc-dot" style="background:#6366f1"></div>Stocks ${helpIcon("allocation_stocks")}<span>${data.allocation.stocks}%</span></div>
                <div class="alloc-row"><div class="alloc-dot" style="background:#22c55e"></div>Bonds ${helpIcon("allocation_bonds")}<span>${data.allocation.bonds}%</span></div>
                <div class="alloc-row"><div class="alloc-dot" style="background:#eab308"></div>Cash ${helpIcon("allocation_cash")}<span>${data.allocation.cash}%</span></div>
                <p class="alloc-note">Based on your ${data.profile_label.toLowerCase()} risk profile, we recommend this allocation to balance growth and stability.</p>
            </div>
        </div>`;

    const filterTabs = `
        <div class="rec-tabs" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;gap:4px;">
                <button class="rec-tab active" onclick="filterRecs('all', this)">All (${data.recommendations.length})</button>
                <button class="rec-tab" onclick="filterRecs('Stock', this)">Stocks</button>
                <button class="rec-tab" onclick="filterRecs('ETF', this)">ETFs</button>
            </div>
            <button class="bundle-buy-btn" onclick="buyRecommendationsBundle()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                Buy All as Bundle
            </button>
        </div>`;

    const cards = data.recommendations.map((r) => {
        const riskColors = { Low: "var(--green)", Medium: "#eab308", High: "var(--red)" };
        const matchColor = r.match_score >= 75 ? "var(--green)" : r.match_score >= 50 ? "#eab308" : "var(--red)";
        const safeName = (r.name || "").replace(/'/g, "\\'");
        return `
        <div class="rec-card" data-asset-type="${r.asset_type}" data-symbol="${r.symbol}" data-stock-name="${(r.name||"").replace(/"/g,'&quot;')}" data-stock-price="${r.price}">
            <div class="rec-card-header">
                <div>
                    <div class="rec-symbol">${r.symbol}</div>
                    <div class="rec-name">${r.name}</div>
                </div>
                <div class="rec-match" style="color:${matchColor}">${r.match_score}% match ${helpIcon("match_score")}</div>
            </div>
            <div class="rec-badges">
                <span class="badge" data-help="risk_level" style="background:${riskColors[r.risk_level]}20;color:${riskColors[r.risk_level]}">${r.risk_level} Risk</span>
                <span class="badge" style="background:var(--bg);color:var(--text-muted)">${r.asset_type}</span>
                <span class="badge" style="background:var(--bg);color:var(--text-muted)">${r.sector}</span>
            </div>
            <div class="rec-metrics">
                <div><span class="metric-label">Price</span><span class="metric-value">${fmt(r.price)}</span></div>
                <div><span class="metric-label">P/E ${helpIcon("pe_ratio")}</span><span class="metric-value">${r.pe_ratio != null ? r.pe_ratio.toFixed(1) : "—"}</span></div>
                <div><span class="metric-label">Div Yield ${helpIcon("dividend_yield")}</span><span class="metric-value">${r.dividend_yield != null ? r.dividend_yield.toFixed(2) + "%" : "—"}</span></div>
                <div><span class="metric-label">Beta ${helpIcon("beta")}</span><span class="metric-value">${r.beta != null ? r.beta.toFixed(2) : "—"}</span></div>
            </div>
            <div class="rec-reason">${r.reason}</div>
            <div class="rec-actions" style="display:flex;gap:8px;margin-top:10px;">
                <button class="btn btn-sm btn-primary" onclick="openAddHoldingModal('${r.symbol}','${safeName}',${r.price})" title="Add to portfolio">+ Portfolio</button>
                <button class="btn btn-sm" onclick="addToWatchlistFromDetail('${r.symbol}','${safeName}')" title="Add to watchlist">+ Watch</button>
                <button class="btn btn-sm" onclick="navigateToStock('${r.symbol}')" title="View details">📈 Details</button>
            </div>
        </div>`;
    }).join("");

    container.innerHTML = allocHtml + filterTabs + `<div class="recs-grid" id="recs-grid">${cards}</div>`;

    renderAllocChart(data.allocation);
}

function renderAllocChart(alloc) {
    const ctx = document.getElementById("chart-alloc");
    if (!ctx) return;
    if (allocChart) allocChart.destroy();
    allocChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Stocks", "Bonds", "Cash"],
            datasets: [{ data: [alloc.stocks, alloc.bonds, alloc.cash], backgroundColor: ["#6366f1", "#22c55e", "#eab308"], borderWidth: 0 }],
        },
        options: {
            responsive: true, cutout: "60%",
            plugins: { legend: { display: false } },
        },
    });
}

function filterRecs(type, btn) {
    document.querySelectorAll(".rec-tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".rec-card").forEach((c) => {
        c.style.display = (type === "all" || c.dataset.assetType === type) ? "" : "none";
    });
}

function buyRecommendationsBundle() {
    if (!_recsData || !_recsData.recommendations || _recsData.recommendations.length === 0) {
        if (typeof showToast === "function") showToast("No recommendations to buy", "info");
        return;
    }
    const stocks = _recsData.recommendations.map(r => ({
        symbol: r.symbol,
        name: r.name,
        price: r.price,
        allocation_pct: r.match_score,
    }));
    buyStockBundle(stocks);
}
