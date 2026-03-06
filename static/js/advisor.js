let _taData = null;
let _taDetailChart = null;
let _taRefreshTimer = null;
let _taActiveTab = "hidden";
let _taLastUpdatedAt = 0;   // skip re-render if data unchanged

async function loadTradingAdvisor() {
    _fetchTradingData();
    if (!_taRefreshTimer) {
        _taRefreshTimer = setInterval(_fetchTradingData, 30000);
    }
}

async function _fetchTradingData() {
    try {
        const data = await api.get("/api/trading");
        // Skip re-render if server data hasn't changed
        if (data.updated_at && data.updated_at === _taLastUpdatedAt && _taData) return;
        _taLastUpdatedAt = data.updated_at || 0;
        _taData = data;
        _renderTADashboard(data);
    } catch (e) {
        console.warn("Trading advisor fetch failed:", e);
    }
}

function _renderTADashboard(data) {
    _renderTAMood(data.market_mood, data.progress);
    _renderTAProgress(data.progress);
    _renderTATabs(data.packages);
    _renderTAPackage(data.packages[_taActiveTab]);
    _renderTAAllPicks(data.all_picks);
}

/* ── Market mood header ─────────────────────────── */

function _renderTAMood(mood, progress) {
    const el = document.getElementById("ta-mood-header");
    if (!mood || !el) return;

    const total = progress.scanned || 0;
    const regime = mood.bullish >= 55 ? "Bullish" : mood.bearish >= 55 ? "Bearish" : mood.bullish >= 40 ? "Leaning Bullish" : "Mixed";
    const regCls = regime.includes("Bullish") ? "ta-regime-bull" : regime.includes("Bearish") ? "ta-regime-bear" : "ta-regime-mixed";

    el.innerHTML = `
        <div class="ta-mood-card">
            <div class="ta-mood-left">
                <span class="ta-regime ${regCls}">${regime}</span>
                <span class="ta-mood-sub">${total} stocks scanned</span>
            </div>
            <div class="ta-mood-bar">
                <div class="ta-bar-seg ta-bar-bull" style="width:${mood.bullish}%"><span>${mood.bullish}%</span></div>
                <div class="ta-bar-seg ta-bar-neut" style="width:${mood.neutral}%"><span>${mood.neutral}%</span></div>
                <div class="ta-bar-seg ta-bar-bear" style="width:${mood.bearish}%"><span>${mood.bearish}%</span></div>
            </div>
            <div class="ta-mood-legend">
                <span class="ta-leg ta-leg-bull">Bullish</span>
                <span class="ta-leg ta-leg-neut">Neutral</span>
                <span class="ta-leg ta-leg-bear">Bearish</span>
            </div>
        </div>`;
}

function _renderTAProgress(progress) {
    const el = document.getElementById("ta-progress");
    if (!el) return;
    if (progress.complete) {
        el.innerHTML = "";
        return;
    }
    const pct = progress.total > 0 ? Math.round(progress.scanned / progress.total * 100) : 0;
    el.innerHTML = `
        <div class="ta-progress-bar">
            <div class="ta-progress-fill" style="width:${pct}%"></div>
            <span class="ta-progress-text">Refreshing data... ${progress.scanned}/${progress.total} stocks</span>
        </div>`;
}

/* ── Package tabs + content ──────────────────────── */

function _renderTATabs(packages) {
    const el = document.getElementById("ta-pkg-tabs");
    if (!el || !packages) return;

    const tabs = [
        { id: "hidden", icon: "🔍" },
        { id: "institutional", icon: "🏦" },
        { id: "momentum", icon: "⚡" },
        { id: "swing", icon: "↗" },
        { id: "oversold", icon: "💎" },
    ];

    el.innerHTML = tabs.map(t => {
        const pkg = packages[t.id];
        if (!pkg) return "";
        const active = t.id === _taActiveTab ? "ta-tab-active" : "";
        const count = pkg.picks ? pkg.picks.length : 0;
        return `<button class="ta-tab ${active}" onclick="switchTATab('${t.id}')">
            <span class="ta-tab-icon">${t.icon}</span>
            <span class="ta-tab-name">${pkg.name}</span>
            <span class="ta-tab-count">${count}</span>
        </button>`;
    }).join("");
}

