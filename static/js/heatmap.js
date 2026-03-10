/* ── Heatmap page — interactive treemap ─────────────────────── */

let _heatmapData = null;
let _heatmapView = 'stocks';  // stocks | sectors | etfs
let _heatmapSector = null;    // drill-down filter

async function loadHeatmap() {
    const container = document.getElementById('heatmap-container');
    if (!container) return;

    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading heatmap data…</p></div>';

    try {
        const params = new URLSearchParams({ view: _heatmapView });
        if (_heatmapSector) params.set('sector', _heatmapSector);
        const data = await api.get('/api/heatmap?' + params.toString());
        _heatmapData = data;
        renderHeatmap(data);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:24px;">Unable to load heatmap data.</p>';
    }
}

function renderHeatmap(data) {
    const container = document.getElementById('heatmap-container');
    if (!container) return;

    const items = data.items || [];
    if (!items.length) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:24px;">No data available for this view.</p>';
        return;
    }

    if (data.view === 'sectors') {
        renderTreemap(container, items, { labelKey: 'sector', sizeKey: 'market_cap', colorKey: 'change_pct', countKey: 'count', isSector: true });
    } else {
        renderTreemap(container, items, { labelKey: 'symbol', sizeKey: 'market_cap', colorKey: 'change_pct', nameKey: 'name', isSector: false });
    }

    // Update breadcrumb
    updateHeatmapBreadcrumb();
}

/* ── Squarified treemap layout ────────────────────────────────
   Implementation of the Bruls–Huizing–van Wijk algorithm.  */

function squarify(items, x, y, w, h, sizeKey) {
    if (!items.length) return [];
    const total = items.reduce((s, d) => s + (d[sizeKey] || 0), 0);
    if (total <= 0) return [];

    const rects = [];
    let remaining = [...items];
    let cx = x, cy = y, cw = w, ch = h;

    while (remaining.length > 0) {
        const isWide = cw >= ch;
        const side = isWide ? ch : cw;
        const totalArea = cw * ch;
        const remTotal = remaining.reduce((s, d) => s + (d[sizeKey] || 0), 0);

        // Lay out a row
        let row = [remaining[0]];
        let rowTotal = remaining[0][sizeKey] || 0;
        let bestRatio = _worstRatio(row, side, totalArea, remTotal, sizeKey);

        for (let i = 1; i < remaining.length; i++) {
            const next = remaining[i];
            const testRow = [...row, next];
            const testTotal = rowTotal + (next[sizeKey] || 0);
            const testRatio = _worstRatio(testRow, side, totalArea, remTotal, sizeKey);
            if (testRatio <= bestRatio) {
                row = testRow;
                rowTotal = testTotal;
                bestRatio = testRatio;
            } else {
                break;
            }
        }

        // Position the row
        const rowFraction = remTotal > 0 ? rowTotal / remTotal : 1;
        const rowSize = isWide ? cw * rowFraction : ch * rowFraction;

        let offset = 0;
        for (const item of row) {
            const frac = rowTotal > 0 ? (item[sizeKey] || 0) / rowTotal : 1 / row.length;
            const itemSize = side * frac;
            if (isWide) {
                rects.push({ item, x: cx, y: cy + offset, w: rowSize, h: itemSize });
            } else {
                rects.push({ item, x: cx + offset, y: cy, w: itemSize, h: rowSize });
            }
            offset += itemSize;
        }

        // Advance to remaining area
        if (isWide) {
            cx += rowSize;
            cw -= rowSize;
        } else {
            cy += rowSize;
            ch -= rowSize;
        }

        remaining = remaining.slice(row.length);
    }

    return rects;
}

function _worstRatio(row, side, totalArea, remTotal, sizeKey) {
    const rowSum = row.reduce((s, d) => s + (d[sizeKey] || 0), 0);
    const rowArea = totalArea * (rowSum / (remTotal || 1));
    const rowSide = rowArea / (side || 1);
    let worst = 0;
    for (const d of row) {
        const area = totalArea * ((d[sizeKey] || 0) / (remTotal || 1));
        const other = area / (rowSide || 1);
        const ratio = Math.max(rowSide / (other || 1), (other || 1) / (rowSide || 1));
        worst = Math.max(worst, ratio);
    }
    return worst;
}

/* ── Color helpers ────────────────────────────────────────────*/

function heatmapColor(changePct) {
    // From deep red (-5%) → dark gray (0%) → deep green (+5%)
    const clamped = Math.max(-5, Math.min(5, changePct));
    const t = (clamped + 5) / 10; // 0..1

    if (t < 0.5) {
        // red zone
        const r = Math.round(180 + (1 - t * 2) * 60);  // 180..240
        const g = Math.round(t * 2 * 60);                // 0..60
        const b = Math.round(t * 2 * 50);                // 0..50
        return `rgb(${r},${g},${b})`;
    }
    // green zone
    const s = (t - 0.5) * 2; // 0..1
    const r = Math.round(60 * (1 - s));    // 60..0
    const g = Math.round(100 + s * 140);   // 100..240
    const b = Math.round(50 * (1 - s));    // 50..0
    return `rgb(${r},${g},${b})`;
}

function heatmapTextColor(changePct) {
    return Math.abs(changePct) > 2 ? '#fff' : '#e1e1e1';
}

/* ── Render treemap into container ───────────────────────────*/

