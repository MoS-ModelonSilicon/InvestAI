let screenerLoaded = false;
let _lastResults = [];
let _scrPage = 1;
const _scrPerPage = 50;

async function initScreener() {
    if (!screenerLoaded) {
        const data = await api.get("/api/screener/sectors");
        const sel = document.getElementById("scr-sector");
        sel.innerHTML = '<option value="">All Sectors</option>';
        (data.sectors || []).forEach((s) => { sel.innerHTML += `<option value="${s}">${s}</option>`; });
        const regSel = document.getElementById("scr-region");
        if (regSel && data.regions) {
            regSel.innerHTML = '<option value="">All Regions</option>';
            data.regions.forEach((r) => { regSel.innerHTML += `<option value="${r}">${r}</option>`; });
        }
        screenerLoaded = true;
    }
    checkCacheStatus();
}

let _cachePoller = null;

async function checkCacheStatus() {
    const banner = document.getElementById("scr-cache-banner");
    if (!banner) return;
    try {
        const st = await api.get("/api/market/cache-status");
        if (st.ready) {
            banner.style.display = "none";
            if (_cachePoller) { clearInterval(_cachePoller); _cachePoller = null; }
        } else {
            const pct = st.total > 0 ? Math.round((st.cached / st.total) * 100) : 0;
            banner.style.display = "flex";
            banner.innerHTML = `
                <div class="cache-banner-text">
                    <div class="spinner" style="width:18px;height:18px;border-width:2px;"></div>
                    <span>Loading market data... ${st.cached}/${st.total} symbols (${pct}%)</span>
                </div>
                <div class="cache-progress-track"><div class="cache-progress-fill" style="width:${pct}%"></div></div>`;
            if (!_cachePoller) _cachePoller = setInterval(checkCacheStatus, 3000);
        }
    } catch (e) { banner.style.display = "none"; }
}

function signalBadge(signal) {
    const map = { Buy: { cls: "signal-buy", icon: "▲" }, Hold: { cls: "signal-hold", icon: "■" }, Avoid: { cls: "signal-avoid", icon: "▼" } };
    const s = map[signal] || map.Hold;
    return `<span class="signal-badge ${s.cls}">${s.icon} ${signal}</span>`;
}

async function runScreener(page) {
    if (page !== undefined) _scrPage = page;
    else _scrPage = 1;

    const params = new URLSearchParams();
    const v = (id) => document.getElementById(id).value;
    if (v("scr-query")) params.set("query", v("scr-query").trim());
    if (v("scr-asset-type")) params.set("asset_type", v("scr-asset-type"));
    if (v("scr-sector")) params.set("sector", v("scr-sector"));
    if (v("scr-region")) params.set("region", v("scr-region"));
    if (v("scr-mcap-min")) params.set("market_cap_min", v("scr-mcap-min"));
    if (v("scr-mcap-max")) params.set("market_cap_max", v("scr-mcap-max"));
    if (v("scr-pe-min")) params.set("pe_min", v("scr-pe-min"));
    if (v("scr-pe-max")) params.set("pe_max", v("scr-pe-max"));
    if (v("scr-div-min")) params.set("dividend_yield_min", v("scr-div-min"));
    if (v("scr-beta-min")) params.set("beta_min", v("scr-beta-min"));
    if (v("scr-beta-max")) params.set("beta_max", v("scr-beta-max"));
    if (v("scr-signal")) params.set("signal", v("scr-signal"));
    params.set("page", _scrPage);
    params.set("per_page", _scrPerPage);

    const resultsEl = document.getElementById("scr-results-area");
    const empty = document.getElementById("scr-empty");
    const countEl = document.getElementById("scr-result-count");
    resultsEl.innerHTML = '<div class="text-center" style="padding:40px;"><div class="spinner"></div><p style="margin-top:12px;color:var(--text-muted);">Searching...</p></div>';
    empty.style.display = "none";
    if (countEl) countEl.textContent = "";

    const t0 = performance.now();

    try {
        const data = await api.get(`/api/screener?${params}`);
        const results = data.items || [];
        _lastResults = results;
        const elapsed = ((performance.now() - t0) / 1000).toFixed(1);

        if (results.length === 0) {
            resultsEl.innerHTML = "";
            // Check if cache is still warming — give a helpful message
            try {
                const cs = await api.get("/api/market/cache-status");
                if (!cs.ready) {
                    const pct = cs.total > 0 ? Math.round((cs.cached / cs.total) * 100) : 0;
                    empty.innerHTML = `<p>Market data is still loading (${cs.cached}/${cs.total} symbols, ${pct}%). Please wait a moment and try again.</p>`;
                } else {
                    empty.innerHTML = `<p>No stocks match these filters. Try adjusting the criteria or using a different preset.</p>`;
                }
            } catch (e) {
                empty.innerHTML = `<p>No stocks match these filters. Try adjusting the criteria or using a different preset.</p>`;
            }
            empty.style.display = "block";
            if (countEl) countEl.textContent = "0 results";
            renderPagination("scr-pagination", data, "scrGoPage");
            return;
        }
        empty.style.display = "none";
        if (countEl) countEl.textContent = `${data.total} results in ${elapsed}s`;

        resultsEl.innerHTML = '<div class="scr-cards-grid">' + results.map((r, i) => renderCard(r, i + (data.page - 1) * data.per_page)).join("") + '</div>';
        renderPagination("scr-pagination", data, "scrGoPage");
    } catch (err) {
        resultsEl.innerHTML = `<p style="color:var(--red);padding:20px;">Error loading data. Try again.</p>`;
    }
}

