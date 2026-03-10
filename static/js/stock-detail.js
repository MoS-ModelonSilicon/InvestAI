let detailChart = null;
let _currentDetailSymbol = null;
let _spyOverlayActive = false;
let _lastHistory = null;
let _lastSpyHistory = null;
let _candleMode = false;
let _currentPatterns = null;
let _currentCurrency = "USD";
let _zoomLevel = parseFloat(localStorage.getItem("sd-zoom") || "1");

/* ── Semantic Zoom State ───────────────────────────────────── */
let _zoomStack = [];            // stack of { min, max, label } for breadcrumb trail
let _dragZoomStart = null;      // pixel X where drag began
let _dragZoomActive = false;
let _dragOverlay = null;        // the blue highlight overlay element
let _currentTimeframe = null;   // { label, period, interval } of currently active TF

/* Resolution ladder — when zoomed in deeply, re-fetch at finer granularity */
const RESOLUTION_LADDER = [
    { maxRangeMs: 2 * 3600_000,  interval: "1m",  period: "1d"  },  // ≤2h  → 1min bars
    { maxRangeMs: 8 * 3600_000,  interval: "2m",  period: "1d"  },  // ≤8h  → 2min bars
    { maxRangeMs: 24 * 3600_000, interval: "5m",  period: "1d"  },  // ≤1d  → 5min bars
    { maxRangeMs: 5 * 86400_000, interval: "15m", period: "5d"  },  // ≤5d  → 15min bars
    { maxRangeMs: 30 * 86400_000, interval: "1h", period: "1mo" },  // ≤30d → 1h bars
];

function _getVisibleTimestamps() {
    if (!detailChart || !_lastHistory) return [];
    return _lastHistory.timestamps || (_lastHistory.dates || []).map(d => new Date(d).getTime());
}

/** Convert a canvas pixel X to the nearest data index */
function _pixelToIndex(chart, pixelX) {
    const xScale = chart.scales.x;
    if (!xScale) return -1;
    const val = xScale.getValueForPixel(pixelX);
    if (xScale.type === "linear") return Math.round(val);
    if (xScale.type === "time" || xScale.type === "timeseries") {
        // Find closest timestamp
        const ts = _getVisibleTimestamps();
        let best = 0, bestDiff = Infinity;
        for (let i = 0; i < ts.length; i++) {
            const diff = Math.abs(ts[i] - val);
            if (diff < bestDiff) { bestDiff = diff; best = i; }
        }
        return best;
    }
    return Math.round(val);
}