function switchTATab(tabId) {
    _taActiveTab = tabId;
    document.querySelectorAll(".ta-tab").forEach(b => b.classList.remove("ta-tab-active"));
    const active = document.querySelector(`.ta-tab[onclick*="${tabId}"]`);
    if (active) active.classList.add("ta-tab-active");
    if (_taData && _taData.packages) {
        _renderTAPackage(_taData.packages[tabId]);
    }
}

function _renderTAPackage(pkg) {
    const el = document.getElementById("ta-pkg-content");
    if (!el || !pkg) { if (el) el.innerHTML = ""; return; }

    if (!pkg.picks || pkg.picks.length === 0) {
        el.innerHTML = `<div class="ta-pkg-empty">
            <p>No picks for <strong>${pkg.name}</strong> right now. The scanner is still analyzing stocks — check back shortly.</p>
        </div>`;
        return;
    }

    const riskCls = pkg.risk_level === "High" ? "ta-risk-high" : pkg.risk_level === "Medium" ? "ta-risk-med" : "ta-risk-low";

    let html = `
        <div class="ta-pkg-header">
            <div>
                <h3 class="ta-pkg-title">${pkg.name}</h3>
                <p class="ta-pkg-subtitle">${pkg.subtitle}</p>
            </div>
            <div class="ta-pkg-meta">
                <span class="ta-pkg-tf">${pkg.timeframe}</span>
                <span class="ta-pkg-risk ${riskCls}">${pkg.risk_level} Risk</span>
            </div>
        </div>
        <div class="ta-picks-grid">`;

    for (const pick of pkg.picks) {
        html += _renderPickCard(pick);
    }

    html += "</div>";
    el.innerHTML = html;

    pkg.picks.forEach((pick, i) => {
        const canvas = document.getElementById(`ta-spark-${pick.symbol}`);
        if (canvas && pick.sparkline) _drawSparkline(canvas, pick.sparkline);
    });
}

function _renderPickCard(p) {
    const sigCls = _taSigClass(p.verdict);
    const signalsList = (p.signals_text || []).slice(0, 4).map(s => `<li>${s}</li>`).join("");

    let edgeBadges = "";
    if (p.has_divergence) edgeBadges += '<span class="ta-edge-badge ta-edge-div">Divergence</span>';
    if (p.quiet_accumulation || p.has_institutional_signal) edgeBadges += '<span class="ta-edge-badge ta-edge-inst">Smart Money</span>';
    if (p.rs_outperforming) edgeBadges += '<span class="ta-edge-badge ta-edge-rs">Outperformer</span>';
    if (p.boll_squeeze) edgeBadges += '<span class="ta-edge-badge ta-edge-squeeze">Squeeze</span>';

    return `
    <div class="ta-pick-card" data-symbol="${p.symbol}" data-stock-name="${(p.name||"").replace(/"/g,'&quot;')}" data-stock-price="${p.entry}" onclick="showTADetail('${p.symbol}')">
        <div class="ta-pick-top">
            <div class="ta-pick-sym">
                <strong>${p.symbol}</strong>
                <span class="ta-pick-name">${p.name}</span>
            </div>
            <span class="signal-badge ${sigCls}">${p.verdict} ${p.confidence}%</span>
        </div>
        ${edgeBadges ? '<div class="ta-edge-badges">' + edgeBadges + '</div>' : ''}
        <div class="ta-pick-prices">
            <div><span class="ta-lbl">Entry</span><span class="ta-val">$${p.entry.toFixed(2)}</span></div>
            <div><span class="ta-lbl">Target</span><span class="ta-val ta-green">$${p.target.toFixed(2)}</span></div>
            <div><span class="ta-lbl">Stop</span><span class="ta-val ta-red">$${p.stop_loss.toFixed(2)}</span></div>
            <div><span class="ta-lbl">R/R</span><span class="ta-val">${p.risk_reward.toFixed(1)}x</span></div>
        </div>
        <div class="ta-pick-spark"><canvas id="ta-spark-${p.symbol}" width="260" height="50"></canvas></div>
        <ul class="ta-pick-signals">${signalsList}</ul>
        <div class="ta-pick-foot">
            <span class="ta-pick-sector">${p.sector}</span>
            <span class="ta-pick-score">Score ${p.score}</span>
        </div>
        <div class="ta-pick-actions" style="display:flex;gap:6px;margin-top:8px;" onclick="event.stopPropagation()">
            <button class="btn btn-sm btn-primary" onclick="openAddHoldingModal('${p.symbol}','${(p.name||"").replace(/'/g,"\\\\'")}',${p.entry})" title="Add to portfolio">+ Buy</button>
            <button class="btn btn-sm" onclick="addToWatchlistFromDetail('${p.symbol}','${(p.name||"").replace(/'/g,"\\\\'")}')" title="Watch">+ Watch</button>
        </div>
    </div>`;
}