function scrGoPage(p) {
    runScreener(p);
    document.getElementById("page-screener")?.scrollTo({ top: 0, behavior: "smooth" });
}

function renderCard(r, idx) {
    const ycSign = (r.year_change || 0) >= 0 ? "+" : "";
    const ycCls = (r.year_change || 0) >= 0 ? "stock-up" : "stock-down";

    return `
    <div class="scr-card" id="scr-card-${idx}" data-symbol="${r.symbol}" data-stock-name="${(r.name||"").replace(/"/g,'&quot;')}" data-stock-price="${r.price}">
        <div class="scr-card-main" onclick="toggleDetail(${idx})">
            <div class="scr-card-header">
                <div>
                    <div class="scr-card-symbol">${r.symbol}</div>
                    <div class="scr-card-name">${r.name}</div>
                </div>
                <div class="scr-card-price-col">
                    <div class="scr-card-price">${fmt(r.price)}</div>
                    ${r.year_change != null ? `<div class="scr-card-yc ${ycCls}">${ycSign}${r.year_change.toFixed(1)}% 1Y</div>` : ""}
                </div>
            </div>
            <div class="scr-card-signal">
                ${signalBadge(r.signal)}
                <span class="scr-signal-reason">${r.signal_reason}</span>
            </div>
            <div class="scr-card-metrics">
                <div><span class="metric-label">Mkt Cap</span><span class="metric-value">${r.market_cap_fmt}</span></div>
                <div><span class="metric-label">P/E ${helpIcon("pe_ratio")}</span><span class="metric-value">${r.pe_ratio != null ? r.pe_ratio.toFixed(1) : "—"}</span></div>
                <div><span class="metric-label">Div % ${helpIcon("dividend_yield")}</span><span class="metric-value">${r.dividend_yield != null ? r.dividend_yield.toFixed(2) + "%" : "—"}</span></div>
                <div><span class="metric-label">Beta ${helpIcon("beta")}</span><span class="metric-value">${r.beta != null ? r.beta.toFixed(2) : "—"}</span></div>
            </div>
            <div class="scr-card-footer">
                <span class="scr-card-sector">${r.sector}${r.region && r.region !== "US" ? ` <span class="region-badge">${r.region}</span>` : ""}</span>
                <span class="scr-card-actions">
                    <button class="btn btn-sm" onclick="event.stopPropagation();navigateToStock('${r.symbol}')" title="Full detail">📈</button>
                    <button class="btn btn-sm" onclick="event.stopPropagation();addToWLFromScreener('${r.symbol}','${(r.name||"").replace(/'/g,"\\'")}')">+ Watch</button>                    <button class="btn btn-sm" onclick="event.stopPropagation();openAddHoldingModal('${r.symbol}','${(r.name||"").replace(/'/g,"\\'")}',${r.price})" title="Add to portfolio">+ Buy</button>                </span>
            </div>
        </div>
        <div class="scr-detail" id="scr-detail-${idx}" style="display:none;"></div>
    </div>`;
}