/** Build a human-readable label for a zoom range */
function _rangeLabel(idxStart, idxEnd) {
    const ts = _getVisibleTimestamps();
    if (!ts.length) return "";
    const s = Math.max(0, Math.min(idxStart, ts.length - 1));
    const e = Math.max(0, Math.min(idxEnd, ts.length - 1));
    const d0 = new Date(ts[s]), d1 = new Date(ts[e]);
    const sameDay = d0.toDateString() === d1.toDateString();
    if (sameDay) {
        return d0.toLocaleDateString([], { month: "short", day: "numeric" }) + " " +
            d0.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + "–" +
            d1.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    return d0.toLocaleDateString([], { month: "short", day: "numeric" }) + " – " +
        d1.toLocaleDateString([], { month: "short", day: "numeric" });
}

/** Apply a zoom to a specific index range, push to stack, optionally re-fetch finer data */
async function _semanticZoomTo(idxStart, idxEnd, pushStack = true) {
    if (!detailChart || !_lastHistory) return;
    const ts = _getVisibleTimestamps();
    if (ts.length < 2) return;
    const s = Math.max(0, Math.min(idxStart, idxEnd));
    const e = Math.min(ts.length - 1, Math.max(idxStart, idxEnd));
    if (e - s < 2) return; // too small to zoom

    const label = _rangeLabel(s, e);
    if (pushStack) {
        _zoomStack.push({ min: s, max: e, label });
    }

    // Check if we should re-fetch at higher resolution
    const rangeMs = ts[e] - ts[s];
    const sym = _currentDetailSymbol;
    let refetched = false;

    if (sym && rangeMs > 0) {
        for (const rung of RESOLUTION_LADDER) {
            if (rangeMs <= rung.maxRangeMs) {
                // Only re-fetch if the rung interval is finer than current
                const curInterval = _currentTimeframe ? _currentTimeframe.interval : "1d";
                if (_intervalRank(rung.interval) < _intervalRank(curInterval)) {
                    try {
                        // Fetch a time window around the selection (with some padding)
                        const fromSec = Math.floor(ts[s] / 1000) - 3600;
                        const toSec = Math.ceil(ts[e] / 1000) + 3600;
                        const url = `/api/stock/${sym}/history?period=${rung.period}&interval=${rung.interval}`;
                        _showChartLoading();
                        const newHistory = await api.get(url);
                        if (newHistory && newHistory.close && newHistory.close.length > 0) {
                            // Filter to just the selected time window
                            const newTs = newHistory.timestamps || newHistory.dates.map(d => new Date(d).getTime());
                            const fromMs = ts[s], toMs = ts[e];
                            let si = 0, ei = newTs.length - 1;
                            for (let i = 0; i < newTs.length; i++) { if (newTs[i] >= fromMs) { si = Math.max(0, i - 1); break; } }
                            for (let i = newTs.length - 1; i >= 0; i--) { if (newTs[i] <= toMs) { ei = Math.min(newTs.length - 1, i + 1); break; } }

                            // Slice the history to just the visible range
                            const sliced = _sliceHistory(newHistory, si, ei + 1);
                            if (sliced.close.length >= 3) {
                                _lastHistory = sliced;
                                if (_candleMode) {
                                    renderCandlestickChart(sliced);
                                } else {
                                    renderDetailChart(sliced, _spyOverlayActive ? _lastSpyHistory : undefined);
                                }
                                refetched = true;
                            }
                        }
                        _hideChartLoading();
                    } catch { _hideChartLoading(); }
                }
                break;
            }
        }
    }

    if (!refetched) {
        // Just zoom the existing chart's x-axis
        const xScale = detailChart.options.scales.x;
        if (xScale.type === "linear") {
            xScale.min = s - 0.5;
            xScale.max = e + 0.5;
        } else {
            // category or time
            const labels = detailChart.data.labels;
            if (labels && labels.length) {
                xScale.min = s;
                xScale.max = e;
            }
        }
        detailChart.update("none");
    }

    _updateZoomBreadcrumb();
}

function _intervalRank(interval) {
    const ranks = { "1m": 1, "2m": 2, "5m": 3, "15m": 4, "30m": 5, "1h": 6, "1d": 7, "1wk": 8, "1mo": 9 };
    return ranks[interval] || 10;
}

function _sliceHistory(h, start, end) {
    const result = {
        dates: (h.dates || []).slice(start, end),
        timestamps: (h.timestamps || []).slice(start, end),
        open: (h.open || []).slice(start, end),
        high: (h.high || []).slice(start, end),
        low: (h.low || []).slice(start, end),
        close: (h.close || []).slice(start, end),
        volume: (h.volume || []).slice(start, end),
    };
    if (h.sessions) result.sessions = h.sessions.slice(start, end);
    if (h.sma50) result.sma50 = h.sma50.slice(start, end);
    return result;
}

function _zoomOut() {
    if (_zoomStack.length === 0) return;
    _zoomStack.pop();
    if (_zoomStack.length === 0) {
        _restoreFullView();
    } else {
        // Re-apply the last remaining zoom level
        const last = _zoomStack[_zoomStack.length - 1];
        _zoomStack.pop(); // will be re-pushed by _semanticZoomTo
        _restoreFullViewThen(() => _semanticZoomTo(last.min, last.max, true));
    }
}

function _zoomReset() {
    _zoomStack = [];
    _restoreFullView();
}

async function _restoreFullViewThen(callback) {
    // Re-fetch original timeframe data, then run callback
    if (_currentDetailSymbol && _currentTimeframe) {
        const { period, interval } = _currentTimeframe;
        const btn = document.querySelector("#sd-timeframes .sd-tf.active");
        // Save/restore stack since changeTimeframe resets it
        const savedStack = [..._zoomStack];
        await changeTimeframe(_currentDetailSymbol, period, interval, btn);
        _zoomStack = savedStack;
        if (callback) await callback();
        _updateZoomBreadcrumb();
    }
}

async function _restoreFullView() {
    // Re-fetch original timeframe data
    if (_currentDetailSymbol && _currentTimeframe) {
        const { period, interval } = _currentTimeframe;
        const btn = document.querySelector("#sd-timeframes .sd-tf.active");
        await changeTimeframe(_currentDetailSymbol, period, interval, btn);
    }
    _updateZoomBreadcrumb();
}

function _updateZoomBreadcrumb() {
    let el = document.getElementById("sd-zoom-breadcrumb");
    if (!el) {
        const wrap = document.querySelector(".sd-chart-controls");
        if (!wrap) return;
        el = document.createElement("div");
        el.id = "sd-zoom-breadcrumb";
        el.className = "sd-zoom-breadcrumb";
        // Insert after the controls row
        wrap.parentNode.insertBefore(el, wrap.nextSibling);
    }

    if (_zoomStack.length === 0) {
        el.style.display = "none";
        return;
    }

    el.style.display = "flex";
    const tfLabel = _currentTimeframe ? _currentTimeframe.label : "";
    let crumbs = `<span class="zb-crumb zb-clickable" onclick="_zoomReset()">${tfLabel || 'Full'}</span>`;
    _zoomStack.forEach((z, i) => {
        crumbs += `<span class="zb-sep">›</span>`;
        if (i === _zoomStack.length - 1) {
            crumbs += `<span class="zb-crumb zb-active">${z.label}</span>`;
        } else {
            crumbs += `<span class="zb-crumb zb-clickable" onclick="_zoomToStackLevel(${i})">${z.label}</span>`;
        }
    });
    crumbs += `<button class="zb-back" onclick="_zoomOut()" title="Zoom out one level">↩ Back</button>`;
    crumbs += `<button class="zb-reset" onclick="_zoomReset()" title="Reset to full view">⟳ Reset</button>`;
    el.innerHTML = crumbs;
}

function _zoomToStackLevel(level) {
    _zoomStack = _zoomStack.slice(0, level + 1);
    _restoreFullView();
}

/* ── Drag-to-zoom overlay plugin for Chart.js ────────────── */
const dragZoomPlugin = {
    id: "dragZoom",
    afterInit(chart) {
        const canvas = chart.canvas;
        if (!canvas || canvas._dragZoomBound) return;
        canvas._dragZoomBound = true;

        canvas.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return; // left click only
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const area = chart.chartArea;
            if (!area || x < area.left || x > area.right) return;
            _dragZoomStart = x;
            _dragZoomActive = false;

            // Create overlay
            _dragOverlay = document.createElement("div");
            _dragOverlay.className = "sd-drag-overlay";
            _dragOverlay.style.left = x + "px";
            _dragOverlay.style.top = area.top + "px";
            _dragOverlay.style.height = (area.bottom - area.top) + "px";
            _dragOverlay.style.width = "0px";
            canvas.parentElement.appendChild(_dragOverlay);
        });

        canvas.addEventListener("mousemove", (e) => {
            if (_dragZoomStart == null || !_dragOverlay) return;
            const rect = canvas.getBoundingClientRect();
            const x = Math.max(chart.chartArea.left, Math.min(e.clientX - rect.left, chart.chartArea.right));
            const left = Math.min(_dragZoomStart, x);
            const width = Math.abs(x - _dragZoomStart);
            if (width > 5) _dragZoomActive = true;
            _dragOverlay.style.left = left + "px";
            _dragOverlay.style.width = width + "px";
        });

        canvas.addEventListener("mouseup", (e) => {
            if (_dragOverlay) { _dragOverlay.remove(); _dragOverlay = null; }
            if (!_dragZoomActive || _dragZoomStart == null) {
                _dragZoomStart = null;
                _dragZoomActive = false;
                return;
            }
            const rect = canvas.getBoundingClientRect();
            const endX = Math.max(chart.chartArea.left, Math.min(e.clientX - rect.left, chart.chartArea.right));
            const startIdx = _pixelToIndex(chart, Math.min(_dragZoomStart, endX));
            const endIdx = _pixelToIndex(chart, Math.max(_dragZoomStart, endX));
            _dragZoomStart = null;
            _dragZoomActive = false;
            if (endIdx - startIdx >= 2) {
                _semanticZoomTo(startIdx, endIdx);
            }
        });

        canvas.addEventListener("mouseleave", () => {
            if (_dragOverlay) { _dragOverlay.remove(); _dragOverlay = null; }
            _dragZoomStart = null;
            _dragZoomActive = false;
        });

        // Double-click to zoom in 50% centered on click point
        canvas.addEventListener("dblclick", (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const area = chart.chartArea;
            if (!area || x < area.left || x > area.right) return;
            const centerIdx = _pixelToIndex(chart, x);
            const ts = _getVisibleTimestamps();
            if (ts.length < 4) return;

            // Determine current visible range
            const xScale = chart.options.scales.x;
            let curMin = 0, curMax = ts.length - 1;
            if (xScale.min != null) curMin = Math.max(0, Math.round(xScale.min));
            if (xScale.max != null) curMax = Math.min(ts.length - 1, Math.round(xScale.max));
            const curRange = curMax - curMin;
            const newRange = Math.max(4, Math.round(curRange * 0.5));
            const newMin = Math.max(0, centerIdx - Math.round(newRange / 2));
            const newMax = Math.min(ts.length - 1, newMin + newRange);
            _semanticZoomTo(newMin, newMax);
        });

        // Right-click context: zoom out
        canvas.addEventListener("contextmenu", (e) => {
            if (_zoomStack.length > 0) {
                e.preventDefault();
                _zoomOut();
            }
        });
    },
};

