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
        <div class="ta-mood-card" data-help="ta_market_mood">
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
        { id: "hidden", icon: "🔍", helpKey: "ta_hidden_gems" },
        { id: "institutional", icon: "🏦", helpKey: "ta_smart_money" },
        { id: "momentum", icon: "⚡", helpKey: "ta_momentum" },
        { id: "swing", icon: "↗", helpKey: "ta_swing" },
        { id: "oversold", icon: "💎", helpKey: "ta_oversold" },
    ];

    el.innerHTML = tabs.map(t => {
        const pkg = packages[t.id];
        if (!pkg) return "";
        const active = t.id === _taActiveTab ? "ta-tab-active" : "";
        const count = pkg.picks ? pkg.picks.length : 0;
        return `<button class="ta-tab ${active}" onclick="switchTATab('${t.id}')">
            <span class="ta-tab-icon">${t.icon}</span>
            <span class="ta-tab-name">${pkg.name}</span>
            ${helpIcon(t.helpKey)}
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
                <span class="ta-pkg-risk ${riskCls}" data-help="ta_risk_level">${pkg.risk_level} Risk</span>
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
    if (p.has_divergence) edgeBadges += '<span class="ta-edge-badge ta-edge-div" data-help="ta_divergence">Divergence</span>';
    if (p.quiet_accumulation || p.has_institutional_signal) edgeBadges += '<span class="ta-edge-badge ta-edge-inst" data-help="ta_smart_money_badge">Smart Money</span>';
    if (p.rs_outperforming) edgeBadges += '<span class="ta-edge-badge ta-edge-rs" data-help="ta_outperformer">Outperformer</span>';
    if (p.boll_squeeze) edgeBadges += '<span class="ta-edge-badge ta-edge-squeeze" data-help="ta_squeeze">Squeeze</span>';

    return `
    <div class="ta-pick-card" data-symbol="${p.symbol}" data-stock-name="${(p.name||"").replace(/"/g,'&quot;')}" data-stock-price="${p.entry}" onclick="showTADetail('${p.symbol}')">
        <div class="ta-pick-top">
            <div class="ta-pick-sym">
                <strong>${p.symbol}</strong>
                <span class="ta-pick-name">${p.name}</span>
            </div>
            <span class="signal-badge ${sigCls}" data-help="ta_confidence">${p.verdict} ${p.confidence}%</span>
        </div>
        ${edgeBadges ? '<div class="ta-edge-badges">' + edgeBadges + '</div>' : ''}
        <div class="ta-pick-prices">
            <div data-help="ta_entry"><span class="ta-lbl">Entry</span><span class="ta-val">$${p.entry.toFixed(2)}</span></div>
            <div data-help="ta_target"><span class="ta-lbl">Target</span><span class="ta-val ta-green">$${p.target.toFixed(2)}</span></div>
            <div data-help="ta_stop_loss"><span class="ta-lbl">Stop</span><span class="ta-val ta-red">$${p.stop_loss.toFixed(2)}</span></div>
            <div data-help="ta_risk_reward"><span class="ta-lbl">R/R</span><span class="ta-val">${p.risk_reward.toFixed(1)}x</span></div>
        </div>
        <div class="ta-pick-spark"><canvas id="ta-spark-${p.symbol}" width="260" height="50"></canvas></div>
        <ul class="ta-pick-signals">${signalsList}</ul>
        <div class="ta-pick-foot">
            <span class="ta-pick-sector">${p.sector}</span>
            <span class="ta-pick-score" data-help="ta_score">Score ${p.score}</span>
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
let _taDetailLoading = false;

async function showTADetail(symbol) {
    if (_taDetailLoading) return; // debounce
    _taDetailLoading = true;
    // Show loading overlay immediately
    _showTALoadingOverlay(symbol);
    try {
        const data = await api.get(`/api/trading/${symbol}`);
        _renderTADetailModal(data);
    } catch (e) {
        console.warn("Detail fetch failed for", symbol, e);
        const ov = document.getElementById("ta-detail-overlay");
        if (ov) ov.style.display = "none";
    } finally {
        _taDetailLoading = false;
    }
}

