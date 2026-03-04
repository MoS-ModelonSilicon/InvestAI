let _advRisk = "balanced";
let _advPeriod = "1y";
let _advChart = null;
let _advDetailChart = null;
let _advLastHoldings = [];

function setAdvRisk(r) {
    _advRisk = r;
    document.querySelectorAll(".adv-risk-btn").forEach(b => {
        b.classList.toggle("adv-risk-active", b.dataset.risk === r);
    });
}

function setAdvPeriod(p) {
    _advPeriod = p;
    document.querySelectorAll(".adv-period-btn").forEach(b => {
        b.classList.toggle("adv-period-active", b.dataset.period === p);
    });
}

async function runAdvisor() {
    const amount = document.getElementById("adv-amount").value || 10000;
    document.getElementById("adv-loading").style.display = "";
    document.getElementById("adv-results").style.display = "none";
    document.getElementById("adv-error").style.display = "none";

    try {
        const data = await api.get(`/api/advisor/analyze?amount=${amount}&risk=${_advRisk}&period=${_advPeriod}`);
        document.getElementById("adv-loading").style.display = "none";
        document.getElementById("adv-results").style.display = "";
        renderAdvisorResults(data);
    } catch (e) {
        document.getElementById("adv-loading").style.display = "none";
        document.getElementById("adv-error").style.display = "";
        document.getElementById("adv-error").innerHTML = `<p style="color:var(--red)">Analysis failed. Market data may still be loading — try again in a minute.</p>`;
    }
}

function loadSmartAdvisor() { /* page shown, no auto-load */ }

function renderAdvisorResults(data) {
    renderAdvisorReport(data.advisor_report);
    renderAdvisorRankings(data.rankings);
    renderAdvisorPortfolios(data.portfolios, data.backtest, data.selected_risk);
}

/* ── Advisor Report Card ─────────────────────────── */

function renderAdvisorReport(report) {
    const el = document.getElementById("adv-report-card");
    const mood = report.market_mood;
    const moodBar = `
        <div class="adv-mood-bar">
            <div class="adv-mood-seg adv-mood-bull" style="width:${mood.bullish}%">${mood.bullish}% Bullish</div>
            <div class="adv-mood-seg adv-mood-neut" style="width:${mood.neutral}%">${mood.neutral}%</div>
            <div class="adv-mood-seg adv-mood-bear" style="width:${mood.bearish}%">${mood.bearish}% Bearish</div>
        </div>`;

    const actions = report.top_actions.map(a => `<li>${a}</li>`).join("");
    const warnings = report.risk_warnings.map(w => `<li>${w}</li>`).join("");

    el.innerHTML = `
        <div class="adv-report">
            <div class="adv-report-header">
                <div class="adv-regime-badge adv-regime-${report.market_regime.toLowerCase().replace(/\s+/g, "-")}">${report.market_regime}</div>
                <span class="adv-report-title">Advisor Report</span>
            </div>
            ${moodBar}
            <p class="adv-summary">${report.summary}</p>
            <div class="adv-report-grid">
                <div class="adv-report-col">
                    <h4>Recommended Actions</h4>
                    <ol class="adv-actions-list">${actions}</ol>
                </div>
                <div class="adv-report-col">
                    <h4>Risk Warnings</h4>
                    <ul class="adv-warnings-list">${warnings}</ul>
                </div>
            </div>
            <p class="adv-disclaimer">${report.disclaimer}</p>
        </div>`;
}

/* ── Rankings Table ─────────────────────────────── */