/* ── All picks table ─────────────────────────────── */

function _renderTAAllPicks(picks) {
    const section = document.getElementById("ta-all-picks-section");
    const body = document.getElementById("ta-picks-body");
    const count = document.getElementById("ta-pick-count");
    if (!section || !body) return;

    if (!picks || picks.length === 0) {
        section.style.display = "none";
        return;
    }

    section.style.display = "";
    count.textContent = `${picks.length} stocks`;

    body.innerHTML = picks.map((p, i) => {
        const sigCls = _taSigClass(p.verdict);
        const rsiCls = p.rsi != null ? (p.rsi > 70 ? "ta-red" : p.rsi < 30 ? "ta-green" : "") : "";
        const macdTxt = p.macd_hist_positive ? "Bullish" : "Bearish";
        const macdCls = p.macd_hist_positive ? "ta-green" : "ta-red";
        return `<tr class="ta-row" data-symbol="${p.symbol}" data-stock-name="${(p.name||"").replace(/"/g,'&quot;')}" data-stock-price="${p.entry}" onclick="showTADetail('${p.symbol}')">
            <td>${i + 1}</td>
            <td><strong>${p.symbol}</strong><br><span class="ta-sub">${p.name}</span></td>
            <td><span class="ta-score-pill">${p.score}</span></td>
            <td><span class="signal-badge ${sigCls}">${p.verdict}</span></td>
            <td class="${rsiCls}">${p.rsi != null ? p.rsi.toFixed(0) : "—"}</td>
            <td class="${macdCls}">${macdTxt}</td>
            <td>$${p.entry.toFixed(2)}</td>
            <td>$${p.target.toFixed(2)}</td>
            <td>$${p.stop_loss.toFixed(2)}</td>
            <td>${p.risk_reward.toFixed(1)}x</td>
            <td onclick="event.stopPropagation()">${stockQuickActions(p.symbol, p.name, p.entry, {hideDetail: true})}</td>
        </tr>`;
    }).join("");
}

/* ── Sparkline drawing ───────────────────────────── */

