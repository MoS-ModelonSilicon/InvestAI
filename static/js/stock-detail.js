let detailChart = null;
let _currentDetailSymbol = null;
let _spyOverlayActive = false;
let _lastHistory = null;
let _lastSpyHistory = null;

function navigateToStock(symbol) {
    _currentDetailSymbol = symbol;
    navigateTo("stock-detail");
}

async function loadStockDetail() {
    const sym = _currentDetailSymbol;
    if (!sym) {
        document.getElementById("stock-detail-content").innerHTML = '<div class="empty-state"><p>Select a stock to view details.</p></div>';
        return;
    }

    const container = document.getElementById("stock-detail-content");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading stock data...</p></div>';

    try {
        // Single combined endpoint — 1 round trip instead of 3
        const resp = await api.get(`/api/stock/${sym}/full`);
        renderStockDetail(resp.info, resp.history, resp.news);
    } catch (e) {
        container.innerHTML = `<p style="color:var(--red);padding:20px;">Failed to load data for ${sym}.</p>`;
    }
}

function renderStockDetail(info, history, news) {
    const container = document.getElementById("stock-detail-content");
    const ycSign = (info.year_change || 0) >= 0 ? "+" : "";
    const ycCls = (info.year_change || 0) >= 0 ? "stock-up" : "stock-down";

    let signalHtml = "";
    if (info.signal) {
        const map = { Buy: "signal-buy", Hold: "signal-hold", Avoid: "signal-avoid" };
        signalHtml = `<span class="signal-badge ${map[info.signal] || "signal-hold"}">${info.signal}</span>`;
    }

    let html = `
    <div class="sd-header" data-symbol="${info.symbol}" data-stock-name="${(info.name||'').replace(/"/g,'&quot;')}" data-stock-price="${info.price||''}">
        <div class="sd-title-area">
            <div class="sd-symbol">${info.symbol}</div>
            <div class="sd-name">${info.name}</div>
            <div class="sd-tags">
                <span class="detail-tag">${info.sector}</span>
                ${info.industry && info.industry !== "N/A" ? `<span class="detail-tag">${info.industry}</span>` : ""}
                ${signalHtml}
            </div>
        </div>
        <div class="sd-price-area">
            <div class="sd-price">${fmt(info.price)}</div>
            ${info.year_change != null ? `<div class="sd-change ${ycCls}">${ycSign}${info.year_change.toFixed(1)}% 1Y</div>` : ""}
        </div>
    </div>

    <div class="sd-actions">
        <button class="btn btn-primary btn-sm" onclick="addToWatchlistFromDetail('${info.symbol}','${(info.name || "").replace(/'/g, "\\'")}')">+ Watchlist</button>
        <button class="btn btn-sm" onclick="openAddHoldingModal('${info.symbol}','${(info.name || "").replace(/'/g, "\\'")}', ${info.price})">+ Portfolio</button>

    </div>

    <div class="sd-chart-section">
        <div class="sd-timeframes">
            <button class="sd-tf active" onclick="changeTimeframe('${info.symbol}','1mo','1d',this)">1M</button>
            <button class="sd-tf" onclick="changeTimeframe('${info.symbol}','3mo','1d',this)">3M</button>
            <button class="sd-tf" onclick="changeTimeframe('${info.symbol}','6mo','1d',this)">6M</button>
            <button class="sd-tf" onclick="changeTimeframe('${info.symbol}','1y','1d',this)">1Y</button>
            <button class="sd-tf" onclick="changeTimeframe('${info.symbol}','5y','1wk',this)">5Y</button>
            <span class="sd-tf-divider"></span>
            <button class="sd-tf sd-spy-toggle" id="spy-toggle-btn" onclick="toggleSpyOverlay('${info.symbol}')">vs SPY</button>
        </div>
        <div class="sd-chart-wrapper">
            <canvas id="sd-price-chart"></canvas>
        </div>
    </div>`;

    // Key Stats
    const stats = [
        ["Market Cap", info.market_cap ? formatMarketCapLocal(info.market_cap) : "N/A"],
        ["P/E (TTM)", info.pe_ratio != null ? info.pe_ratio.toFixed(1) : "—"],
        ["Forward P/E", info.forward_pe != null ? info.forward_pe.toFixed(1) : "—"],
        ["Div Yield", info.dividend_yield != null ? info.dividend_yield.toFixed(2) + "%" : "—"],
        ["Beta", info.beta != null ? info.beta.toFixed(2) : "—"],
        ["52W High", info.week52_high != null ? fmt(info.week52_high) : "—"],
        ["52W Low", info.week52_low != null ? fmt(info.week52_low) : "—"],
        ["Revenue Growth", info.revenue_growth != null ? `${info.revenue_growth > 0 ? "+" : ""}${info.revenue_growth.toFixed(1)}%` : "—"],
        ["Profit Margin", info.profit_margin != null ? info.profit_margin.toFixed(1) + "%" : "—"],
        ["Debt/Equity", info.debt_to_equity != null ? info.debt_to_equity.toFixed(0) + "%" : "—"],
        ["ROE", info.return_on_equity != null ? info.return_on_equity.toFixed(1) + "%" : "—"],
    ];

    html += `<div class="sd-grid-2col">`;
    html += `<div class="sd-section"><h3>Key Statistics</h3><div class="sd-stats-grid">`;
    stats.forEach(([label, value]) => {
        html += `<div class="sd-stat-row"><span>${label}</span><span>${value}</span></div>`;
    });
    html += `</div></div>`;

    // Risk Analysis
    if (info.risk_analysis && info.risk_analysis.factors && info.risk_analysis.factors.length > 0) {
        const ra = info.risk_analysis;
        const riskColor = ra.overall_score <= 3 ? "var(--green)" : ra.overall_score <= 5 ? "#eab308" : "var(--red)";
        html += `<div class="sd-section"><h3>Risk Analysis</h3>
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
            const barColor = f.score <= 3 ? "var(--green)" : f.score <= 5 ? "#eab308" : "var(--red)";
            html += `<div class="risk-factor"><div class="risk-factor-header"><span class="risk-factor-name">${f.name}</span><span class="risk-factor-label" style="color:${barColor}">${f.label}</span></div><div class="risk-bar-track"><div class="risk-bar-fill" style="width:${pct}%;background:${barColor}"></div></div><div class="risk-factor-detail">${f.detail}</div></div>`;
        });
        html += `</div></div>`;
    }
    html += `</div>`;

    // Analyst Targets
    if (info.analyst_targets) {
        const at = info.analyst_targets;
        const upsideColor = at.upside_pct >= 0 ? "var(--green)" : "var(--red)";
        html += `<div class="sd-section"><h3>Analyst Price Targets</h3>
            <div class="analyst-grid">
                <div class="analyst-item"><span class="analyst-label">Current</span><span class="analyst-value">${fmt(info.price)}</span></div>
                <div class="analyst-item"><span class="analyst-label">Avg Target</span><span class="analyst-value" style="color:${upsideColor}">${fmt(at.target_mean)}</span></div>
                <div class="analyst-item"><span class="analyst-label">Upside</span><span class="analyst-value" style="color:${upsideColor}">${at.upside_pct > 0 ? "+" : ""}${at.upside_pct}%</span></div>
                <div class="analyst-item"><span class="analyst-label">Analysts</span><span class="analyst-value">${at.num_analysts}</span></div>
            </div></div>`;
    }

    // About
    if (info.summary) {
        html += `<div class="sd-section"><h3>About ${info.symbol}</h3><p class="detail-summary">${info.summary}</p></div>`;
    }

    // News
    if (news && news.length > 0) {
        html += `<div class="sd-section"><h3>Recent News</h3><div class="sd-news-list">`;
        news.forEach(n => {
            const date = n.published ? new Date(n.published * 1000).toLocaleDateString() : "";
            html += `<a href="${n.link}" target="_blank" class="sd-news-item">
                <div class="sd-news-text"><div class="sd-news-title">${n.title}</div><div class="sd-news-meta">${n.publisher} · ${date}</div></div>
            </a>`;
        });
        html += `</div></div>`;
    }

    container.innerHTML = html;
    _spyOverlayActive = false;
    _lastSpyHistory = null;
    if (history && history.close && history.close.length > 0) {
        _lastHistory = history;
        renderDetailChart(history);
    }
}

function renderDetailChart(history, spyHistory) {
    const canvas = document.getElementById("sd-price-chart");
    if (!canvas) return;
    if (detailChart) detailChart.destroy();

    const closes = history.close;
    const isUp = closes[closes.length - 1] >= closes[0];
    const color = isUp ? "rgba(34, 197, 94, 1)" : "rgba(239, 68, 68, 1)";
    const bgColor = isUp ? "rgba(34, 197, 94, 0.08)" : "rgba(239, 68, 68, 0.08)";

    // SMA 50 — pre-computed server-side, fallback to client if missing
    const sma50 = history.sma50 || closes.map((_, i) => {
        if (i < 49) return null;
        const slice = closes.slice(i - 49, i + 1);
        return Math.round(slice.reduce((a, b) => a + b, 0) / 50 * 100) / 100;
    });

    const datasets = [
        {
            label: "Price",
            data: closes,
            borderColor: color,
            borderWidth: 2,
            fill: true,
            backgroundColor: bgColor,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.1,
            yAxisID: "y",
        },
        {
            label: "SMA 50",
            data: sma50,
            borderColor: "rgba(99, 102, 241, 0.6)",
            borderWidth: 1.5,
            borderDash: [5, 3],
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            yAxisID: "y",
        },
    ];

    const scales = {
        x: { display: true, ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 8 }, grid: { color: "rgba(42,45,62,0.3)" } },
        y: { display: true, position: "left", ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => "$" + v }, grid: { color: "rgba(42,45,62,0.3)" } },
    };

    // SPY overlay — normalized % change on secondary axis
    if (spyHistory && spyHistory.close && spyHistory.close.length > 0) {
        const normalize = (arr) => {
            const base = arr[0];
            return base ? arr.map(v => v != null ? +((v / base - 1) * 100).toFixed(2) : null) : arr;
        };
        const stockPct = normalize(closes);
        const spyPct = normalize(spyHistory.close);

        // Replace price dataset with % change version
        datasets[0] = {
            label: _currentDetailSymbol + " %",
            data: stockPct,
            borderColor: color,
            borderWidth: 2,
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.1,
            yAxisID: "y",
        };
        // Remove SMA when in overlay mode
        datasets[1] = {
            label: "SPY %",
            data: spyPct,
            borderColor: "rgba(251, 191, 36, 0.85)",
            borderWidth: 2,
            borderDash: [4, 2],
            pointRadius: 0,
            fill: false,
            tension: 0.1,
            yAxisID: "y",
        };
        scales.y.ticks.callback = v => v + "%";
    }

    detailChart = new Chart(canvas, {
        type: "line",
        data: { labels: history.dates, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: "top", labels: { color: "#8b8fa3", font: { size: 11 } } },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    backgroundColor: "rgba(20,22,34,0.95)",
                    titleColor: "#8b8fa3",
                    bodyColor: "#e4e4e7",
                },
            },
            scales,
            interaction: { mode: "index", intersect: false },
        },
    });
}

async function changeTimeframe(symbol, period, interval, btn) {
    document.querySelectorAll(".sd-tf").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _lastSpyHistory = null; // reset SPY cache on timeframe change
    try {
        const history = await api.get(`/api/stock/${symbol}/history?period=${period}&interval=${interval}`);
        if (history && history.close && history.close.length > 0) {
            _lastHistory = history;
            if (_spyOverlayActive) {
                const spy = await api.get(`/api/stock/SPY/history?period=${period}&interval=${interval}`);
                _lastSpyHistory = spy;
                renderDetailChart(history, spy);
            } else {
                renderDetailChart(history);
            }
        }
    } catch (e) { /* ignore */ }
}

async function toggleSpyOverlay(symbol) {
    const btn = document.getElementById("spy-toggle-btn");
    _spyOverlayActive = !_spyOverlayActive;
    if (btn) btn.classList.toggle("active", _spyOverlayActive);

    if (!_lastHistory) return;

    if (_spyOverlayActive) {
        // Determine current timeframe from active button
        const activeBtn = document.querySelector(".sd-tf.active:not(.sd-spy-toggle)");
        const periodMap = { "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y" };
        const intervalMap = { "1M": "1d", "3M": "1d", "6M": "1d", "1Y": "1d", "5Y": "1wk" };
        const label = activeBtn ? activeBtn.textContent.trim() : "1Y";
        const period = periodMap[label] || "1y";
        const interval = intervalMap[label] || "1d";

        try {
            const spy = await api.get(`/api/stock/SPY/history?period=${period}&interval=${interval}`);
            _lastSpyHistory = spy;
            renderDetailChart(_lastHistory, spy);
        } catch (e) {
            _spyOverlayActive = false;
            if (btn) btn.classList.remove("active");
        }
    } else {
        renderDetailChart(_lastHistory);
    }
}

async function addToWatchlistFromDetail(symbol, name) {
    try {
        await api.post(`/api/screener/watchlist?symbol=${symbol}&name=${encodeURIComponent(name)}`, {});
        showToast(`${symbol} added to watchlist`);
    } catch (e) {
        showToast(`${symbol} is already in your watchlist`, "info");
    }
}

function formatMarketCapLocal(cap) {
    if (!cap) return "N/A";
    if (cap >= 1e12) return `$${(cap / 1e12).toFixed(1)}T`;
    if (cap >= 1e9) return `$${(cap / 1e9).toFixed(1)}B`;
    if (cap >= 1e6) return `$${(cap / 1e6).toFixed(0)}M`;
    return `$${cap.toLocaleString()}`;
}

function showToast(msg, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("visible"));
    setTimeout(() => { toast.classList.remove("visible"); setTimeout(() => toast.remove(), 300); }, 2500);
}