// Keyboard: Escape to zoom out
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && _zoomStack.length > 0) {
        _zoomOut();
    }
});

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

/* ── Session boundary lines plugin (day separators + session transitions) ── */
const sessionBoundaryPlugin = {
    id: "sessionBoundaries",
    afterDatasetsDraw(chart) {
        const timestamps = chart.options._timestamps;
        const sessions = chart.options._sessions;
        if (!timestamps || timestamps.length < 2) return;
        const ctx = chart.ctx;
        const xAxis = chart.scales.x;
        const { top, bottom } = chart.chartArea;
        if (!xAxis || top == null) return;

        ctx.save();
        // Day boundaries — dashed lines where the calendar date changes
        let prevDay = new Date(timestamps[0]).toDateString();
        for (let i = 1; i < timestamps.length; i++) {
            const curDay = new Date(timestamps[i]).toDateString();
            if (curDay !== prevDay) {
                ctx.strokeStyle = "rgba(128,140,160,0.4)";
                ctx.lineWidth = 1;
                ctx.setLineDash([5, 4]);
                const x = xAxis.getPixelForValue(i - 0.5);
                ctx.beginPath();
                ctx.moveTo(x, top);
                ctx.lineTo(x, bottom);
                ctx.stroke();
                prevDay = curDay;
            }
        }
        // Session transitions within the same day (pre↔regular↔post)
        if (sessions && sessions.length === timestamps.length) {
            for (let i = 1; i < sessions.length; i++) {
                if (sessions[i] !== sessions[i - 1]) {
                    const pDay = new Date(timestamps[i - 1]).toDateString();
                    const cDay = new Date(timestamps[i]).toDateString();
                    if (pDay !== cDay) continue; // day boundary already drawn
                    ctx.strokeStyle = sessions[i] === "regular" ? "rgba(34,197,94,0.25)" : "rgba(168,85,247,0.25)";
                    ctx.lineWidth = 1;
                    ctx.setLineDash([3, 3]);
                    const x = xAxis.getPixelForValue(i - 0.5);
                    ctx.beginPath();
                    ctx.moveTo(x, top);
                    ctx.lineTo(x, bottom);
                    ctx.stroke();
                }
            }
        }
        ctx.restore();
    },
};

