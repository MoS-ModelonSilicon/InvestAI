let detailChart = null;
let _currentDetailSymbol = null;
let _spyOverlayActive = false;
let _lastHistory = null;
let _lastSpyHistory = null;
let _candleMode = false;
let _currentPatterns = null;
let _currentCurrency = "USD";
let _tfFetchId = 0;              // debounce: only the latest fetch renders
const _historyCache = new Map();  // client-side cache: "SYM:period:interval" → {history, patterns, ts}

/* ── Market session shading plugin ─────────────────────────── */
const sessionZonePlugin = {
    id: "sessionZones",
    beforeDraw(chart) {
        const sessions = chart.options._sessions;
        if (!sessions || !sessions.length) return;
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const { top, bottom } = chart.chartArea;
        if (!xAxis || top == null) return;

        // Pre-market: blue tint, Post-market: purple tint
        const colors = { pre: "rgba(59,130,246,0.06)", post: "rgba(168,85,247,0.06)" };

        let i = 0;
        while (i < sessions.length) {
            const s = sessions[i];
            if (s === "regular") { i++; continue; }
            // Find contiguous run of same session type
            let j = i;
            while (j < sessions.length && sessions[j] === s) j++;
            const x0 = xAxis.getPixelForValue(i);
            const x1 = xAxis.getPixelForValue(j - 1);
            if (colors[s]) {
                ctx.save();
                ctx.fillStyle = colors[s];
                ctx.fillRect(Math.min(x0, x1), top, Math.abs(x1 - x0) + 1, bottom - top);
                ctx.restore();
            }
            i = j;
        }
    },
};
const sessionZoneTimePlugin = {
    id: "sessionZonesTime",
    beforeDraw(chart) {
        const sessions = chart.options._sessions;
        const timestamps = chart.options._timestamps;
        if (!sessions || !sessions.length || !timestamps) return;
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const { top, bottom } = chart.chartArea;
        if (!xAxis || top == null) return;

        const colors = { pre: "rgba(59,130,246,0.06)", post: "rgba(168,85,247,0.06)" };

        let i = 0;
        while (i < sessions.length) {
            const s = sessions[i];
            if (s === "regular") { i++; continue; }
            let j = i;
            while (j < sessions.length && sessions[j] === s) j++;
            const x0 = xAxis.getPixelForValue(timestamps[i]);
            const x1 = xAxis.getPixelForValue(timestamps[j - 1]);
            if (colors[s]) {
                ctx.save();
                ctx.fillStyle = colors[s];
                ctx.fillRect(Math.min(x0, x1), top, Math.abs(x1 - x0) + 1, bottom - top);
                ctx.restore();
            }
            i = j;
        }
    },
};

