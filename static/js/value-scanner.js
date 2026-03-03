let _vsLoaded = false;
let _vsData = null;
let _vsPolling = null;
let _vsCurrentPage = 1;
const VS_PER_PAGE = 15;

async function loadValueScanner() {
    if (!_vsLoaded) {
        try {
            const data = await api.get("/api/value-scanner/sectors");
            const sel = document.getElementById("vs-sector");
            sel.innerHTML = '<option value="">All Sectors</option>';
            (data.sectors || []).forEach(s => {
                sel.innerHTML += `<option value="${s}">${s}</option>`;
            });
        } catch (e) { /* sectors optional */ }
        _vsLoaded = true;
    }
    _vsCurrentPage = 1;
    runValueScanner();
}

function _stopPolling() {
    if (_vsPolling) {
        clearInterval(_vsPolling);
        _vsPolling = null;
    }
}

async function runValueScanner(keepPage) {
    if (!keepPage) _vsCurrentPage = 1;

    const params = new URLSearchParams();
    const sector = document.getElementById("vs-sector").value;
    const signal = document.getElementById("vs-signal").value;
    const sort = document.getElementById("vs-sort").value;

    if (sector) params.set("sector", sector);
    if (signal) params.set("signal", signal);
    if (sort) params.set("sort_by", sort);
    params.set("page", _vsCurrentPage);
    params.set("per_page", VS_PER_PAGE);

    const container = document.getElementById("vs-candidates");
    if (!_vsData) {
        container.innerHTML = '<div class="text-center" style="padding:40px;"><div class="spinner"></div><p style="margin-top:12px;color:var(--text-muted);">Starting scan...</p></div>';
    }

    try {
        const data = await api.get(`/api/value-scanner?${params}`);
        _vsData = data;
        renderStatCards(data.stats);
        renderProgress(data.progress);
        renderCandidates(data.candidates);
        renderPagination(data.pagination);
        renderRejected(data.rejected);
        renderSectorTabs(data);

        const statsEl = document.getElementById("vs-stats");
        if (statsEl) statsEl.textContent = `${data.stats.scanned} scanned · ${data.stats.candidates} candidates`;

        if (!data.progress.complete) {
            _startPolling();
        } else {
            _stopPolling();
        }
    } catch (err) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Error loading data. Try again later.</p>';
        _stopPolling();
    }
}

function _startPolling() {
    if (_vsPolling) return;
    _vsPolling = setInterval(() => {
        runValueScanner(true);
    }, 4000);
}

function renderProgress(progress) {
    const el = document.getElementById("vs-progress");
    if (!el) return;

    if (progress.complete) {
        el.style.display = "none";
        return;
    }

    el.style.display = "block";
    const pct = progress.total > 0 ? Math.round((progress.scanned / progress.total) * 100) : 0;
    el.innerHTML = `
        <div class="vs-progress-bar">
            <div class="vs-progress-fill" style="width:${pct}%"></div>
        </div>
        <div class="vs-progress-text">
            Scanning stocks... ${progress.scanned} of ${progress.total} (${pct}%)
        </div>`;
}

function renderStatCards(stats) {
    const el = document.getElementById("vs-stat-cards");
    el.innerHTML = `
        <div class="vs-stat-card">
            <div class="vs-stat-num">${stats.scanned}</div>
            <div class="vs-stat-label">Stocks Scanned</div>
        </div>
        <div class="vs-stat-card vs-stat-green">
            <div class="vs-stat-num">${stats.candidates}</div>
            <div class="vs-stat-label">Candidates</div>
        </div>
        <div class="vs-stat-card vs-stat-red">
            <div class="vs-stat-num">${stats.rejected}</div>
            <div class="vs-stat-label">Rejected</div>
        </div>`;
}

function renderSectorTabs(data) {
    const el = document.getElementById("vs-sector-tabs");
    const candidates = data.candidates || [];
    const totalCandidates = data.pagination ? data.pagination.total_items : candidates.length;

    const sectors = {};
    candidates.forEach(c => {
        sectors[c.sector] = (sectors[c.sector] || 0) + 1;
    });

    if (totalCandidates <= 0) { el.innerHTML = ""; return; }

    const sorted = Object.entries(sectors).sort((a, b) => b[1] - a[1]);
    el.innerHTML = `<button class="vs-tab vs-tab-active" onclick="filterVSSector(this, '')">All (${totalCandidates})</button>` +
        sorted.map(([s, n]) => `<button class="vs-tab" onclick="filterVSSector(this, '${s}')">${s} (${n})</button>`).join("");
}