const LINE_TF = [
    { label: "1D", period: "1d", interval: "5m" },
    { label: "1W", period: "5d", interval: "15m" },
    { label: "1M", period: "1mo", interval: "1d" },
    { label: "3M", period: "3mo", interval: "1d" },
    { label: "6M", period: "6mo", interval: "1d" },
    { label: "1Y", period: "1y", interval: "1d" },
    { label: "5Y", period: "5y", interval: "1wk" },
];
const CANDLE_TF = [
    { label: "1m", period: "1d", interval: "1m" },
    { label: "2m", period: "5d", interval: "2m" },
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
        renderStockDetail(resp.info, resp.history, resp.news, resp.sentiment);
    } catch (e) {
        container.innerHTML = `<p style="color:var(--red);padding:20px;">Failed to load data for ${sym}.</p>`;
    }
}

function renderStockDetail(info, history, news, sentiment) {
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
            <div class="sd-zoom-controls">
                <button class="sd-zoom-btn" onclick="chartZoom(1)" title="Zoom in">+</button>
                <button class="sd-zoom-btn" onclick="chartZoom(-1)" title="Zoom out">&minus;</button>
                <button class="sd-zoom-btn sd-zoom-reset" onclick="chartZoom(0)" title="Reset zoom">⟳</button>
            </div>
        </div>
        <div class="sd-zoom-hint" id="sd-zoom-hint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
            Drag to select a range · Double-click to zoom in · Right-click to zoom out
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

    // ── News Sentiment Gauge ──────────────────────────────────
    if (sentiment && sentiment.article_count > 0) {
        const sc = sentiment.overall_score;
        const pct = Math.round((sc + 1) / 2 * 100);  // map -1..1 → 0..100
        const sentColor = sc >= 0.10 ? "var(--green)" : sc <= -0.10 ? "var(--red)" : "#eab308";
        const bullPct = sentiment.bullish_count ? Math.round(sentiment.bullish_count / sentiment.article_count * 100) : 0;
        const bearPct = sentiment.bearish_count ? Math.round(sentiment.bearish_count / sentiment.article_count * 100) : 0;
        const neutPct = 100 - bullPct - bearPct;

        html += `<div class="sd-section"><h3>News Sentiment</h3>
            <div class="sentiment-gauge-wrap">
                <div class="sentiment-gauge-bar">
                    <div class="sentiment-gauge-fill" style="width:${pct}%;background:${sentColor}"></div>
                    <div class="sentiment-gauge-needle" style="left:${pct}%"></div>
                </div>
                <div class="sentiment-gauge-labels">
                    <span>Bearish</span><span>Neutral</span><span>Bullish</span>
                </div>
                <div class="sentiment-score-row">
                    <span class="sentiment-overall" style="color:${sentColor}">${sentiment.overall_label}</span>
                    <span class="sentiment-score-num">${sc >= 0 ? "+" : ""}${sc.toFixed(2)}</span>
                </div>
                <div class="sentiment-breakdown">
                    <div class="sentiment-bar-stacked">
                        <div class="sent-bull" style="width:${bullPct}%"></div>
                        <div class="sent-neut" style="width:${neutPct}%"></div>
                        <div class="sent-bear" style="width:${bearPct}%"></div>
                    </div>
                    <div class="sentiment-breakdown-labels">
                        <span class="sent-label-bull">${bullPct}% Bullish</span>
                        <span class="sent-label-neut">${neutPct}% Neutral</span>
                        <span class="sent-label-bear">${bearPct}% Bearish</span>
                    </div>
                </div>
                <div class="sentiment-articles-count">${sentiment.article_count} articles analysed</div>
            </div>`;

        // Individual article sentiments
        if (sentiment.articles && sentiment.articles.length > 0) {
            html += `<div class="sentiment-articles">`;
            sentiment.articles.forEach(a => {
                const aColor = a.sentiment_label === "Bullish" ? "var(--green)" : a.sentiment_label === "Bearish" ? "var(--red)" : "#eab308";
                const icon = a.sentiment_label === "Bullish" ? "▲" : a.sentiment_label === "Bearish" ? "▼" : "●";
                const date = a.published ? new Date(a.published * 1000).toLocaleDateString() : "";
                html += `<div class="sentiment-article-row">
                    <span class="sent-icon" style="color:${aColor}">${icon}</span>
                    <span class="sent-article-title">${a.title}</span>
                    <span class="sent-article-meta">${a.publisher}${date ? " · " + date : ""}</span>
                    <span class="sent-article-badge" style="background:${aColor}">${a.sentiment_label}</span>
                </div>`;
            });
            html += `</div>`;
        }
        html += `</div>`;
    }

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
    _zoomStack = [];
    _currentTimeframe = LINE_TF[2]; // default 1M
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
    const defIdx = _candleMode ? 4 : 2;
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
    _zoomStack = [];
    _updateZoomBreadcrumb();
    buildTimeframeButtons(symbol);
    const tfs = _candleMode ? CANDLE_TF : LINE_TF;
    const def = tfs[_candleMode ? 4 : 2];
    changeTimeframe(symbol, def.period, def.interval, document.querySelector("#sd-timeframes .sd-tf.active"));
}