function renderTreemap(container, items, opts) {
    const { labelKey, sizeKey, colorKey, nameKey, isSector, countKey } = opts;

    // Measure container
    container.innerHTML = '';
    const rect = container.getBoundingClientRect();
    const W = rect.width || 900;
    const H = Math.max(500, window.innerHeight - 260);
    container.style.height = H + 'px';
    container.style.position = 'relative';

    // Sort descending by size
    const sorted = [...items].sort((a, b) => (b[sizeKey] || 0) - (a[sizeKey] || 0));

    const rects = squarify(sorted, 0, 0, W, H, sizeKey);

    const GAP = 2;
    const frag = document.createDocumentFragment();

    for (const r of rects) {
        const d = r.item;
        const changePct = d[colorKey] || 0;
        const el = document.createElement('div');
        el.className = 'hm-tile';
        el.style.left = (r.x + GAP / 2) + 'px';
        el.style.top = (r.y + GAP / 2) + 'px';
        el.style.width = Math.max(0, r.w - GAP) + 'px';
        el.style.height = Math.max(0, r.h - GAP) + 'px';
        el.style.backgroundColor = heatmapColor(changePct);
        el.style.color = heatmapTextColor(changePct);

        const showW = r.w - GAP;
        const showH = r.h - GAP;

        let inner = '';
        if (isSector) {
            const label = d[labelKey] || '';
            const cap = _fmtCap(d[sizeKey]);
            const sign = changePct >= 0 ? '+' : '';
            if (showW > 80 && showH > 50) {
                inner = `<span class="hm-label">${label}</span>
                         <span class="hm-pct">${sign}${changePct.toFixed(2)}%</span>
                         <span class="hm-cap">${cap} · ${d[countKey] || 0} stocks</span>`;
            } else if (showW > 50 && showH > 30) {
                inner = `<span class="hm-label hm-label-sm">${label}</span>
                         <span class="hm-pct">${sign}${changePct.toFixed(2)}%</span>`;
            }
        } else {
            const sym = d[labelKey] || '';
            const name = d[nameKey] || '';
            const sign = changePct >= 0 ? '+' : '';
            if (showW > 70 && showH > 50) {
                inner = `<span class="hm-label">${sym}</span>
                         <span class="hm-pct">${sign}${changePct.toFixed(2)}%</span>
                         <span class="hm-cap">${_fmtCap(d[sizeKey])}</span>`;
            } else if (showW > 40 && showH > 24) {
                inner = `<span class="hm-label hm-label-sm">${sym}</span>
                         <span class="hm-pct hm-pct-sm">${sign}${changePct.toFixed(2)}%</span>`;
            } else if (showW > 28 && showH > 16) {
                inner = `<span class="hm-label hm-label-xs">${sym}</span>`;
            }
        }

        el.innerHTML = inner;

        // Tooltip
        if (isSector) {
            el.title = `${d[labelKey]}  ${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%  Cap: ${_fmtCap(d[sizeKey])}  (${d[countKey] || 0} stocks)`;
        } else {
            el.title = `${d[labelKey]} — ${d[nameKey] || ''}  ${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%  Cap: ${_fmtCap(d[sizeKey])}`;
        }

        // Click handler — drill-down
        if (isSector) {
            el.style.cursor = 'pointer';
            const sectorName = d[labelKey];
            el.addEventListener('click', () => {
                _heatmapView = 'stocks';
                _heatmapSector = sectorName;
                setActiveViewBtn('stocks');
                loadHeatmap();
            });
        } else {
            el.style.cursor = 'pointer';
            el.dataset.symbol = d.symbol;
            el.dataset.stockName = d.name || d.symbol;
            el.dataset.stockPrice = d.price || '';
            el.addEventListener('click', () => {
                if (typeof navigateToStock === 'function') {
                    navigateToStock(d.symbol);
                }
            });
        }

        frag.appendChild(el);
    }

    container.appendChild(frag);
}

/* ── View switching ──────────────────────────────────────────*/

function setHeatmapView(view) {
    _heatmapView = view;
    _heatmapSector = null;
    setActiveViewBtn(view);
    loadHeatmap();
}

function setActiveViewBtn(view) {
    document.querySelectorAll('.hm-view-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
}

function updateHeatmapBreadcrumb() {
    const bc = document.getElementById('hm-breadcrumb');
    if (!bc) return;
    if (_heatmapSector) {
        bc.innerHTML = `<a href="#" onclick="setHeatmapView('sectors');return false;">All Sectors</a> <span class="hm-bc-sep">›</span> <strong>${_heatmapSector}</strong>`;
        bc.style.display = '';
    } else if (_heatmapView === 'sectors') {
        bc.innerHTML = '<strong>All Sectors</strong> <span class="hm-bc-hint">— click a sector to drill down</span>';
        bc.style.display = '';
    } else {
        bc.style.display = 'none';
    }
}

/* ── Helpers ─────────────────────────────────────────────────*/

function _fmtCap(cap) {
    if (!cap) return '';
    if (cap >= 1e12) return '$' + (cap / 1e12).toFixed(1) + 'T';
    if (cap >= 1e9) return '$' + (cap / 1e9).toFixed(1) + 'B';
    if (cap >= 1e6) return '$' + (cap / 1e6).toFixed(0) + 'M';
    return '$' + cap.toLocaleString();
}

/* ── Resize handling ─────────────────────────────────────────*/
let _hmResizeTimer = null;
window.addEventListener('resize', () => {
    if (_heatmapData && document.getElementById('page-heatmap')?.classList.contains('active')) {
        clearTimeout(_hmResizeTimer);
        _hmResizeTimer = setTimeout(() => renderHeatmap(_heatmapData), 200);
    }
});