function _showTALoadingOverlay(symbol) {
    let overlay = document.getElementById("ta-detail-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "ta-detail-overlay";
        overlay.className = "modal-overlay";
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.style.display = "none"; _taDetailLoading = false; } };
        document.body.appendChild(overlay);
    }
    overlay.innerHTML = `<div class="modal ta-detail-modal" onclick="event.stopPropagation()">
        <div class="ta-loading-state"><div class="ta-loading-spinner"></div><span>Analyzing ${symbol}...</span></div>
    </div>`;
    overlay.style.display = "flex";
}

/* Chart view mode: 'line' or 'candle' */
let _taChartMode = 'candle';
let _taOverlayToggles = { sma: true, bollinger: true, vwap: false, keltner: false, sar: false, ichimoku: false };
let _taCurrentData = null;

function _renderTADetailModal(data) {
    _taCurrentData = data;
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
    const patterns = data.patterns || {};
    const chartPats = patterns.chart_patterns || [];
    const candlePats = patterns.candlestick_patterns || [];
    const gaps = patterns.gaps || [];

    /* ── Decision Breakdown waterfall HTML ── */
    const breakdown = data.decision_breakdown || [];
    const breakdownHTML = _buildDecisionBreakdownHTML(breakdown, a);

    /* ── Pattern badges ── */
    const patBadges = _buildPatternBadgesHTML(chartPats, candlePats, gaps, data);

    /* ── Signal rows ── */
    const edgeSignals = (a.edge_signals || []).map(s => {
        const cls = s.direction === "bullish" ? "ta-sig-bull" : s.direction === "bearish" ? "ta-sig-bear" : "ta-sig-neut";
        return `<div class="ta-sig-row ta-sig-edge ${cls}"><strong>★ ${s.name}</strong>: ${s.detail}</div>`;
    }).join("");

    const signals = (a.signals || []).map(s => {
        const cls = s.direction === "bullish" ? "ta-sig-bull" : s.direction === "bearish" ? "ta-sig-bear" : "ta-sig-neut";
        return `<div class="ta-sig-row ${cls}"><strong>${s.name}</strong>: ${s.detail}</div>`;
    }).join("");

    /* ── Overlay toggles ── */
    const overlayBtns = [
        { key: 'sma', label: 'SMA', color: '#6366f1' },
        { key: 'bollinger', label: 'Bollinger', color: '#9ca3af' },
        { key: 'vwap', label: 'VWAP', color: '#06b6d4' },
        { key: 'keltner', label: 'Keltner', color: '#f59e0b' },
        { key: 'sar', label: 'SAR', color: '#ec4899' },
        { key: 'ichimoku', label: 'Ichimoku', color: '#8b5cf6' },
    ].map(b => {
        const active = _taOverlayToggles[b.key] ? 'ta-ovl-active' : '';
        return `<button class="ta-ovl-btn ${active}" style="--ovl-color:${b.color}" onclick="_toggleOverlay('${b.key}')">${b.label}</button>`;
    }).join("");

    const squeeze = data.ttm_squeeze || {};
    const squeezeHTML = squeeze.squeeze_on || squeeze.squeeze_fired
        ? `<div class="ta-squeeze-badge ${squeeze.squeeze_fired ? 'ta-squeeze-fired' : 'ta-squeeze-on'}">${squeeze.detail}</div>` : '';

    overlay.innerHTML = `
        <div class="modal ta-detail-modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2>${data.symbol} — ${data.name}</h2>
                <button class="modal-close" onclick="document.getElementById('ta-detail-overlay').style.display='none'">&times;</button>
            </div>
            <div class="ta-detail-body">
                <!-- Verdict row -->
                <div class="ta-detail-verdict-row">
                    <span class="signal-badge ${sigCls}" style="font-size:1.1em;padding:6px 16px;">${a.verdict}</span>
                    <span class="ta-detail-meta">Score ${a.score} · Confidence ${a.confidence}% · ${a.timeframe}</span>
                </div>
                <div class="ta-detail-prices-row">
                    <div class="ta-dp"><span>Current</span><strong>$${data.price.close[data.price.close.length - 1].toFixed(2)}</strong></div>
                    <div class="ta-dp"><span>Entry</span><strong>$${a.entry.toFixed(2)}</strong></div>
                    <div class="ta-dp ta-dp-green"><span>Target</span><strong>$${a.target.toFixed(2)}</strong></div>
                    <div class="ta-dp ta-dp-red"><span>Stop</span><strong>$${a.stop_loss.toFixed(2)}</strong></div>
                    <div class="ta-dp"><span>R/R</span><strong>${a.risk_reward.toFixed(1)}x</strong></div>
                </div>

                ${squeezeHTML}

                <!-- ★ DECISION BREAKDOWN — "Why this score?" ★ -->
                <div class="ta-decision-section">
                    <h4>Why This Score? — Decision Breakdown</h4>
                    <div class="ta-decision-desc">Each bar shows how an indicator pushed the score up (green) or down (red). The final score is the sum of all weighted contributions.</div>
                    <div class="ta-waterfall-wrap">
                        <canvas id="ta-waterfall-canvas" height="160"></canvas>
                    </div>
                    ${breakdownHTML}
                </div>

                <!-- Pattern badges -->
                ${patBadges}

                <!-- Price Chart with overlays -->
                <div class="ta-detail-chart-area">
                    <div class="ta-chart-header">
                        <h4>Price Chart</h4>
                        <div class="ta-chart-controls">
                            <button class="ta-chart-mode-btn ${_taChartMode === 'candle' ? 'active' : ''}" onclick="_setChartMode('candle')">Candlestick</button>
                            <button class="ta-chart-mode-btn ${_taChartMode === 'line' ? 'active' : ''}" onclick="_setChartMode('line')">Line</button>
                        </div>
                    </div>
                    <div class="ta-overlay-toggles">${overlayBtns}</div>
                    <div id="ta-chart-pattern-badge"></div>
                    <canvas id="ta-detail-canvas" height="220"></canvas>
                </div>

                <!-- RSI -->
                <div class="ta-detail-chart-area">
                    <h4>RSI (14)</h4>
                    <canvas id="ta-rsi-canvas" height="80"></canvas>
                </div>

                <!-- MACD -->
                <div class="ta-detail-chart-area">
                    <h4>MACD (12, 26, 9)</h4>
                    <canvas id="ta-macd-canvas" height="90"></canvas>
                </div>

                <!-- Stochastic -->
                <div class="ta-detail-chart-area">
                    <h4>Stochastic %K / %D</h4>
                    <canvas id="ta-stoch-canvas" height="80"></canvas>
                </div>

                <!-- ADX -->
                <div class="ta-detail-chart-area">
                    <h4>ADX — Trend Strength</h4>
                    <canvas id="ta-adx-canvas" height="80"></canvas>
                </div>

                <!-- Signals expandable -->
                ${edgeSignals ? '<div class="ta-detail-edge"><h4>Advanced Signals</h4>' + edgeSignals + '</div>' : ''}
                <div class="ta-detail-signals"><h4>Classic Indicators</h4>${signals}</div>

                <div class="ta-detail-reasoning"><strong>Summary:</strong> ${a.reasoning}</div>
            </div>
        </div>`;

    overlay.style.display = "flex";
    setTimeout(() => _drawAllTACharts(data), 50);
}