/* ── Chart Zoom ─────────────────────────────────────────────── */
function chartZoom(dir) {
    // dir: 1 = zoom in (more detail), -1 = zoom out (wider view), 0 = reset
    if (dir === 0) { _zoomLevel = 1; }
    else {
        const step = _zoomLevel >= 5 ? 0.8 : _zoomLevel >= 2 ? 0.5 : 0.3;
        _zoomLevel = Math.max(0.1, Math.min(20, _zoomLevel + dir * step));
    }
    localStorage.setItem("sd-zoom", String(_zoomLevel));
    _applyZoom();
}

function _applyZoom() {
    if (!detailChart) return;
    const xScale = detailChart.options.scales.x;
    if (!xScale) return;

    if (_zoomLevel === 1) {
        // Reset: remove zoom constraints
        delete xScale.min;
        delete xScale.max;
        // For linear (intraday candle) axes, restore full range
        if (xScale.type === "linear" && detailChart._sdFullMax != null) {
            xScale.min = -0.5;
            xScale.max = detailChart._sdFullMax;
        }
    } else {
        // Zoom works by showing a subset of data from the right (most recent)
        if (xScale.type === "linear") {
            const fullLen = (detailChart._sdFullMax || 0) + 0.5;
            const visible = Math.max(5, Math.round(fullLen / _zoomLevel));
            xScale.max = detailChart._sdFullMax;
            xScale.min = xScale.max - visible + 0.5;
        } else if (xScale.type === "time" || xScale.type === "timeseries") {
            const labels = detailChart.data.labels;
            const dsets = detailChart.data.datasets;
            let allX = [];
            if (labels && labels.length) {
                allX = labels.map(l => new Date(l).getTime());
            } else {
                dsets.forEach(ds => { (ds.data || []).forEach(d => { if (d && d.x != null) allX.push(typeof d.x === "number" ? d.x : new Date(d.x).getTime()); }); });
                allX.sort((a, b) => a - b);
            }
            if (allX.length > 1) {
                const fullRange = allX[allX.length - 1] - allX[0];
                const visible = fullRange / _zoomLevel;
                xScale.min = allX[allX.length - 1] - visible;
                xScale.max = allX[allX.length - 1];
            }
        } else {
            // Category axis (line chart with date labels)
            const labels = detailChart.data.labels;
            if (labels && labels.length > 1) {
                const visible = Math.max(5, Math.round(labels.length / _zoomLevel));
                xScale.min = labels.length - visible;
                xScale.max = labels.length - 1;
            }
        }
    }
    detailChart.update("none");
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
        plugins: [dragZoomPlugin, ...(hasSessions ? [sessionZonePlugin] : []), ...(hasSessions ? [sessionBoundaryPlugin] : [])],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            _sessions: hasSessions ? sessions : null,
            _timestamps: history.timestamps || null,
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
    if (_zoomLevel !== 1) _applyZoom();
    renderSessionLegend(hasSessions);
}