const LINE_TF = [
    { label: "1M", period: "1mo", interval: "1d" },
    { label: "3M", period: "3mo", interval: "1d" },
    { label: "6M", period: "6mo", interval: "1d" },
    { label: "1Y", period: "1y", interval: "1d" },
    { label: "5Y", period: "5y", interval: "1wk" },
];
const CANDLE_TF = [
    { label: "1m", period: "1d", interval: "1m" },
    { label: "3m", period: "5d", interval: "3m" },
    { label: "5m", period: "5d", interval: "5m" },
    { label: "15m", period: "5d", interval: "15m" },
    { label: "1H", period: "3mo", interval: "1h" },
    { label: "1D", period: "1y", interval: "1d" },
    { label: "1W", period: "5y", interval: "1wk" },
    { label: "1M", period: "5y", interval: "1mo" },
];

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
    _currentCurrency = info.currency || "USD";
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
            <div class="sd-price">${fmt(info.price, info.currency)}</div>
            ${info.year_change != null ? `<div class="sd-change ${ycCls}">${ycSign}${info.year_change.toFixed(1)}% 1Y</div>` : ""}
        </div>
    </div>

    <div class="sd-actions">
        <button class="btn btn-primary btn-sm${isInWatchlist(info.symbol) ? ' wl-watched' : ''}" data-wl-symbol="${info.symbol}" onclick="addToWatchlistFromDetail('${info.symbol}','${(info.name || "").replace(/'/g, "\\'")}')">${isInWatchlist(info.symbol) ? '✓ Watching' : '+ Watchlist'}</button>
        <button class="btn btn-sm" onclick="openAddHoldingModal('${info.symbol}','${(info.name || "").replace(/'/g, "\\'")}', ${info.price})">+ Portfolio</button>
        <button class="btn btn-sm btn-ta" onclick="showTADetail('${info.symbol}')">🔬 Technical Analysis</button>
    </div>

    <div class="sd-chart-section">
        <div class="sd-chart-controls">
            <div class="sd-chart-type">
                <button class="sd-ct active" id="ct-line" onclick="setChartType('line','${info.symbol}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 8 13 13 9 9 2 16"/></svg>
                </button>
                <button class="sd-ct" id="ct-candle" onclick="setChartType('candle','${info.symbol}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="9" y1="2" x2="9" y2="6"/><rect x="6" y="6" width="6" height="10" rx="1"/><line x1="9" y1="16" x2="9" y2="22"/><line x1="17" y1="4" x2="17" y2="8"/><rect x="14" y="8" width="6" height="8" rx="1"/><line x1="17" y1="16" x2="17" y2="20"/></svg>
                </button>
            </div>
            <div class="sd-timeframes" id="sd-timeframes"></div>
            <button class="sd-tf sd-spy-toggle" id="spy-toggle-btn" onclick="toggleSpyOverlay('${info.symbol}')" style="margin-left:auto">vs SPY</button>
        </div>
        <div class="sd-chart-wrapper">
            <canvas id="sd-price-chart"></canvas>
        </div>
        <div id="sd-patterns-legend" class="sd-patterns-legend"></div>
    </div>`;

    // Key Stats
    const stats = [
        ["Market Cap", info.market_cap ? formatMarketCapLocal(info.market_cap, info.currency) : "N/A"],
        ["P/E (TTM)", info.pe_ratio != null ? info.pe_ratio.toFixed(1) : "—"],
        ["Forward P/E", info.forward_pe != null ? info.forward_pe.toFixed(1) : "—"],
        ["Div Yield", info.dividend_yield != null ? info.dividend_yield.toFixed(2) + "%" : "—"],
        ["Beta", info.beta != null ? info.beta.toFixed(2) : "—"],
        ["52W High", info.week52_high != null ? fmt(info.week52_high, info.currency) : "—"],
        ["52W Low", info.week52_low != null ? fmt(info.week52_low, info.currency) : "—"],
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
                <div class="analyst-item"><span class="analyst-label">Current</span><span class="analyst-value">${fmt(info.price, info.currency)}</span></div>
                <div class="analyst-item"><span class="analyst-label">Avg Target</span><span class="analyst-value" style="color:${upsideColor}">${fmt(at.target_mean, info.currency)}</span></div>
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
    _candleMode = false;
    _currentPatterns = null;
    _historyCache.clear();
    buildTimeframeButtons(info.symbol);
    if (history && history.close && history.close.length > 0) {
        _lastHistory = history;
        renderDetailChart(history);
    }
}

function buildTimeframeButtons(symbol) {
    const el = document.getElementById("sd-timeframes");
    if (!el) return;
    const tfs = _candleMode ? CANDLE_TF : LINE_TF;
    const defIdx = _candleMode ? 4 : 0;
    el.innerHTML = tfs.map((tf, i) =>
        `<button class="sd-tf${i === defIdx ? ' active' : ''}" onclick="changeTimeframe('${symbol}','${tf.period}','${tf.interval}',this)">${tf.label}</button>`
    ).join("");
}

function setChartType(type, symbol) {
    _candleMode = type === "candle";
    document.getElementById("ct-line").classList.toggle("active", !_candleMode);
    document.getElementById("ct-candle").classList.toggle("active", _candleMode);
    const spyBtn = document.getElementById("spy-toggle-btn");
    if (spyBtn) spyBtn.style.display = _candleMode ? "none" : "";
    _spyOverlayActive = false;
    _currentPatterns = null;
    buildTimeframeButtons(symbol);
    const tfs = _candleMode ? CANDLE_TF : LINE_TF;
    const def = tfs[_candleMode ? 4 : 0];
    changeTimeframe(symbol, def.period, def.interval, document.querySelector("#sd-timeframes .sd-tf.active"));
}

function _showChartLoading() {
    const wrap = document.querySelector(".sd-chart-wrapper");
    if (!wrap) return;
    let overlay = wrap.querySelector(".sd-chart-loading");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.className = "sd-chart-loading";
        overlay.innerHTML = '<div class="spinner" style="width:24px;height:24px"></div>';
        wrap.style.position = "relative";
        wrap.appendChild(overlay);
    }
    overlay.style.display = "flex";
}

function _hideChartLoading() {
    const overlay = document.querySelector(".sd-chart-loading");
    if (overlay) overlay.style.display = "none";
}

function _showChartEmpty(msg) {
    const wrap = document.querySelector(".sd-chart-wrapper");
    if (!wrap) return;
    let el = wrap.querySelector(".sd-chart-empty");
    if (!el) {
        el = document.createElement("div");
        el.className = "sd-chart-empty";
        wrap.appendChild(el);
    }
    el.textContent = msg || "No data available for this timeframe";
    el.style.display = "flex";
}

function _hideChartEmpty() {
    const el = document.querySelector(".sd-chart-empty");
    if (el) el.style.display = "none";
}

function _getCacheKey(symbol, period, interval) {
    return `${symbol}:${period}:${interval}`;
}

async function changeTimeframe(symbol, period, interval, btn) {
    document.querySelectorAll("#sd-timeframes .sd-tf").forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    _lastSpyHistory = null;

    const fetchId = ++_tfFetchId;  // debounce: ignore stale fetches

    // Check client-side cache first (instant switch for previously viewed timeframes)
    const cacheKey = _getCacheKey(symbol, period, interval);
    const cached = _historyCache.get(cacheKey);
    const CACHE_TTL = _candleMode && ["1m", "3m", "5m", "15m", "1h"].includes(interval) ? 120000 : 600000;
    if (cached && (Date.now() - cached.ts < CACHE_TTL)) {
        if (fetchId !== _tfFetchId) return;
        _lastHistory = cached.history;
        _currentPatterns = cached.patterns || null;
        _hideChartEmpty();
        if (_candleMode) {
            renderCandlestickChart(cached.history);
        } else if (_spyOverlayActive) {
            _showChartLoading();
            try {
                const spy = await api.get(`/api/stock/SPY/history?period=${period}&interval=${interval}`);
                if (fetchId !== _tfFetchId) return;
                _lastSpyHistory = spy;
                _hideChartLoading();
                renderDetailChart(cached.history, spy);
            } catch { _hideChartLoading(); renderDetailChart(cached.history); }
        } else {
            renderDetailChart(cached.history);
        }
        return;
    }

    _showChartLoading();
    _hideChartEmpty();

    try {
        const url = _candleMode
            ? `/api/stock/${symbol}/history?period=${period}&interval=${interval}&include_patterns=true`
            : `/api/stock/${symbol}/history?period=${period}&interval=${interval}`;
        const history = await api.get(url);
        if (fetchId !== _tfFetchId) return;  // stale fetch — discard

        if (!history || !history.close || history.close.length === 0) {
            _hideChartLoading();
            _showChartEmpty("No data available for this timeframe");
            return;
        }

        _lastHistory = history;
        _currentPatterns = history.patterns || null;
        // Cache this result
        _historyCache.set(cacheKey, { history, patterns: _currentPatterns, ts: Date.now() });
        // Limit cache size to 30 entries
        if (_historyCache.size > 30) {
            const oldest = _historyCache.keys().next().value;
            _historyCache.delete(oldest);
        }

        _hideChartLoading();
        _hideChartEmpty();
        if (_candleMode) {
            renderCandlestickChart(history);
        } else if (_spyOverlayActive) {
            try {
                const spy = await api.get(`/api/stock/SPY/history?period=${period}&interval=${interval}`);
                if (fetchId !== _tfFetchId) return;
                _lastSpyHistory = spy;
                renderDetailChart(history, spy);
            } catch { renderDetailChart(history); }
        } else {
            renderDetailChart(history);
        }
    } catch (e) {
        if (fetchId !== _tfFetchId) return;
        _hideChartLoading();
        _showChartEmpty("Failed to load chart data");
    }
}

function renderDetailChart(history, spyHistory) {
    if (_candleMode) { renderCandlestickChart(history); return; }
    const canvas = document.getElementById("sd-price-chart");
    if (!canvas) return;
    if (detailChart) detailChart.destroy();

    const closes = history.close;
    const sessions = history.sessions || [];
    const hasSessions = sessions.length === closes.length;
    const isUp = closes[closes.length - 1] >= closes[0];
    const color = isUp ? "rgba(34, 197, 94, 1)" : "rgba(239, 68, 68, 1)";
    const bgColor = isUp ? "rgba(34, 197, 94, 0.08)" : "rgba(239, 68, 68, 0.08)";
    const extColor = isUp ? "rgba(34, 197, 94, 0.4)" : "rgba(239, 68, 68, 0.4)";

    // Segment styling: pre/post-market lines are dashed and more transparent
    const segmentBorder = hasSessions ? (ctx) => {
        const idx = ctx.p0DataIndex;
        return (sessions[idx] !== "regular" || sessions[idx + 1] !== "regular") ? extColor : color;
    } : undefined;
    const segmentDash = hasSessions ? (ctx) => {
        const idx = ctx.p0DataIndex;
        return (sessions[idx] !== "regular" || sessions[idx + 1] !== "regular") ? [4, 3] : undefined;
    } : undefined;

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
            segment: segmentBorder ? { borderColor: segmentBorder, borderDash: segmentDash } : undefined,
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
        y: { display: true, position: "left", ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => currSym(_currentCurrency) + v }, grid: { color: "rgba(42,45,62,0.3)" } },
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
        plugins: hasSessions ? [sessionZonePlugin] : [],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            _sessions: hasSessions ? sessions : null,
            plugins: {
                legend: { display: true, position: "top", labels: { color: "#8b8fa3", font: { size: 11 } } },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    backgroundColor: "rgba(20,22,34,0.95)",
                    titleColor: "#8b8fa3",
                    bodyColor: "#e4e4e7",
                    callbacks: hasSessions ? {
                        afterTitle(items) {
                            const idx = items[0] && items[0].dataIndex;
                            const s = sessions[idx];
                            if (s === "pre") return "PRE-MARKET";
                            if (s === "post") return "AFTER-HOURS";
                            return "";
                        },
                    } : {},
                },
            },
            scales,
            interaction: { mode: "index", intersect: false },
        },
    });
    renderSessionLegend(hasSessions);
}

function renderCandlestickChart(history) {
    const canvas = document.getElementById("sd-price-chart");
    if (!canvas) return;
    if (detailChart) detailChart.destroy();
    const ts = history.timestamps || history.dates.map(d => new Date(d).getTime());
    const sessions = history.sessions || [];
    const hasSessions = sessions.length === ts.length;

    // Detect intraday: median gap between candles < 1 hour → use index-based x to eliminate overnight/weekend gaps
    const _gaps = [];
    for (let gi = 1; gi < Math.min(ts.length, 10); gi++) _gaps.push(ts[gi] - ts[gi - 1]);
    _gaps.sort((a, b) => a - b);
    const isIntraday = _gaps.length > 0 && _gaps[Math.floor(_gaps.length / 2)] < 3600000;
    const multiDay = ts.length >= 2 && (ts[ts.length - 1] - ts[0]) > 86400000;

    const ohlc = ts.map((t, i) => ({ x: isIntraday ? i : t, o: history.open[i], h: history.high[i], l: history.low[i], c: history.close[i] }));
    const maxVol = Math.max(...history.volume);

    // Color candles differently for extended hours
    const volCol = history.close.map((c, i) => {
        const ext = hasSessions && sessions[i] !== "regular";
        if (c >= history.open[i]) return ext ? "rgba(34,197,94,0.15)" : "rgba(34,197,94,0.35)";
        return ext ? "rgba(239,68,68,0.15)" : "rgba(239,68,68,0.35)";
    });

    // Split candles into regular and extended datasets for different opacity
    let ohlcRegular, ohlcExtended;
    if (hasSessions) {
        ohlcRegular = ohlc.map((d, i) => sessions[i] === "regular" ? d : null);
        ohlcExtended = ohlc.map((d, i) => sessions[i] !== "regular" ? d : null);
    }

    const ds = hasSessions ? [
        { label: "OHLC", data: ohlcRegular, borderColor: { up: "#22c55e", down: "#ef4444", unchanged: "#999" }, yAxisID: "y" },
        { label: "Extended", data: ohlcExtended, borderColor: { up: "rgba(34,197,94,0.4)", down: "rgba(239,68,68,0.4)", unchanged: "rgba(153,153,153,0.4)" }, color: { up: "rgba(34,197,94,0.15)", down: "rgba(239,68,68,0.15)", unchanged: "rgba(153,153,153,0.15)" }, yAxisID: "y" },
        { type: "bar", label: "Volume", data: ts.map((t, i) => ({ x: isIntraday ? i : t, y: history.volume[i] })), backgroundColor: volCol, yAxisID: "yVol", barPercentage: 0.8, order: 1 },
    ] : [
        { label: "OHLC", data: ohlc, borderColor: { up: "#22c55e", down: "#ef4444", unchanged: "#999" }, yAxisID: "y" },
        { type: "bar", label: "Volume", data: ts.map((t, i) => ({ x: isIntraday ? i : t, y: history.volume[i] })), backgroundColor: volCol, yAxisID: "yVol", barPercentage: 0.8, order: 1 },
    ];

    if (_currentPatterns) {
        const mk = { bullish: [], bearish: [], neutral: [] };
        (_currentPatterns.candlestick_patterns || []).forEach(p => {
            if (p.idx < ts.length) mk[p.direction || "neutral"].push({ x: isIntraday ? p.idx : ts[p.idx], y: p.direction === "bearish" ? history.high[p.idx] * 1.01 : history.low[p.idx] * 0.99, _pat: p });
        });
        if (mk.bullish.length) ds.push({ type: "scatter", label: "\u25B2 Bullish", data: mk.bullish, pointStyle: "triangle", pointRadius: 8, backgroundColor: "#22c55e", borderColor: "#22c55e", yAxisID: "y", order: 0 });
        if (mk.bearish.length) ds.push({ type: "scatter", label: "\u25BC Bearish", data: mk.bearish, pointStyle: "triangle", rotation: 180, pointRadius: 8, backgroundColor: "#ef4444", borderColor: "#ef4444", yAxisID: "y", order: 0 });
        if (mk.neutral.length) ds.push({ type: "scatter", label: "\u25C6 Neutral", data: mk.neutral, pointStyle: "rectRot", pointRadius: 7, backgroundColor: "#eab308", borderColor: "#eab308", yAxisID: "y", order: 0 });
    }
    detailChart = new Chart(canvas, {
        type: "candlestick",
        data: { datasets: ds },
        plugins: hasSessions ? [isIntraday ? sessionZonePlugin : sessionZoneTimePlugin] : [],
        options: {
            responsive: true, maintainAspectRatio: false,
            _sessions: hasSessions ? sessions : null,
            _timestamps: hasSessions ? ts : null,
            plugins: {
                legend: { display: false },
                tooltip: { mode: "nearest", intersect: true, backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7",
                    callbacks: {
                        title(items) {
                            if (!isIntraday) return undefined;
                            const d = items[0]?.raw;
                            if (!d || d.x == null) return '';
                            const idx = Math.round(d.x);
                            if (idx >= 0 && idx < ts.length) {
                                const dt = new Date(ts[idx]);
                                if (multiDay) return dt.toLocaleDateString([], {month:'short',day:'numeric'}) + ' ' + dt.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                                return dt.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                            }
                            return '';
                        },
                        afterTitle(items) {
                            if (!hasSessions) return "";
                            const d = items[0] && items[0].raw;
                            if (!d || d.x == null) return "";
                            const idx = isIntraday ? Math.round(d.x) : ts.indexOf(d.x);
                            if (idx >= 0 && sessions[idx] === "pre") return "PRE-MARKET";
                            if (idx >= 0 && sessions[idx] === "post") return "AFTER-HOURS";
                            return "";
                        },
                        label(ctx) {
                            const d = ctx.raw;
                            const sym = currSym(_currentCurrency);
                            if (d && d.o != null) return [`O: ${sym}${d.o.toFixed(2)}  H: ${sym}${d.h.toFixed(2)}`, `L: ${sym}${d.l.toFixed(2)}  C: ${sym}${d.c.toFixed(2)}`];
                            if (d && d._pat) return [d._pat.pattern, d._pat.detail];
                            if (ctx.dataset.label === "Volume") return `Vol: ${(d.y || 0).toLocaleString()}`;
                            return ctx.formattedValue;
                        },
                    },
                },
            },
            scales: {
                x: isIntraday
                    ? { type: "linear", min: -0.5, max: ts.length - 0.5,
                        ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 8,
                            callback(val) {
                                const i = Math.round(val); if (i < 0 || i >= ts.length) return '';
                                const d = new Date(ts[i]);
                                if (multiDay) return d.toLocaleDateString([], {month:'short',day:'numeric'}) + ' ' + d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                                return d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                            }
                        }, grid: { color: "rgba(42,45,62,0.3)" } }
                    : { type: "time", ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 8 }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { position: "right", ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => currSym(_currentCurrency) + v }, grid: { color: "rgba(42,45,62,0.3)" } },
                yVol: { position: "left", max: maxVol * 4, display: false, grid: { display: false } },
            },
        },
    });
    renderPatternLegend();
    renderSessionLegend(hasSessions);
}

function renderPatternLegend() {
    const el = document.getElementById("sd-patterns-legend");
    if (!el) return;
    const p = _currentPatterns;
    if (!p || (!(p.candlestick_patterns || []).length && !(p.chart_patterns || []).length)) { el.style.display = "none"; return; }
    el.style.display = "";
    const sc = p.pattern_score >= 0 ? "pat-bull" : "pat-bear";
    let h = `<div class="pl-header"><span>Detected Patterns</span><span class="${sc}">Score: ${p.pattern_score > 0 ? "+" : ""}${p.pattern_score}</span></div><div class="pl-items">`;
    (p.candlestick_patterns || []).forEach(c => {
        const cls = c.direction === "bullish" ? "pat-bull" : c.direction === "bearish" ? "pat-bear" : "pat-neutral";
        h += `<div class="pl-item ${cls}"><strong>${c.pattern}</strong> <span class="pl-rel">${c.reliability}%</span><br><small>${c.detail}</small></div>`;
    });
    (p.chart_patterns || []).forEach(c => {
        const cls = c.direction === "bullish" ? "pat-bull" : "pat-bear";
        h += `<div class="pl-item ${cls}"><strong>${c.name}</strong><br><small>${c.detail || ""}</small></div>`;
    });
    el.innerHTML = h + "</div>";
}

function renderSessionLegend(hasSessions) {
    let el = document.getElementById("sd-session-legend");
    if (!el) {
        const wrap = document.querySelector(".sd-chart-section");
        if (!wrap) return;
        el = document.createElement("div");
        el.id = "sd-session-legend";
        el.className = "sd-session-legend";
        wrap.appendChild(el);
    }
    if (!hasSessions) { el.style.display = "none"; return; }
    el.style.display = "";
    el.innerHTML = `<span class="sl-item"><span class="sl-swatch sl-pre"></span>Pre-Market (4:00–9:30 ET)</span>`
        + `<span class="sl-item"><span class="sl-swatch sl-regular"></span>Regular Hours (9:30–16:00 ET)</span>`
        + `<span class="sl-item"><span class="sl-swatch sl-post"></span>After-Hours (16:00–20:00 ET)</span>`;
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
    const sym = symbol.toUpperCase();
    if (isInWatchlist(sym)) {
        showToast(`${sym} is already in your watchlist`, "info");
        return;
    }
    try {
        await api.post(`/api/screener/watchlist?symbol=${sym}&name=${encodeURIComponent(name)}`, {});
        _wlSymbolSet.add(sym);
        showToast(`${sym} added to watchlist`);
        _refreshWlButtons();
    } catch (e) {
        showToast(`${sym} is already in your watchlist`, "info");
    }
}

function formatMarketCapLocal(cap, currency) {
    if (!cap) return "N/A";
    const s = currSym(currency);
    if (cap >= 1e12) return `${s}${(cap / 1e12).toFixed(1)}T`;
    if (cap >= 1e9) return `${s}${(cap / 1e9).toFixed(1)}B`;
    if (cap >= 1e6) return `${s}${(cap / 1e6).toFixed(0)}M`;
    return `${s}${cap.toLocaleString()}`;
}

function showToast(msg, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("visible"));
    setTimeout(() => { toast.classList.remove("visible"); setTimeout(() => toast.remove(), 300); }, 2500);
}