/* ── Decision Breakdown HTML builder ───────────── */
function _buildDecisionBreakdownHTML(breakdown, action) {
    if (!breakdown || !breakdown.length) return '';
    let rows = '';
    for (const b of breakdown) {
        const pct = Math.abs(b.weighted_score) / 0.5 * 100; // scale: 0.5 = full bar
        const barPct = Math.min(pct, 100);
        const cls = b.direction === 'bullish' ? 'ta-wb-bull' : b.direction === 'bearish' ? 'ta-wb-bear' : 'ta-wb-neut';
        const catIcon = b.category === 'advanced' ? '★ ' : '';
        rows += `<div class="ta-wb-row">
            <span class="ta-wb-name" title="${b.detail}">${catIcon}${b.name}</span>
            <div class="ta-wb-bar-track">
                <div class="ta-wb-bar ${cls}" style="width:${barPct}%"></div>
            </div>
            <span class="ta-wb-val ${cls}">${b.weighted_score > 0 ? '+' : ''}${b.weighted_score.toFixed(3)}</span>
        </div>`;
    }
    return `<div class="ta-wb-container">${rows}</div>`;
}

/* ── Pattern Badges HTML builder ───────────────── */
function _buildPatternBadgesHTML(chartPats, candlePats, gaps, data) {
    const parts = [];
    const fib = data.fibonacci || {};
    const cup = data.cup_and_handle || {};

    if (fib.nearest_support) parts.push(`<span class="ta-pattern-tag ta-tag-support">▾ Support $${fib.nearest_support.toFixed(2)}</span>`);
    if (fib.nearest_resistance) parts.push(`<span class="ta-pattern-tag ta-tag-resist">▴ Resistance $${fib.nearest_resistance.toFixed(2)}</span>`);
    if (cup && cup.detected) parts.push(`<span class="ta-pattern-tag ta-tag-pattern">☕ Cup & Handle (${cup.confidence}%)</span>`);

    for (const p of chartPats) {
        const cls = p.direction === 'bullish' ? 'ta-tag-support' : p.direction === 'bearish' ? 'ta-tag-resist' : 'ta-tag-pattern';
        const icon = p.direction === 'bullish' ? '▴' : p.direction === 'bearish' ? '▾' : '◆';
        parts.push(`<span class="ta-pattern-tag ${cls}" title="${p.detail}">${icon} ${p.name} (${p.confidence}%)</span>`);
    }

    for (const c of candlePats.slice(-6)) {
        const cls = c.direction === 'bullish' ? 'ta-tag-candle-bull' : c.direction === 'bearish' ? 'ta-tag-candle-bear' : 'ta-tag-pattern';
        parts.push(`<span class="ta-pattern-tag ${cls}" title="${c.detail}">${c.pattern}</span>`);
    }

    for (const g of gaps) {
        const cls = g.direction === 'up' ? 'ta-tag-gap-up' : 'ta-tag-gap-down';
        parts.push(`<span class="ta-pattern-tag ${cls}" title="${g.label}">Gap ${g.direction === 'up' ? '↑' : '↓'} ${g.gap_pct}%</span>`);
    }

    if (!parts.length) return '';
    return `<div class="ta-pattern-badges-section"><h4>Detected Patterns</h4><div class="ta-pattern-badges-wrap">${parts.join(' ')}</div></div>`;
}