let _tfFetchId = 0;

function _showChartLoading() {
    let el = document.getElementById("sd-chart-loading");
    if (!el) {
        const wrap = document.querySelector(".sd-chart-wrapper");
        if (!wrap) return;
        el = document.createElement("div");
        el.id = "sd-chart-loading";
        el.className = "sd-chart-loading";
        el.innerHTML = '<div class="spinner"></div>';
        wrap.appendChild(el);
    }
    el.style.display = "flex";
}
function _hideChartLoading() {
    const el = document.getElementById("sd-chart-loading");
    if (el) el.style.display = "none";
}
function _showChartEmpty(msg) {
    let el = document.getElementById("sd-chart-empty");
    if (!el) {
        const wrap = document.querySelector(".sd-chart-wrapper");
        if (!wrap) return;
        el = document.createElement("div");
        el.id = "sd-chart-empty";
        el.className = "sd-chart-empty";
        wrap.appendChild(el);
    }
    el.textContent = msg;
    el.style.display = "flex";
}
function _hideChartEmpty() {
    const el = document.getElementById("sd-chart-empty");
    if (el) el.style.display = "none";
}

async function changeTimeframe(symbol, period, interval, btn) {
    document.querySelectorAll("#sd-timeframes .sd-tf").forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    _lastSpyHistory = null;

    // Track current timeframe and reset zoom stack on explicit TF change
    const tfs = _candleMode ? CANDLE_TF : LINE_TF;
    const matched = tfs.find(t => t.period === period && t.interval === interval);
    _currentTimeframe = matched || { label: interval, period, interval };
    _zoomStack = [];
    _updateZoomBreadcrumb();

    const fetchId = ++_tfFetchId;
    _hideChartEmpty();
    _showChartLoading();

    try {
        const url = _candleMode
            ? `/api/stock/${symbol}/history?period=${period}&interval=${interval}&include_patterns=true`
            : `/api/stock/${symbol}/history?period=${period}&interval=${interval}`;
        const history = await api.get(url);

        if (fetchId !== _tfFetchId) return; // stale request — discard

        if (!history || !history.close || history.close.length === 0) {
            _hideChartLoading();
            _showChartEmpty("No data available for this timeframe");
            return;
        }

        _lastHistory = history;
        if (_candleMode) {
            _currentPatterns = history.patterns || null;
            renderCandlestickChart(history);
        } else if (_spyOverlayActive) {
            try {
                const spy = await api.get(`/api/stock/SPY/history?period=${period}&interval=${interval}`);
                if (fetchId !== _tfFetchId) return;
                _lastSpyHistory = spy;
                renderDetailChart(history, spy);
            } catch {
                renderDetailChart(history);
            }
        } else {
            renderDetailChart(history);
        }
        _hideChartLoading();
    } catch (e) {
        if (fetchId !== _tfFetchId) return;
        _hideChartLoading();
        _showChartEmpty("Failed to load chart data");
    }
}