function renderAdvisorRankings(rankings) {
    const el = document.getElementById("adv-rankings-section");
    if (!rankings || !rankings.length) {
        el.innerHTML = '<div class="empty-state"><p>No stocks analyzed yet.</p></div>';
        return;
    }

    const rows = rankings.slice(0, 20).map(r => {
        const sigCls = _signalClass(r.signal);
        const rsiCls = r.rsi != null ? (r.rsi > 70 ? "adv-warn" : r.rsi < 30 ? "adv-good" : "") : "";
        return `<tr class="adv-rank-row" data-symbol="${r.symbol}" data-stock-name="${(r.name||"").replace(/"/g,'&quot;')}" data-stock-price="${r.entry_price}" onclick="showAdvisorDetail('${r.symbol}')">
            <td>${r.rank}</td>
            <td><strong>${r.symbol}</strong><br><span class="adv-subtext">${r.name}</span></td>
            <td><span class="adv-score-pill">${r.score}</span></td>
            <td><span class="signal-badge ${sigCls}">${r.signal}</span></td>
            <td>${r.confidence}%</td>
            <td class="${rsiCls}">${r.rsi != null ? r.rsi.toFixed(0) : "—"}</td>
            <td>${r.macd_signal}</td>
            <td>$${r.entry_price.toFixed(2)}</td>
            <td>$${r.target_price.toFixed(2)}</td>
            <td>$${r.stop_loss.toFixed(2)}</td>
            <td>${r.risk_reward.toFixed(1)}x</td>
            <td>${stockQuickActions(r.symbol, r.name, r.entry_price, {hideDetail: true})}</td>
        </tr>`;
    }).join("");

    el.innerHTML = `
        <div class="adv-section">
            <h3>Top 20 Ranked Stocks <span class="scr-result-count">${rankings.length} analyzed</span></h3>
            <div class="table-wrapper">
                <table class="tx-table adv-table">
                    <thead><tr>
                        <th>#</th><th>Stock</th><th>Score</th><th>Signal</th><th>Conf.</th>
                        <th>RSI</th><th>MACD</th><th>Entry</th><th>Target</th><th>Stop</th><th>R/R</th><th></th>
                    </tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

/* ── Portfolio Packages ──────────────────────────── */

function renderAdvisorPortfolios(portfolios, backtest, selectedRisk) {
    const el = document.getElementById("adv-portfolio-section");
    const tabs = ["conservative", "balanced", "aggressive"];
    const tabHtml = tabs.map(t => {
        const p = portfolios[t];
        const active = t === selectedRisk ? "adv-tab-active" : "";
        return `<button class="btn btn-sm adv-port-tab ${active}" onclick="switchAdvPortfolio('${t}', this)">${p.name} (${p.risk} Risk)</button>`;
    }).join("");

    let holdingsHtml = "";
    let btHtml = "";

    const port = portfolios[selectedRisk];
    if (port && port.holdings && port.holdings.length) {
        _advLastHoldings = port.holdings;
        holdingsHtml = _renderHoldingsTable(port.holdings);
    }

    if (backtest && backtest.dates) {
        btHtml = `
            <div class="adv-bt-stats">${_renderBtStats(backtest.stats)}</div>
            <div class="adv-chart-card">
                <h4>Backtest: Portfolio vs S&P 500</h4>
                <canvas id="adv-bt-chart"></canvas>
            </div>`;
    }

    el.innerHTML = `
        <div class="adv-section">
            <h3>Portfolio Packages
                <button class="bundle-buy-btn" style="margin-left:12px;font-size:.8rem;padding:5px 12px;" onclick="buyAdvisorBundle()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    Buy All
                </button>
            </h3>
            <div class="adv-port-tabs">${tabHtml}</div>
            <div id="adv-port-content">
                ${holdingsHtml}
                ${btHtml}
            </div>
        </div>`;

    if (backtest && backtest.dates) {
        _renderBtChart(backtest);
    }
}

function _renderHoldingsTable(holdings) {
    const rows = holdings.map(h => {
        const sigCls = _signalClass(h.signal);
        return `<tr data-symbol="${h.symbol}" data-stock-name="${(h.name||"").replace(/"/g,'&quot;')}" data-stock-price="${h.entry_price}">
            <td><strong>${h.symbol}</strong></td>
            <td>${h.name}</td>
            <td>${h.sector}</td>
            <td>${h.allocation_pct.toFixed(1)}%</td>
            <td>$${h.buy_price.toFixed(2)}</td>
            <td>$${h.entry_price.toFixed(2)}</td>
            <td>$${h.target_price.toFixed(2)}</td>
            <td>$${h.stop_loss.toFixed(2)}</td>
            <td>${h.risk_reward.toFixed(1)}x</td>
            <td><span class="signal-badge ${sigCls}">${h.signal}</span></td>
            <td>${stockQuickActions(h.symbol, h.name, h.entry_price, {hideDetail: false})}</td>
        </tr>`;
    }).join("");

    return `<div class="table-wrapper">
        <table class="tx-table adv-table">
            <thead><tr>
                <th>Symbol</th><th>Name</th><th>Sector</th><th>Alloc</th>
                <th>Price</th><th>Entry</th><th>Target</th><th>Stop</th><th>R/R</th><th>Signal</th><th></th>
            </tr></thead>
            <tbody>${rows}</tbody>
        </table>
    </div>`;
}

function _renderBtStats(stats) {
    if (!stats) return "";
    const retCls = stats.total_return_pct >= 0 ? "stock-up" : "stock-down";
    const alphaCls = stats.alpha >= 0 ? "stock-up" : "stock-down";
    return `
        <div class="adv-stat-grid">
            <div class="adv-stat-item"><span class="adv-stat-label">Portfolio Return</span><span class="adv-stat-value ${retCls}">${stats.total_return_pct >= 0 ? "+" : ""}${stats.total_return_pct}%</span></div>
            <div class="adv-stat-item"><span class="adv-stat-label">S&P 500</span><span class="adv-stat-value">${stats.bench_return_pct >= 0 ? "+" : ""}${stats.bench_return_pct}%</span></div>
            <div class="adv-stat-item"><span class="adv-stat-label">Alpha</span><span class="adv-stat-value ${alphaCls}">${stats.alpha >= 0 ? "+" : ""}${stats.alpha}%</span></div>
            <div class="adv-stat-item"><span class="adv-stat-label">Sharpe</span><span class="adv-stat-value">${stats.sharpe}</span></div>
            <div class="adv-stat-item"><span class="adv-stat-label">Max Drawdown</span><span class="adv-stat-value" style="color:var(--red)">-${stats.max_drawdown}%</span></div>
        </div>`;
}

function _renderBtChart(bt) {
    const canvas = document.getElementById("adv-bt-chart");
    if (!canvas) return;
    if (_advChart) _advChart.destroy();

    _advChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: bt.dates,
            datasets: [
                {
                    label: "Portfolio",
                    data: bt.portfolio,
                    borderColor: "rgba(99, 102, 241, 1)",
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.1,
                },
                {
                    label: "S&P 500",
                    data: bt.benchmark,
                    borderColor: "rgba(156, 163, 175, 0.6)",
                    borderWidth: 1.5,
                    borderDash: [5, 3],
                    fill: false,
                    pointRadius: 0,
                    tension: 0.1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: "top", labels: { color: "#8b8fa3", font: { size: 11 } } },
                tooltip: { mode: "index", intersect: false, backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7" },
            },
            scales: {
                x: { display: true, ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 8 }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { display: true, ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => "$" + v.toLocaleString() }, grid: { color: "rgba(42,45,62,0.3)" } },
            },
            interaction: { mode: "index", intersect: false },
        },
    });
}

async function switchAdvPortfolio(risk, btn) {
    document.querySelectorAll(".adv-port-tab").forEach(b => b.classList.remove("adv-tab-active"));
    btn.classList.add("adv-tab-active");

    const amount = document.getElementById("adv-amount").value || 10000;
    try {
        const data = await api.get(`/api/advisor/analyze?amount=${amount}&risk=${risk}&period=${_advPeriod}`);
        renderAdvisorPortfolios(data.portfolios, data.backtest, risk);
    } catch (e) { /* ignore */ }
}

/* ── Single Stock Detail Modal ───────────────────── */

async function showAdvisorDetail(symbol) {
    try {
        const data = await api.get(`/api/advisor/stock/${symbol}`);
        _renderDetailModal(data);
    } catch (e) {
        alert(`Could not load analysis for ${symbol}`);
    }
}

function _renderDetailModal(data) {
    let overlay = document.getElementById("adv-detail-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "adv-detail-overlay";
        overlay.className = "modal-overlay";
        overlay.onclick = (e) => { if (e.target === overlay) overlay.style.display = "none"; };
        document.body.appendChild(overlay);
    }

    const signals = (data.signals || []).map(s => {
        const cls = s.direction === "bullish" ? "adv-sig-bull" : s.direction === "bearish" ? "adv-sig-bear" : "adv-sig-neut";
        return `<div class="adv-sig-item ${cls}"><strong>${s.name}</strong>: ${s.detail}</div>`;
    }).join("");

    const sigCls = _signalClass(data.verdict);

    overlay.innerHTML = `
        <div class="modal adv-detail-modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2>${data.symbol} — ${data.name || data.symbol}</h2>
                <button class="modal-close" onclick="document.getElementById('adv-detail-overlay').style.display='none'">&times;</button>
            </div>
            <div class="adv-detail-body">
                <div class="adv-detail-top">
                    <div class="adv-detail-verdict">
                        <span class="signal-badge ${sigCls}" style="font-size:1.1em;padding:6px 16px;">${data.verdict}</span>
                        <span class="adv-detail-score">Score: ${data.combined_score || data.technical_score}/100</span>
                        <span class="adv-detail-conf">Confidence: ${data.confidence}%</span>
                    </div>
                    <div class="adv-detail-prices">
                        <div><span class="adv-stat-label">Current</span><span>$${data.current_price.toFixed(2)}</span></div>
                        <div><span class="adv-stat-label">Entry</span><span>$${data.entry_price.toFixed(2)}</span></div>
                        <div><span class="adv-stat-label">Target</span><span style="color:var(--green)">$${data.target_price.toFixed(2)}</span></div>
                        <div><span class="adv-stat-label">Stop-Loss</span><span style="color:var(--red)">$${data.stop_loss.toFixed(2)}</span></div>
                        <div><span class="adv-stat-label">R/R</span><span>${data.risk_reward.toFixed(1)}x</span></div>
                    </div>
                </div>
                <div class="adv-detail-reasoning"><strong>Analysis:</strong> ${data.reasoning || "N/A"}</div>
                <div class="adv-detail-signals"><h4>Indicator Signals</h4>${signals}</div>
                <div class="adv-detail-chart-wrap"><canvas id="adv-detail-chart"></canvas></div>
            </div>
        </div>`;

    overlay.style.display = "flex";

    if (data.price_data && data.price_data.close && data.indicators) {
        setTimeout(() => _renderDetailCharts(data), 50);
    }
}

function _renderDetailCharts(data) {
    const canvas = document.getElementById("adv-detail-chart");
    if (!canvas) return;
    if (_advDetailChart) _advDetailChart.destroy();

    const closes = data.price_data.close;
    const dates = data.price_data.dates;
    const sma50 = data.indicators.sma_50;
    const sma200 = data.indicators.sma_200;
    const bollU = data.indicators.bollinger.upper;
    const bollL = data.indicators.bollinger.lower;

    const isUp = closes[closes.length - 1] >= closes[0];
    const color = isUp ? "rgba(34, 197, 94, 1)" : "rgba(239, 68, 68, 1)";

    _advDetailChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: dates,
            datasets: [
                { label: "Price", data: closes, borderColor: color, borderWidth: 2, fill: false, pointRadius: 0, tension: 0.1 },
                { label: "SMA 50", data: sma50, borderColor: "rgba(99, 102, 241, 0.7)", borderWidth: 1.5, borderDash: [5, 3], pointRadius: 0, fill: false, tension: 0.1 },
                { label: "SMA 200", data: sma200, borderColor: "rgba(234, 179, 8, 0.7)", borderWidth: 1.5, borderDash: [4, 4], pointRadius: 0, fill: false, tension: 0.1 },
                { label: "Bollinger Upper", data: bollU, borderColor: "rgba(156,163,175,0.3)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "Bollinger Lower", data: bollL, borderColor: "rgba(156,163,175,0.3)", borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: "rgba(156,163,175,0.05)", tension: 0.1 },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: "top", labels: { color: "#8b8fa3", font: { size: 10 } } },
                tooltip: { mode: "index", intersect: false, backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7" },
            },
            scales: {
                x: { display: true, ticks: { color: "#8b8fa3", font: { size: 9 }, maxTicksLimit: 8 }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { display: true, ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => "$" + v }, grid: { color: "rgba(42,45,62,0.3)" } },
            },
            interaction: { mode: "index", intersect: false },
        },
    });
}

/* ── Helpers ─────────────────────────────────────── */

function _signalClass(signal) {
    if (signal === "Strong Buy") return "signal-buy";
    if (signal === "Buy") return "signal-buy";
    if (signal === "Neutral") return "signal-hold";
    if (signal === "Sell") return "signal-avoid";
    if (signal === "Strong Sell") return "signal-avoid";
    return "signal-hold";
}

function buyAdvisorBundle() {
    if (!_advLastHoldings || _advLastHoldings.length === 0) {
        if (typeof showToast === "function") showToast("Run analysis first to get holdings", "info");
        return;
    }
    const stocks = _advLastHoldings.map(h => ({
        symbol: h.symbol,
        name: h.name || h.symbol,
        price: h.entry_price || h.buy_price,
        allocation_pct: h.allocation_pct,
    }));
    buyStockBundle(stocks);
}