/* ── Overlay toggle ─────────────────────────────── */
function _toggleOverlay(key) {
    _taOverlayToggles[key] = !_taOverlayToggles[key];
    if (_taCurrentData) _renderTADetailModal(_taCurrentData);
}
function _setChartMode(mode) {
    _taChartMode = mode;
    if (_taCurrentData) _renderTADetailModal(_taCurrentData);
}

/* ════════════════════════════════════════════════════
   CHART DRAWING ENGINE — all charts
   ════════════════════════════════════════════════════ */

let _taPriceChart = null, _taRsiChart = null, _taMacdChart = null, _taStochChart = null, _taAdxChart = null, _taWaterfallChart = null;

function _drawAllTACharts(data) {
    _drawWaterfallChart(data);
    _drawPriceChart(data);
    _drawRSIChart(data);
    _drawMACDChart(data);
    _drawStochChart(data);
    _drawADXChart(data);
}

/* ── Waterfall "Decision" chart ─────────────────── */
function _drawWaterfallChart(data) {
    const breakdown = data.decision_breakdown || [];
    if (!breakdown.length) return;
    if (_taWaterfallChart) _taWaterfallChart.destroy();

    const canvas = document.getElementById("ta-waterfall-canvas");
    if (!canvas) return;

    const labels = breakdown.map(b => b.name);
    const values = breakdown.map(b => b.weighted_score);
    const bgColors = values.map(v => v > 0 ? 'rgba(34,197,94,0.7)' : v < 0 ? 'rgba(239,68,68,0.7)' : 'rgba(234,179,8,0.4)');
    const borderColors = values.map(v => v > 0 ? 'rgba(34,197,94,1)' : v < 0 ? 'rgba(239,68,68,1)' : 'rgba(234,179,8,1)');

    _taWaterfallChart = new Chart(canvas, {
        type: 'bar',
        data: { labels, datasets: [{ data: values, backgroundColor: bgColors, borderColor: borderColors, borderWidth: 1 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const b = breakdown[ctx.dataIndex];
                            return `${b.name}: ${b.weighted_score > 0 ? '+' : ''}${b.weighted_score.toFixed(3)} (${b.detail})`;
                        }
                    },
                    backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7",
                },
            },
            scales: {
                x: { ticks: { color: "#8b8fa3", font: { size: 9 }, maxRotation: 45 }, grid: { display: false } },
                y: { ticks: { color: "#8b8fa3", font: { size: 9 } }, grid: { color: "rgba(42,45,62,0.3)" } },
            },
        },
    });
}