function renderCandlestickChart(history) {
    const canvas = document.getElementById("sd-price-chart");
    if (!canvas) return;
    if (detailChart) detailChart.destroy();
    const ts = history.timestamps || history.dates.map(d => new Date(d).getTime());
    const sessions = history.sessions || [];
    const hasSessions = sessions.length === ts.length;

    // Detect data characteristics for tick label formatting
    const _gaps = [];
    for (let gi = 1; gi < Math.min(ts.length, 20); gi++) _gaps.push(ts[gi] - ts[gi - 1]);
    _gaps.sort((a, b) => a - b);
    const medianGapMs = _gaps.length > 0 ? _gaps[Math.floor(_gaps.length / 2)] : 86400000;
    const isSubDaily = medianGapMs < 86400000;
    const spanMs = ts.length >= 2 ? ts[ts.length - 1] - ts[0] : 0;
    const multiDay = spanMs > 86400000;

    // Always use index-based x to eliminate ALL gaps (overnight, weekend, holiday)
    const ohlc = ts.map((t, i) => ({ x: i, o: history.open[i], h: history.high[i], l: history.low[i], c: history.close[i] }));
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
        ohlcRegular = ohlc.filter((_, i) => sessions[i] === "regular");
        ohlcExtended = ohlc.filter((_, i) => sessions[i] !== "regular");
    }

    const ds = hasSessions ? [
        { label: "OHLC", data: ohlcRegular, borderColor: { up: "#22c55e", down: "#ef4444", unchanged: "#999" }, yAxisID: "y" },
        { label: "Extended", data: ohlcExtended, borderColor: { up: "rgba(34,197,94,0.4)", down: "rgba(239,68,68,0.4)", unchanged: "rgba(153,153,153,0.4)" }, color: { up: "rgba(34,197,94,0.15)", down: "rgba(239,68,68,0.15)", unchanged: "rgba(153,153,153,0.15)" }, yAxisID: "y" },
        { type: "bar", label: "Volume", data: ts.map((t, i) => ({ x: i, y: history.volume[i] })), backgroundColor: volCol, yAxisID: "yVol", barPercentage: 0.8, order: 1 },
    ] : [
        { label: "OHLC", data: ohlc, borderColor: { up: "#22c55e", down: "#ef4444", unchanged: "#999" }, yAxisID: "y" },
        { type: "bar", label: "Volume", data: ts.map((t, i) => ({ x: i, y: history.volume[i] })), backgroundColor: volCol, yAxisID: "yVol", barPercentage: 0.8, order: 1 },
    ];

    if (_currentPatterns) {
        const mk = { bullish: [], bearish: [], neutral: [] };
        (_currentPatterns.candlestick_patterns || []).forEach(p => {
            if (p.idx < ts.length) mk[p.direction || "neutral"].push({ x: p.idx, y: p.direction === "bearish" ? history.high[p.idx] * 1.01 : history.low[p.idx] * 0.99, _pat: p });
        });
        if (mk.bullish.length) ds.push({ type: "scatter", label: "\u25B2 Bullish", data: mk.bullish, pointStyle: "triangle", pointRadius: 8, backgroundColor: "#22c55e", borderColor: "#22c55e", yAxisID: "y", order: 0 });
        if (mk.bearish.length) ds.push({ type: "scatter", label: "\u25BC Bearish", data: mk.bearish, pointStyle: "triangle", rotation: 180, pointRadius: 8, backgroundColor: "#ef4444", borderColor: "#ef4444", yAxisID: "y", order: 0 });
        if (mk.neutral.length) ds.push({ type: "scatter", label: "\u25C6 Neutral", data: mk.neutral, pointStyle: "rectRot", pointRadius: 7, backgroundColor: "#eab308", borderColor: "#eab308", yAxisID: "y", order: 0 });
    }

    // Build plugins: session shading + boundary lines
    const chartPlugins = [dragZoomPlugin];
    if (hasSessions) chartPlugins.push(sessionZonePlugin);
    if (isSubDaily) chartPlugins.push(sessionBoundaryPlugin);

    detailChart = new Chart(canvas, {
        type: "candlestick",
        data: { datasets: ds },
        plugins: chartPlugins,
        options: {
            responsive: true, maintainAspectRatio: false,
            _sessions: hasSessions ? sessions : null,
            _timestamps: ts,
            plugins: {
                legend: { display: false },
                tooltip: { mode: "nearest", intersect: true, backgroundColor: "rgba(20,22,34,0.95)", titleColor: "#8b8fa3", bodyColor: "#e4e4e7",
                    callbacks: {
                        title(items) {
                            const d = items[0]?.raw;
                            if (!d || d.x == null) return '';
                            const idx = Math.round(d.x);
                            if (idx >= 0 && idx < ts.length) {
                                const dt = new Date(ts[idx]);
                                if (isSubDaily && multiDay) return dt.toLocaleDateString([], {month:'short',day:'numeric'}) + ' ' + dt.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                                if (isSubDaily) return dt.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                                if (spanMs > 365 * 86400000) return dt.toLocaleDateString([], {year:'numeric', month:'short', day:'numeric'});
                                return dt.toLocaleDateString([], {month:'short', day:'numeric', year:'numeric'});
                            }
                            return '';
                        },
                        afterTitle(items) {
                            if (!hasSessions) return "";
                            const d = items[0] && items[0].raw;
                            if (!d || d.x == null) return "";
                            const idx = Math.round(d.x);
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
                x: { type: "linear", min: -0.5, max: ts.length - 0.5,
                    ticks: { color: "#8b8fa3", font: { size: 10 }, maxTicksLimit: 8,
                        callback(val) {
                            const i = Math.round(val); if (i < 0 || i >= ts.length) return '';
                            const d = new Date(ts[i]);
                            if (isSubDaily && multiDay) return d.toLocaleDateString([], {month:'short',day:'numeric'}) + ' ' + d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                            if (isSubDaily) return d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                            if (spanMs > 365 * 86400000) return d.toLocaleDateString([], {year:'2-digit', month:'short'});
                            return d.toLocaleDateString([], {month:'short', day:'numeric'});
                        }
                    }, grid: { color: "rgba(42,45,62,0.3)" } },
                y: { position: "right", ticks: { color: "#8b8fa3", font: { size: 10 }, callback: v => currSym(_currentCurrency) + v }, grid: { color: "rgba(42,45,62,0.3)" } },
                yVol: { position: "left", max: maxVol * 4, display: false, grid: { display: false } },
            },
        },
    });
    detailChart._sdFullMax = ts.length - 0.5;
    if (_zoomLevel !== 1) _applyZoom();
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
        const periodMap = { "1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y" };
        const intervalMap = { "1D": "5m", "1W": "15m", "1M": "1d", "3M": "1d", "6M": "1d", "1Y": "1d", "5Y": "1wk" };
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