function toggleDetail(idx) {
    const el = document.getElementById(`scr-detail-${idx}`);
    if (!el) return;

    if (el.style.display !== "none") {
        el.style.display = "none";
        return;
    }

    const r = _lastResults[idx];
    if (!r) return;

    el.innerHTML = buildDetailPanel(r);
    el.style.display = "block";
}

function buildDetailPanel(r) {
    let html = '<div class="detail-panel">';

    if (r.summary) {
        html += `<div class="detail-section">
            <div class="detail-section-title">About ${r.symbol}</div>
            <p class="detail-summary">${r.summary}</p>
            <div class="detail-tags">
                <span class="detail-tag">${r.sector}</span>
                ${r.industry !== "N/A" ? `<span class="detail-tag">${r.industry}</span>` : ""}
                ${r.region ? `<span class="detail-tag">${r.region}</span>` : ""}
            </div>
        </div>`;
    }

    // Risk Analysis
    if (r.risk_analysis && r.risk_analysis.factors.length > 0) {
        const ra = r.risk_analysis;
        const riskColor = ra.overall_score <= 3 ? "var(--green)" : ra.overall_score <= 5 ? "#eab308" : ra.overall_score <= 7 ? "var(--red)" : "#dc2626";
        html += `<div class="detail-section">
            <div class="detail-section-title">Risk Analysis ${helpIcon("signal")}</div>
            <div class="risk-overview">
                <div class="risk-score-circle" style="border-color:${riskColor}">
                    <span class="risk-score-num" style="color:${riskColor}">${ra.overall_score}</span>
                    <span class="risk-score-of">/10</span>
                </div>
                <div class="risk-score-label" style="color:${riskColor}">${ra.overall_label}</div>
            </div>
            <div class="risk-factors">`;

        ra.factors.forEach(f => {
            const pct = (f.score / f.max) * 100;
            const barColor = f.score <= 3 ? "var(--green)" : f.score <= 5 ? "#eab308" : f.score <= 7 ? "var(--red)" : "#dc2626";
            html += `
                <div class="risk-factor">
                    <div class="risk-factor-header">
                        <span class="risk-factor-name">${f.name}</span>
                        <span class="risk-factor-label" style="color:${barColor}">${f.label}</span>
                    </div>
                    <div class="risk-bar-track"><div class="risk-bar-fill" style="width:${pct}%;background:${barColor}"></div></div>
                    <div class="risk-factor-detail">${f.detail}</div>
                </div>`;
        });
        html += '</div></div>';
    }

    // Analyst Price Targets
    if (r.analyst_targets) {
        const at = r.analyst_targets;
        const upsideColor = at.upside_pct >= 0 ? "var(--green)" : "var(--red)";
        const upsideSign = at.upside_pct >= 0 ? "+" : "";
        html += `<div class="detail-section">
            <div class="detail-section-title">Analyst Price Targets</div>
            <div class="analyst-grid">
                <div class="analyst-item">
                    <span class="analyst-label">Current Price</span>
                    <span class="analyst-value">${fmt(r.price)}</span>
                </div>
                <div class="analyst-item">
                    <span class="analyst-label">Avg Target</span>
                    <span class="analyst-value" style="color:${upsideColor}">${fmt(at.target_mean)}</span>
                </div>
                <div class="analyst-item">
                    <span class="analyst-label">Upside</span>
                    <span class="analyst-value" style="color:${upsideColor}">${upsideSign}${at.upside_pct}%</span>
                </div>
                <div class="analyst-item">
                    <span class="analyst-label">Analysts</span>
                    <span class="analyst-value">${at.num_analysts}</span>
                </div>
            </div>`;
        if (at.target_low && at.target_high) {
            const range = at.target_high - at.target_low;
            const pricePct = range > 0 ? Math.min(100, Math.max(0, ((r.price - at.target_low) / range) * 100)) : 50;
            html += `<div class="analyst-range">
                <div class="analyst-range-labels"><span>${fmt(at.target_low)}</span><span>${fmt(at.target_high)}</span></div>
                <div class="analyst-range-track">
                    <div class="analyst-range-marker" style="left:${pricePct}%"></div>
                </div>
                <div class="analyst-range-labels"><span>Low Target</span><span>High Target</span></div>
            </div>`;
        }
        html += '</div>';
    }

    // Key Financials
    const financials = [
        ["52W High", r.week52_high != null ? fmt(r.week52_high) : null, r.pct_from_high != null ? `(${r.pct_from_high > 0 ? "+" : ""}${r.pct_from_high}%)` : null],
        ["52W Low", r.week52_low != null ? fmt(r.week52_low) : null, r.pct_from_low != null ? `(+${r.pct_from_low}%)` : null],
        ["Forward P/E", r.forward_pe != null ? r.forward_pe.toFixed(1) : null],
        ["Revenue Growth", r.revenue_growth != null ? `${r.revenue_growth > 0 ? "+" : ""}${r.revenue_growth.toFixed(1)}%` : null],
        ["Earnings Growth", r.earnings_growth != null ? `${r.earnings_growth > 0 ? "+" : ""}${r.earnings_growth.toFixed(1)}%` : null],
        ["Profit Margin", r.profit_margin != null ? `${r.profit_margin.toFixed(1)}%` : null],
        ["Return on Equity", r.return_on_equity != null ? `${r.return_on_equity.toFixed(1)}%` : null],
        ["Debt/Equity", r.debt_to_equity != null ? `${r.debt_to_equity.toFixed(0)}%` : null],
    ].filter(row => row[1] != null);

    if (financials.length > 0) {
        html += `<div class="detail-section">
            <div class="detail-section-title">Key Financials</div>
            <div class="financials-grid">`;
        financials.forEach(([label, value, extra]) => {
            html += `<div class="financial-row"><span>${label}</span><span>${value} ${extra || ""}</span></div>`;
        });
        html += '</div></div>';
    }

    html += '</div>';
    return html;
}