function _drawSparkline(canvas, data) {
    if (!data || data.length < 2) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const step = w / (data.length - 1);

    const isUp = data[data.length - 1] >= data[0];
    const color = isUp ? "rgba(34,197,94,0.9)" : "rgba(239,68,68,0.9)";
    const fill = isUp ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)";

    ctx.beginPath();
    data.forEach((v, i) => {
        const x = i * step;
        const y = h - ((v - min) / range) * (h - 4) - 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.lineTo((data.length - 1) * step, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
}

/* ── Detail modal ────────────────────────────────── */

async function showTADetail(symbol) {
    try {
        const data = await api.get(`/api/trading/${symbol}`);
        _renderTADetailModal(data);
    } catch (e) {
        console.warn("Detail fetch failed for", symbol, e);
    }
}

function _renderTADetailModal(data) {
    let overlay = document.getElementById("ta-detail-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "ta-detail-overlay";
        overlay.className = "modal-overlay";
        overlay.onclick = (e) => { if (e.target === overlay) overlay.style.display = "none"; };
        document.body.appendChild(overlay);
    }

    const a = data.action;
    const sigCls = _taSigClass(a.verdict);

    const edgeSignals = (a.edge_signals || []).map(s => {
        const cls = s.direction === "bullish" ? "ta-sig-bull" : s.direction === "bearish" ? "ta-sig-bear" : "ta-sig-neut";
        return `<div class="ta-sig-row ta-sig-edge ${cls}"><strong>★ ${s.name}</strong>: ${s.detail}</div>`;
    }).join("");

    const signals = (a.signals || []).map(s => {
        const cls = s.direction === "bullish" ? "ta-sig-bull" : s.direction === "bearish" ? "ta-sig-bear" : "ta-sig-neut";
        return `<div class="ta-sig-row ${cls}"><strong>${s.name}</strong>: ${s.detail}</div>`;
    }).join("");

    overlay.innerHTML = `
        <div class="modal ta-detail-modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2>${data.symbol} — ${data.name}</h2>
                <button class="modal-close" onclick="document.getElementById('ta-detail-overlay').style.display='none'">&times;</button>
            </div>
            <div class="ta-detail-body">
                <div class="ta-detail-verdict-row">
                    <span class="signal-badge ${sigCls}" style="font-size:1.1em;padding:6px 16px;">${a.verdict}</span>
                    <span class="ta-detail-meta">Score ${a.score} &middot; Confidence ${a.confidence}% &middot; ${a.timeframe}</span>
                </div>
                <div class="ta-detail-prices-row">
                    <div class="ta-dp"><span>Current</span><strong>$${data.price.close[data.price.close.length - 1].toFixed(2)}</strong></div>
                    <div class="ta-dp"><span>Entry</span><strong>$${a.entry.toFixed(2)}</strong></div>
                    <div class="ta-dp ta-dp-green"><span>Target</span><strong>$${a.target.toFixed(2)}</strong></div>
                    <div class="ta-dp ta-dp-red"><span>Stop-Loss</span><strong>$${a.stop_loss.toFixed(2)}</strong></div>
                    <div class="ta-dp"><span>R/R</span><strong>${a.risk_reward.toFixed(1)}x</strong></div>
                </div>
                <div class="ta-detail-reasoning">${a.reasoning}</div>
                ${edgeSignals ? '<div class="ta-detail-edge"><h4>Advanced Signals (Edge)</h4>' + edgeSignals + '</div>' : ''}
                <div class="ta-detail-signals"><h4>Classic Indicators</h4>${signals}</div>
                <div class="ta-detail-chart-area">
                    <h4>Price &amp; Indicators</h4>
                    <canvas id="ta-detail-canvas" height="300"></canvas>
                </div>
                <div class="ta-detail-chart-area">
                    <h4>RSI (14)</h4>
                    <canvas id="ta-rsi-canvas" height="120"></canvas>
                </div>
                <div class="ta-detail-chart-area">
                    <h4>MACD (12, 26, 9)</h4>
                    <canvas id="ta-macd-canvas" height="140"></canvas>
                </div>
            </div>
        </div>`;

    overlay.style.display = "flex";
    setTimeout(() => _drawTADetailCharts(data), 50);
}

let _taPriceChart = null, _taRsiChart = null, _taMacdChart = null;

function _drawTADetailCharts(data) {
    const dates = data.dates;
    const closes = data.price.close;
    const ind = data.indicators;

    const isUp = closes[closes.length - 1] >= closes[0];
    const mainColor = isUp ? "rgba(34,197,94,1)" : "rgba(239,68,68,1)";

    if (_taPriceChart) _taPriceChart.destroy();
    const priceCanvas = document.getElementById("ta-detail-canvas");
    if (priceCanvas) {
        _taPriceChart = new Chart(priceCanvas, {
            type: "line",
            data: {
                labels: dates,
                datasets: [
                    { label: "Price", data: closes, borderColor: mainColor, borderWidth: 2, fill: false, pointRadius: 0, tension: 0.1 },
                    { label: "SMA 50", data: ind.sma_50, borderColor: "rgba(99,102,241,0.7)", borderWidth: 1.5, borderDash: [5,3], pointRadius: 0, fill: false, tension: 0.1 },
                    { label: "SMA 200", data: ind.sma_200, borderColor: "rgba(234,179,8,0.7)", borderWidth: 1.5, borderDash: [4,4], pointRadius: 0, fill: false, tension: 0.1 },
                    { label: "BB Upper", data: ind.bollinger.upper, borderColor: "rgba(156,163,175,0.3)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1 },
                    { label: "BB Lower", data: ind.bollinger.lower, borderColor: "rgba(156,163,175,0.3)", borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: "rgba(156,163,175,0.05)", tension: 0.1 },
                ],
            },
            options: _chartOpts("$"),
        });
    }

    if (_taRsiChart) _taRsiChart.destroy();
    const rsiCanvas = document.getElementById("ta-rsi-canvas");
    if (rsiCanvas) {
        const rsiData = ind.rsi;
        const upper70 = rsiData.map(() => 70);
        const lower30 = rsiData.map(() => 30);
        _taRsiChart = new Chart(rsiCanvas, {
            type: "line",
            data: {
                labels: dates,
                datasets: [
                    { label: "RSI", data: rsiData, borderColor: "rgba(168,85,247,1)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1 },
                    { label: "Overbought", data: upper70, borderColor: "rgba(239,68,68,0.3)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                    { label: "Oversold", data: lower30, borderColor: "rgba(34,197,94,0.3)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                ],
            },
            options: _chartOpts("", 0, 100),
        });
    }

    if (_taMacdChart) _taMacdChart.destroy();
    const macdCanvas = document.getElementById("ta-macd-canvas");
    if (macdCanvas) {
        const hist = ind.macd.histogram.map(v => v);
        const histColors = hist.map(v => v != null && v >= 0 ? "rgba(34,197,94,0.5)" : "rgba(239,68,68,0.5)");
        _taMacdChart = new Chart(macdCanvas, {
            type: "bar",
            data: {
                labels: dates,
                datasets: [
                    { type: "line", label: "MACD", data: ind.macd.line, borderColor: "rgba(99,102,241,1)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, order: 1 },
                    { type: "line", label: "Signal", data: ind.macd.signal, borderColor: "rgba(234,179,8,0.8)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, order: 2 },
                    { label: "Histogram", data: hist, backgroundColor: histColors, order: 3 },
                ],
            },
            options: _chartOpts(""),
        });
    }
}

function _chartOpts(prefix, sugMin, sugMax) {
    return {
        responsive: true, maintainAspectRatio: false,
        plugins: {
            legend: { display: true, position: "top", labels: { color: "#8b8fa3", font: { size: 10 } } },
            tooltip: { mode: "index", intersect: false, backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7" },
        },
        scales: {
            x: { display: true, ticks: { color: "#8b8fa3", font: { size: 9 }, maxTicksLimit: 8 }, grid: { color: "rgba(42,45,62,0.3)" } },
            y: {
                display: true,
                ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => prefix + v },
                grid: { color: "rgba(42,45,62,0.3)" },
                ...(sugMin != null ? { suggestedMin: sugMin } : {}),
                ...(sugMax != null ? { suggestedMax: sugMax } : {}),
            },
        },
        interaction: { mode: "index", intersect: false },
    };
}

/* ── Helpers ─────────────────────────────────────── */

function _taSigClass(sig) {
    if (sig === "Strong Buy" || sig === "Buy") return "signal-buy";
    if (sig === "Sell" || sig === "Strong Sell") return "signal-avoid";
    return "signal-hold";
}