/* ── Price chart (candlestick OR line) with overlays ── */
function _drawPriceChart(data) {
    const dates = data.dates;
    const closes = data.price.close;
    const highs = data.price.high;
    const lows = data.price.low;
    const opens = data.price.open || closes;
    const ind = data.indicators;
    const fib = data.fibonacci || {};
    const isUp = closes[closes.length - 1] >= closes[0];
    const mainColor = isUp ? "rgba(34,197,94,1)" : "rgba(239,68,68,1)";

    if (_taPriceChart) _taPriceChart.destroy();
    const canvas = document.getElementById("ta-detail-canvas");
    if (!canvas) return;

    const datasets = [];

    /* ── Main price data ── */
    if (_taChartMode === 'candle') {
        // Build OHLC dataset for candlestick rendering via floating bars
        const candleColors = [];
        const candleData = [];
        const wickData = new Array(dates.length).fill(null);
        for (let i = 0; i < dates.length; i++) {
            const bull = closes[i] >= opens[i];
            candleColors.push(bull ? 'rgba(34,197,94,0.85)' : 'rgba(239,68,68,0.85)');
            candleData.push([opens[i], closes[i]]);
        }
        datasets.push({
            type: 'bar',
            label: 'Price',
            data: candleData,
            backgroundColor: candleColors,
            borderColor: candleColors,
            borderWidth: 1,
            borderSkipped: false,
            barPercentage: 0.6,
            order: 5,
        });
        // Wicks as thin bars (high-low)
        const wickColors = candleColors.map(c => c.replace('0.85', '0.6'));
        datasets.push({
            type: 'bar',
            label: 'Wick',
            data: dates.map((_, i) => [lows[i], highs[i]]),
            backgroundColor: wickColors,
            borderColor: wickColors,
            borderWidth: 0.5,
            borderSkipped: false,
            barPercentage: 0.08,
            order: 6,
        });
    } else {
        datasets.push({
            label: "Price", data: closes, borderColor: mainColor, borderWidth: 2,
            fill: false, pointRadius: 0, tension: 0.1, order: 1,
        });
    }

    /* ── Optional overlays ── */
    const t = _taOverlayToggles;
    if (t.sma && ind.sma_50) {
        datasets.push({ label: "SMA 50", data: ind.sma_50, borderColor: "rgba(99,102,241,0.7)", borderWidth: 1.5, borderDash: [5,3], pointRadius: 0, fill: false, tension: 0.1, order: 2 });
        datasets.push({ label: "SMA 200", data: ind.sma_200, borderColor: "rgba(234,179,8,0.7)", borderWidth: 1.5, borderDash: [4,4], pointRadius: 0, fill: false, tension: 0.1, order: 2 });
    }
    if (t.bollinger && ind.bollinger) {
        datasets.push({ label: "BB Upper", data: ind.bollinger.upper, borderColor: "rgba(156,163,175,0.35)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1, order: 3 });
        datasets.push({ label: "BB Lower", data: ind.bollinger.lower, borderColor: "rgba(156,163,175,0.35)", borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: "rgba(156,163,175,0.04)", tension: 0.1, order: 3 });
    }
    if (t.vwap && ind.vwap) {
        datasets.push({ label: "VWAP", data: ind.vwap, borderColor: "rgba(6,182,212,0.8)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, order: 2 });
    }
    if (t.keltner && ind.keltner) {
        datasets.push({ label: "KC Upper", data: ind.keltner.upper, borderColor: "rgba(245,158,11,0.5)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false, tension: 0.1, order: 3 });
        datasets.push({ label: "KC Lower", data: ind.keltner.lower, borderColor: "rgba(245,158,11,0.5)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: "+1", backgroundColor: "rgba(245,158,11,0.03)", tension: 0.1, order: 3 });
    }
    if (t.sar && ind.parabolic_sar) {
        const sarData = ind.parabolic_sar.sar;
        const sarColors = ind.parabolic_sar.trend.map(t => t > 0 ? 'rgba(34,197,94,0.8)' : 'rgba(239,68,68,0.8)');
        datasets.push({
            label: "SAR", data: sarData, pointBackgroundColor: sarColors,
            pointBorderColor: sarColors, pointRadius: 2, pointStyle: 'circle',
            showLine: false, fill: false, order: 2,
        });
    }
    if (t.ichimoku && ind.ichimoku) {
        const ichi = ind.ichimoku;
        datasets.push({ label: "Tenkan", data: ichi.tenkan, borderColor: "rgba(139,92,246,0.6)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1, order: 3 });
        datasets.push({ label: "Kijun", data: ichi.kijun, borderColor: "rgba(236,72,153,0.6)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1, order: 3 });
        datasets.push({ label: "Senkou A", data: ichi.senkou_a, borderColor: "rgba(34,197,94,0.3)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1, order: 4 });
        datasets.push({ label: "Senkou B", data: ichi.senkou_b, borderColor: "rgba(239,68,68,0.3)", borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: "rgba(139,92,246,0.04)", tension: 0.1, order: 4 });
    }

    /* ── Support / Resistance lines ─────── */
    if (fib.nearest_support) {
        datasets.push({ label: `Support $${fib.nearest_support.toFixed(2)}`, data: dates.map(() => fib.nearest_support), borderColor: "rgba(34,197,94,0.6)", borderWidth: 1.5, borderDash: [8,4], pointRadius: 0, fill: false, tension: 0, order: 3 });
    }
    if (fib.nearest_resistance) {
        datasets.push({ label: `Resist $${fib.nearest_resistance.toFixed(2)}`, data: dates.map(() => fib.nearest_resistance), borderColor: "rgba(239,68,68,0.6)", borderWidth: 1.5, borderDash: [8,4], pointRadius: 0, fill: false, tension: 0, order: 3 });
    }

    /* ── Cup & Handle markers ──────────── */
    const cup = data.cup_and_handle;
    if (cup && cup.detected) {
        const cupPts = new Array(dates.length).fill(null);
        if (cup.cup_bottom_idx != null) cupPts[cup.cup_bottom_idx] = closes[cup.cup_bottom_idx];
        if (cup.left_rim_idx != null) cupPts[cup.left_rim_idx] = closes[cup.left_rim_idx];
        if (cup.right_rim_idx != null) cupPts[cup.right_rim_idx] = closes[cup.right_rim_idx];
        if (cup.handle_low_idx != null) cupPts[cup.handle_low_idx] = closes[cup.handle_low_idx];
        datasets.push({
            label: "Cup & Handle", data: cupPts, borderColor: "rgba(251,191,36,0)",
            pointBackgroundColor: "rgba(251,191,36,1)", pointBorderColor: "rgba(251,191,36,1)",
            pointRadius: cupPts.map(v => v != null ? 6 : 0),
            pointStyle: cupPts.map((v, i) => { if (v == null) return "circle"; if (i === cup.cup_bottom_idx) return "triangle"; if (i === cup.handle_low_idx) return "rectRot"; return "circle"; }),
            fill: false, showLine: false, tension: 0, order: 1,
        });
        if (cup.rim_level) {
            datasets.push({ label: `Rim $${cup.rim_level.toFixed(2)}`, data: dates.map(() => cup.rim_level), borderColor: "rgba(251,191,36,0.5)", borderWidth: 1, borderDash: [4,4], pointRadius: 0, fill: false, tension: 0, order: 3 });
        }
    }

    /* ── Chart pattern viz points (Double Top, H&S, etc.) ── */
    const chartPats = (data.patterns || {}).chart_patterns || [];
    for (const pat of chartPats) {
        const vizPts = pat.viz_points || [];
        if (!vizPts.length) continue;
        const ptData = new Array(dates.length).fill(null);
        const ptLabels = new Array(dates.length).fill('');
        const patColor = pat.direction === 'bullish' ? 'rgba(34,197,94,0.9)' : pat.direction === 'bearish' ? 'rgba(239,68,68,0.9)' : 'rgba(251,191,36,0.9)';
        for (const vp of vizPts) {
            if (vp.idx >= 0 && vp.idx < dates.length) {
                ptData[vp.idx] = vp.value;
                ptLabels[vp.idx] = vp.label;
            }
        }
        datasets.push({
            label: pat.name, data: ptData,
            pointBackgroundColor: patColor, pointBorderColor: patColor,
            pointRadius: ptData.map(v => v != null ? 7 : 0),
            pointStyle: pat.direction === 'bullish' ? 'triangle' : pat.direction === 'bearish' ? 'triangle' : 'rectRot',
            pointRotation: pat.direction === 'bearish' ? 180 : 0,
            showLine: true, borderColor: patColor.replace('0.9', '0.3'), borderWidth: 1.5,
            borderDash: [4, 3], fill: false, tension: 0, order: 1,
        });
    }

    /* ── Candlestick pattern markers ── */
    const candlePats = (data.patterns || {}).candlestick_patterns || [];
    if (candlePats.length) {
        const candleMarkers = new Array(dates.length).fill(null);
        const candleColors = new Array(dates.length).fill('transparent');
        const candleStyles = new Array(dates.length).fill('circle');
        for (const cp of candlePats) {
            if (cp.idx >= 0 && cp.idx < dates.length) {
                candleMarkers[cp.idx] = cp.direction === 'bullish' ? lows[cp.idx] * 0.995 : highs[cp.idx] * 1.005;
                candleColors[cp.idx] = cp.direction === 'bullish' ? 'rgba(34,197,94,1)' : cp.direction === 'bearish' ? 'rgba(239,68,68,1)' : 'rgba(234,179,8,1)';
                candleStyles[cp.idx] = cp.direction === 'bullish' ? 'triangle' : cp.direction === 'bearish' ? 'triangle' : 'star';
            }
        }
        datasets.push({
            label: "Candle Signals", data: candleMarkers,
            pointBackgroundColor: candleColors, pointBorderColor: candleColors,
            pointRadius: candleMarkers.map(v => v != null ? 5 : 0),
            pointStyle: candleStyles,
            pointRotation: candleMarkers.map((v, i) => candlePats.find(c => c.idx === i && c.direction === 'bearish') ? 180 : 0),
            showLine: false, fill: false, order: 0,
        });
    }

    _taPriceChart = new Chart(canvas, {
        type: _taChartMode === 'candle' ? 'bar' : 'line',
        data: { labels: dates, datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: "top", labels: { color: "#8b8fa3", font: { size: 9 }, boxWidth: 10, filter: item => item.text !== 'Wick' } },
                tooltip: {
                    mode: "index", intersect: false,
                    backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7",
                    callbacks: {
                        afterBody: (ctx) => {
                            const idx = ctx[0]?.dataIndex;
                            if (idx == null) return '';
                            const cp = candlePats.filter(c => c.idx === idx);
                            return cp.length ? '\n' + cp.map(c => `📌 ${c.pattern}: ${c.detail}`).join('\n') : '';
                        },
                    },
                },
            },
            scales: {
                x: { display: true, ticks: { color: "#8b8fa3", font: { size: 9 }, maxTicksLimit: 8 }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { display: true, ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => '$' + v }, grid: { color: "rgba(42,45,62,0.3)" } },
            },
            interaction: { mode: "index", intersect: false },
        },
    });

    // Update pattern badge area
    const badgeEl = document.getElementById("ta-chart-pattern-badge");
    if (badgeEl) badgeEl.innerHTML = ''; // badges are now in their own section
}

/* ── RSI chart ──────────────────────────────────── */
function _drawRSIChart(data) {
    if (_taRsiChart) _taRsiChart.destroy();
    const canvas = document.getElementById("ta-rsi-canvas");
    if (!canvas) return;
    const rsiData = data.indicators.rsi;
    const dates = data.dates;
    _taRsiChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: dates,
            datasets: [
                { label: "RSI", data: rsiData, borderColor: "rgba(168,85,247,1)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "Overbought", data: rsiData.map(() => 70), borderColor: "rgba(239,68,68,0.3)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                { label: "Oversold", data: rsiData.map(() => 30), borderColor: "rgba(34,197,94,0.3)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
            ],
        },
        options: _chartOpts("", 0, 100),
    });
}

/* ── MACD chart ─────────────────────────────────── */
function _drawMACDChart(data) {
    if (_taMacdChart) _taMacdChart.destroy();
    const canvas = document.getElementById("ta-macd-canvas");
    if (!canvas) return;
    const ind = data.indicators;
    const hist = ind.macd.histogram.map(v => v);
    const histColors = hist.map(v => v != null && v >= 0 ? "rgba(34,197,94,0.5)" : "rgba(239,68,68,0.5)");
    _taMacdChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: data.dates,
            datasets: [
                { type: "line", label: "MACD", data: ind.macd.line, borderColor: "rgba(99,102,241,1)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, order: 1 },
                { type: "line", label: "Signal", data: ind.macd.signal, borderColor: "rgba(234,179,8,0.8)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, order: 2 },
                { label: "Histogram", data: hist, backgroundColor: histColors, order: 3 },
            ],
        },
        options: _chartOpts(""),
    });
}

/* ── Stochastic chart ───────────────────────────── */
function _drawStochChart(data) {
    if (_taStochChart) _taStochChart.destroy();
    const canvas = document.getElementById("ta-stoch-canvas");
    if (!canvas || !data.indicators.stochastic) return;
    const stoch = data.indicators.stochastic;
    _taStochChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.dates,
            datasets: [
                { label: "%K", data: stoch.k, borderColor: "rgba(99,102,241,1)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "%D", data: stoch.d, borderColor: "rgba(234,179,8,0.8)", borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "Overbought", data: stoch.k.map(() => 80), borderColor: "rgba(239,68,68,0.25)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
                { label: "Oversold", data: stoch.k.map(() => 20), borderColor: "rgba(34,197,94,0.25)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
            ],
        },
        options: _chartOpts("", 0, 100),
    });
}

/* ── ADX chart ──────────────────────────────────── */
function _drawADXChart(data) {
    if (_taAdxChart) _taAdxChart.destroy();
    const canvas = document.getElementById("ta-adx-canvas");
    if (!canvas || !data.indicators.adx) return;
    const adx = data.indicators.adx;
    _taAdxChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.dates,
            datasets: [
                { label: "ADX", data: adx.adx, borderColor: "rgba(168,85,247,1)", borderWidth: 2, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "+DI", data: adx.plus_di, borderColor: "rgba(34,197,94,0.7)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "-DI", data: adx.minus_di, borderColor: "rgba(239,68,68,0.7)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.1 },
                { label: "Trending", data: (adx.adx || []).map(() => 25), borderColor: "rgba(234,179,8,0.3)", borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: false },
            ],
        },
        options: _chartOpts(""),
    });
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