function clearScreener() {
    ["scr-query", "scr-asset-type", "scr-sector", "scr-region", "scr-mcap-min", "scr-mcap-max", "scr-pe-min", "scr-pe-max", "scr-div-min", "scr-beta-min", "scr-beta-max", "scr-signal"]
        .forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
    const countEl = document.getElementById("scr-result-count");
    if (countEl) countEl.textContent = "";
    _scrPage = 1;
    const pagEl = document.getElementById("scr-pagination");
    if (pagEl) pagEl.innerHTML = "";
}

async function addToWLFromScreener(symbol, name) {
    try {
        await api.post(`/api/screener/watchlist?symbol=${symbol}&name=${encodeURIComponent(name)}`, {});
        if (typeof showToast === "function") showToast(`${symbol} added to watchlist`);
    } catch (e) {
        if (typeof showToast === "function") showToast(`${symbol} already in watchlist`, "info");
    }
}

function applyPreset(name) {
    clearScreener();
    if (name === "value") {
        document.getElementById("scr-asset-type").value = "Stock";
        document.getElementById("scr-pe-max").value = "15";
        document.getElementById("scr-div-min").value = "2";
    } else if (name === "growth") {
        document.getElementById("scr-asset-type").value = "Stock";
        document.getElementById("scr-sector").value = "Technology";
    } else if (name === "dividend") {
        document.getElementById("scr-div-min").value = "3";
    } else if (name === "etf") {
        document.getElementById("scr-asset-type").value = "ETF";
    } else if (name === "asia") {
        document.getElementById("scr-asset-type").value = "Stock";
        document.getElementById("scr-region").value = "China / Hong Kong";
    } else if (name === "europe") {
        document.getElementById("scr-asset-type").value = "Stock";
        document.getElementById("scr-region").value = "Europe";
    } else if (name === "emerging") {
        document.getElementById("scr-asset-type").value = "Stock";
    }
    runScreener();
}