function filterVSSector(btn, sector) {
    document.querySelectorAll(".vs-tab").forEach(t => t.classList.remove("vs-tab-active"));
    btn.classList.add("vs-tab-active");
    const sectorEl = document.getElementById("vs-sector");
    sectorEl.value = sector;
    _vsCurrentPage = 1;
    runValueScanner();
}

function vsSignalBadge(signal) {
    const map = {
        "Strong Buy": { cls: "vs-sig-strong", icon: "▲▲" },
        "Buy":        { cls: "vs-sig-buy",    icon: "▲" },
        "Watch":      { cls: "vs-sig-watch",  icon: "●" },
    };
    const s = map[signal] || map.Watch;
    return `<span class="vs-signal ${s.cls}">${s.icon} ${signal}</span>`;
}

function vsQualityBar(q) {
    const color = q >= 70 ? "var(--green)" : q >= 50 ? "#eab308" : q >= 30 ? "var(--red)" : "#64748b";
    return `<div class="vs-quality-wrap">
        <span class="vs-quality-num" style="color:${color}">${q}</span>
        <div class="vs-quality-track"><div class="vs-quality-fill" style="width:${q}%;background:${color}"></div></div>
    </div>`;
}

function vsMosBadge(mos) {
    if (mos === null || mos === undefined) return '<span class="vs-mos vs-mos-na">N/A</span>';
    const color = mos >= 30 ? "var(--green)" : mos >= 0 ? "#eab308" : "var(--red)";
    return `<span class="vs-mos" style="color:${color}">${mos > 0 ? "+" : ""}${mos.toFixed(1)}%</span>`;
}

function vsCriteriaIcons(criteria) {
    return criteria.map(c =>
        `<span class="vs-crit ${c.passed ? "vs-crit-pass" : "vs-crit-fail"}" title="${c.label}: ${c.detail}">${c.passed ? "✓" : "✗"}</span>`
    ).join("");
}

function renderCandidates(candidates) {
    const container = document.getElementById("vs-candidates");

    if (!candidates || candidates.length === 0) {
        const prog = _vsData && _vsData.progress;
        if (prog && !prog.complete) {
            container.innerHTML = '<div class="text-center" style="padding:40px;"><div class="spinner"></div><p style="margin-top:12px;color:var(--text-muted);">Scanning in progress... results will appear shortly.</p></div>';
        } else {
            container.innerHTML = '<div class="empty-state"><p>No candidates match the current filters. Try adjusting the signal or sector filter.</p></div>';
        }
        return;
    }

    const pageOffset = (_vsCurrentPage - 1) * VS_PER_PAGE;

    let html = `<div class="vs-table">
        <div class="vs-table-header">
            <div class="vs-col-rank">#</div>
            <div class="vs-col-signal">Signal</div>
            <div class="vs-col-ticker">Ticker</div>
            <div class="vs-col-company">Company</div>
            <div class="vs-col-sector">Sector</div>
            <div class="vs-col-quality">Quality</div>
            <div class="vs-col-mos">MOS</div>
            <div class="vs-col-pe">P/E</div>
            <div class="vs-col-roe">ROE</div>
            <div class="vs-col-de">D/E</div>
            <div class="vs-col-fcfy">FCF Yield</div>
            <div class="vs-col-cr">C.Ratio</div>
            <div class="vs-col-checks">Checks</div>
            <div class="vs-col-links">Links</div>
        </div>`;

    candidates.forEach((c, i) => {
        html += `<div class="vs-table-row" onclick="navigateToStock('${c.symbol}')">
            <div class="vs-col-rank">${pageOffset + i + 1}</div>
            <div class="vs-col-signal">${vsSignalBadge(c.signal)}</div>
            <div class="vs-col-ticker"><strong>${c.symbol}</strong></div>
            <div class="vs-col-company">${c.name}</div>
            <div class="vs-col-sector"><span class="vs-sector-badge">${c.sector}</span></div>
            <div class="vs-col-quality">${vsQualityBar(c.quality)}</div>
            <div class="vs-col-mos">${vsMosBadge(c.mos)}</div>
            <div class="vs-col-pe">${c.pe_ratio != null ? c.pe_ratio.toFixed(1) : "—"}</div>
            <div class="vs-col-roe">${c.roe != null ? c.roe.toFixed(1) + "%" : "—"}</div>
            <div class="vs-col-de">${c.debt_to_equity != null ? c.debt_to_equity.toFixed(2) : "—"}</div>
            <div class="vs-col-fcfy">${c.fcf_yield != null ? c.fcf_yield.toFixed(1) + "%" : "—"}</div>
            <div class="vs-col-cr">${c.current_ratio != null ? c.current_ratio.toFixed(2) : "—"}</div>
            <div class="vs-col-checks">${vsCriteriaIcons(c.criteria)}</div>
            <div class="vs-col-links">
                <a href="https://finance.yahoo.com/quote/${c.symbol}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Yahoo Finance">YF</a>
                <a href="https://finviz.com/quote.ashx?t=${c.symbol}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Finviz">FV</a>
            </div>
        </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}

function renderPagination(pagination) {
    const el = document.getElementById("vs-pagination");
    if (!el) return;

    if (!pagination || pagination.total_pages <= 1) {
        el.innerHTML = "";
        return;
    }

    const { page, total_pages, total_items, per_page } = pagination;
    const start = (page - 1) * per_page + 1;
    const end = Math.min(page * per_page, total_items);

    let btns = "";

    btns += `<button class="vs-page-btn" ${page <= 1 ? "disabled" : ""} onclick="vsGoPage(${page - 1})">‹ Prev</button>`;

    const range = _pageRange(page, total_pages);
    for (const p of range) {
        if (p === "...") {
            btns += `<span class="vs-page-dots">…</span>`;
        } else {
            btns += `<button class="vs-page-btn ${p === page ? "vs-page-active" : ""}" onclick="vsGoPage(${p})">${p}</button>`;
        }
    }

    btns += `<button class="vs-page-btn" ${page >= total_pages ? "disabled" : ""} onclick="vsGoPage(${page + 1})">Next ›</button>`;

    el.innerHTML = `
        <div class="vs-pagination-info">Showing ${start}–${end} of ${total_items} candidates</div>
        <div class="vs-pagination-buttons">${btns}</div>`;
}

function _pageRange(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

    const pages = [1];
    const left = Math.max(2, current - 1);
    const right = Math.min(total - 1, current + 1);

    if (left > 2) pages.push("...");
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < total - 1) pages.push("...");
    pages.push(total);

    return pages;
}

function vsGoPage(p) {
    _vsCurrentPage = p;
    runValueScanner(true);
    const container = document.getElementById("vs-candidates");
    if (container) container.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderRejected(rejected) {
    const toggle = document.getElementById("vs-rejected-toggle");
    const countEl = document.getElementById("vs-rejected-count");
    const container = document.getElementById("vs-rejected");

    if (!rejected || rejected.length === 0) {
        toggle.style.display = "none";
        container.style.display = "none";
        return;
    }

    toggle.style.display = "flex";
    countEl.textContent = rejected.length;

    let html = '<div class="vs-rej-table"><div class="vs-rej-header"><div>Ticker</div><div>Company</div><div>Sector</div><div>Rejection Reasons</div></div>';
    rejected.forEach(r => {
        html += `<div class="vs-rej-row">
            <div><strong>${r.symbol}</strong></div>
            <div>${r.name}</div>
            <div>${r.sector}</div>
            <div class="vs-rej-reasons">${r.reasons.join(" · ")}</div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function toggleRejected() {
    const el = document.getElementById("vs-rejected");
    const arrow = document.getElementById("vs-rej-arrow");
    if (el.style.display === "none") {
        el.style.display = "block";
        arrow.style.transform = "rotate(180deg)";
    } else {
        el.style.display = "none";
        arrow.style.transform = "";
    }
}

function toggleVSMethodology() {
    const el = document.getElementById("vs-methodology");
    const arrow = document.getElementById("vs-meth-arrow");
    if (el.style.display === "none") {
        el.style.display = "block";
        arrow.style.transform = "rotate(180deg)";
    } else {
        el.style.display = "none";
        arrow.style.transform = "";
    }
}
