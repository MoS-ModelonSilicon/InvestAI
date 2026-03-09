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
    if (!_vsData && !keepPage) {
        container.innerHTML = '<div class="text-center" style="padding:40px;"><div class="spinner"></div><p style="margin-top:12px;color:var(--text-muted);">Loading results...</p></div>';
    }

    try {
        const url = `/api/value-scanner?${params}`;
        console.log("[VS] Fetching:", url);
        const data = await api.get(url);
        console.log("[VS] Response:", data.stats, "progress:", data.progress, "page candidates:", data.candidates?.length);
        _vsData = data;
        renderStatCards(data.stats);
        renderProgress(data.progress);
        renderCandidates(data.candidates);
        renderPagination(data.pagination);
        renderRejected(data.rejected);
        renderSectorTabs(data);

        const statsEl = document.getElementById("vs-stats");
        if (statsEl) {
            let txt = `${data.stats.scanned} scanned · ${data.stats.candidates} candidates`;
            if (data.progress.complete && data.progress.updated_at) {
                const ago = Math.round((Date.now() / 1000) - data.progress.updated_at);
                if (ago < 60) txt += ` · updated just now`;
                else if (ago < 3600) txt += ` · updated ${Math.round(ago / 60)}m ago`;
                else txt += ` · updated ${Math.round(ago / 3600)}h ago`;
            }
            statsEl.textContent = txt;
        }

        if (!data.progress.complete) {
            _startPolling();
        } else {
            _stopPolling();
        }
    } catch (err) {
        console.error("[VS] Error:", err);
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
        "Consider":   { cls: "vs-sig-consider", icon: "◐" },
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
        const globalIdx = pageOffset + i;
        html += `<div class="vs-row-wrap" id="vs-row-${globalIdx}">
        <div class="vs-table-row" data-symbol="${c.symbol}" data-stock-name="${(c.name||"").replace(/"/g,'&quot;')}" data-stock-price="${c.price || 0}" onclick="toggleVSDetail(${globalIdx})">
            <div class="vs-col-rank">${globalIdx + 1}</div>
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
            <div class="vs-col-links" onclick="event.stopPropagation()">
                <a href="https://finance.yahoo.com/quote/${c.symbol}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Yahoo Finance">YF</a>
                <a href="https://finviz.com/quote.ashx?t=${c.symbol}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Finviz">FV</a>
                ${stockQuickActions(c.symbol, c.name, c.price, {hideDetail: true})}
            </div>
        </div>
        <div class="vs-detail" id="vs-detail-${globalIdx}" style="display:none;"></div>
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

// ── Action Plan Modal ──────────────────────────────────────
let _vapData = null;

async function openActionPlanModal() {
    // Build query params matching current filters
    const params = new URLSearchParams();
    const sector = document.getElementById("vs-sector").value;
    const signal = document.getElementById("vs-signal").value;
    const amountInput = document.getElementById("vap-invest-amount");
    const amount = amountInput ? parseFloat(amountInput.value) || 10000 : 10000;
    params.set("amount", amount);
    if (sector) params.set("sector", sector);
    if (signal) params.set("signal", signal);

    // Create or get overlay
    let overlay = document.getElementById("vap-modal-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "vap-modal-overlay";
        overlay.className = "modal-overlay";
        overlay.onclick = (e) => { if (e.target === overlay) overlay.classList.remove("open"); };
        document.body.appendChild(overlay);
    }

    // Show loading state
    overlay.innerHTML = `
        <div class="modal vap-modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2>📋 Action Plan</h2>
                <button class="modal-close" onclick="document.getElementById('vap-modal-overlay').classList.remove('open')">&times;</button>
            </div>
            <div class="vap-body" style="padding:60px;text-align:center;">
                <div class="spinner"></div>
                <p style="margin-top:12px;color:var(--text-muted);">Generating your action plan...</p>
            </div>
        </div>`;
    overlay.classList.add("open");

    try {
        const data = await api.get(`/api/value-scanner/action-plan?${params}`);
        _vapData = data;
        renderActionPlanModal(data, amount);
    } catch (err) {
        overlay.innerHTML = `
            <div class="modal vap-modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>📋 Action Plan</h2>
                    <button class="modal-close" onclick="document.getElementById('vap-modal-overlay').classList.remove('open')">&times;</button>
                </div>
                <div class="vap-body" style="padding:40px;text-align:center;">
                    <p style="color:var(--red);">Failed to generate action plan. Try again later.</p>
                </div>
            </div>`;
    }
}

function renderActionPlanModal(data, amount) {
    const overlay = document.getElementById("vap-modal-overlay");
    if (!overlay) return;

    const summary = data.summary;
    const plan = data.plan;

    // Signal group icons & colors
    const signalMeta = {
        "Strong Buy": { icon: "🟢", cls: "vap-sig-strong", emoji: "▲▲" },
        "Buy":        { icon: "🔵", cls: "vap-sig-buy",    emoji: "▲" },
        "Watch":      { icon: "🟡", cls: "vap-sig-watch",  emoji: "●" },
        "Consider":   { icon: "⚪", cls: "vap-sig-consider", emoji: "◐" },
    };

    // Build summary bar breakdown
    let breakdownHTML = "";
    for (const [sig, info] of Object.entries(summary.signal_breakdown)) {
        const meta = signalMeta[sig] || signalMeta.Watch;
        breakdownHTML += `
            <div class="vap-breakdown-item ${meta.cls}">
                <span class="vap-bd-icon">${meta.icon}</span>
                <span class="vap-bd-label">${sig}</span>
                <span class="vap-bd-count">${info.count} stocks</span>
                <span class="vap-bd-pct">${info.allocation_pct}%</span>
                <span class="vap-bd-dollars">$${info.allocation_dollars.toLocaleString()}</span>
            </div>`;
    }

    // Build group sections
    let groupsHTML = "";
    for (const group of plan) {
        const meta = signalMeta[group.signal] || signalMeta.Watch;

        let stockRows = "";
        for (const s of group.stocks) {
            const mosFmt = s.mos !== null && s.mos !== undefined
                ? `<span style="color:${s.mos >= 30 ? 'var(--green)' : s.mos >= 0 ? '#eab308' : 'var(--red)'}">${s.mos > 0 ? '+' : ''}${s.mos.toFixed(1)}%</span>`
                : '<span style="color:var(--text-muted)">N/A</span>';

            const strengthsHTML = s.strengths.map(st => `<span class="vap-tag vap-tag-green">✓ ${st}</span>`).join("");
            const weaknessesHTML = s.weaknesses.map(w => `<span class="vap-tag vap-tag-red">✗ ${w}</span>`).join("");

            stockRows += `
                <div class="vap-stock-row">
                    <div class="vap-stock-main">
                        <div class="vap-stock-info">
                            <strong class="vap-stock-sym" onclick="navigateToStock('${s.symbol}');document.getElementById('vap-modal-overlay').classList.remove('open');">${s.symbol}</strong>
                            <span class="vap-stock-name">${s.name}</span>
                            <span class="vap-stock-sector">${s.sector}</span>
                        </div>
                        <div class="vap-stock-metrics">
                            <div class="vap-metric"><span class="vap-metric-label">Price</span><span class="vap-metric-val">${currSym(s.currency)}${s.price.toFixed(2)}</span></div>
                            <div class="vap-metric"><span class="vap-metric-label">Quality</span><span class="vap-metric-val">${s.quality}</span></div>
                            <div class="vap-metric"><span class="vap-metric-label">MOS</span><span class="vap-metric-val">${mosFmt}</span></div>
                            <div class="vap-metric"><span class="vap-metric-label">P/E</span><span class="vap-metric-val">${s.pe_ratio != null ? s.pe_ratio.toFixed(1) : '—'}</span></div>
                        </div>
                        <div class="vap-stock-alloc">
                            <div class="vap-alloc-bar"><div class="vap-alloc-fill" style="width:${Math.min(s.allocation_pct * 2, 100)}%"></div></div>
                            <span class="vap-alloc-pct">${s.allocation_pct}%</span>
                            <span class="vap-alloc-dollars">$${s.allocation_dollars.toLocaleString()}</span>
                            <span class="vap-alloc-shares">≈ ${s.suggested_shares} shares</span>
                        </div>
                    </div>
                    <div class="vap-stock-tags">
                        ${strengthsHTML}${weaknessesHTML}
                    </div>
                </div>`;
        }

        groupsHTML += `
            <div class="vap-group ${meta.cls}">
                <div class="vap-group-header">
                    <div class="vap-group-title">
                        <span class="vap-group-icon">${meta.icon}</span>
                        <h3>${group.signal}</h3>
                        <span class="vap-group-badge">${group.stocks.length} stock${group.stocks.length > 1 ? 's' : ''}</span>
                        <span class="vap-group-alloc">${group.group_allocation_pct}% · $${group.group_allocation_dollars.toLocaleString()}</span>
                    </div>
                    <div class="vap-group-action">${group.action}</div>
                </div>
                <div class="vap-group-strategy">
                    <div class="vap-strategy-row">
                        <span class="vap-strat-icon">📌</span>
                        <span>${group.strategy}</span>
                    </div>
                    <div class="vap-strategy-row">
                        <span class="vap-strat-icon">📊</span>
                        <span><strong>Position limit:</strong> ${group.position_limit}</span>
                    </div>
                    <div class="vap-strategy-row">
                        <span class="vap-strat-icon">⚠️</span>
                        <span><strong>Risk:</strong> ${group.risk_note}</span>
                    </div>
                </div>
                <div class="vap-group-stocks">${stockRows}</div>
            </div>`;
    }

    const noStocks = summary.stocks_count === 0;

    overlay.innerHTML = `
        <div class="modal vap-modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2>📋 Action Plan</h2>
                <button class="modal-close" onclick="document.getElementById('vap-modal-overlay').classList.remove('open')">&times;</button>
            </div>
            <div class="vap-body">
                <div class="vap-invest-row">
                    <label>Investment Amount</label>
                    <div class="vap-invest-input-wrap">
                        <span class="vap-dollar">$</span>
                        <input type="number" id="vap-invest-amount" value="${amount}" min="100" max="10000000" step="100">
                        <button class="btn btn-sm btn-primary" onclick="refreshActionPlan()">Update</button>
                    </div>
                </div>
                ${!data.ready ? '<div class="vap-warning">⏳ Scan still in progress — plan may be incomplete. Re-open later for full results.</div>' : ''}
                ${noStocks
                    ? '<div class="vap-empty"><p>No candidates match the current filters. Adjust filters or wait for the scan to complete.</p></div>'
                    : `
                <div class="vap-summary-bar">
                    <div class="vap-summary-stat">
                        <span class="vap-sum-num">${summary.stocks_count}</span>
                        <span class="vap-sum-label">Stocks</span>
                    </div>
                    <div class="vap-summary-stat">
                        <span class="vap-sum-num">$${summary.allocated.toLocaleString()}</span>
                        <span class="vap-sum-label">Allocated</span>
                    </div>
                    <div class="vap-summary-breakdown">${breakdownHTML}</div>
                </div>
                <div class="vap-groups">${groupsHTML}</div>
                <div class="vap-actions">
                    <button class="btn btn-ghost" onclick="document.getElementById('vap-modal-overlay').classList.remove('open')">Close</button>
                    <button class="btn btn-primary" onclick="buyActionPlanBundle()">
                        💰 Buy All ${summary.stocks_count} Stocks
                    </button>
                </div>
                <div class="vap-disclaimer">This is for educational purposes only — not financial advice. Always do your own research.</div>
                `}
            </div>
        </div>`;
}

function refreshActionPlan() {
    openActionPlanModal();
}

// ── Expandable "Why Selected" detail per row ──────────────

function toggleVSDetail(globalIdx) {
    const el = document.getElementById(`vs-detail-${globalIdx}`);
    if (!el) return;

    if (el.style.display !== "none") {
        el.style.display = "none";
        return;
    }

    // Find the candidate from current data
    const pageOffset = (_vsCurrentPage - 1) * VS_PER_PAGE;
    const localIdx = globalIdx - pageOffset;
    const c = _vsData && _vsData.candidates ? _vsData.candidates[localIdx] : null;
    if (!c) return;

    el.innerHTML = buildVSDetailPanel(c);
    el.style.display = "block";
}

function buildVSDetailPanel(c) {
    // Build "Why Selected" rationale from criteria + metrics
    const passed = (c.criteria || []).filter(cr => cr.passed);
    const failed = (c.criteria || []).filter(cr => !cr.passed);

    let reasonParts = [];
    // Quality assessment
    if (c.quality >= 70) reasonParts.push(`High quality score (${c.quality}/100) indicates a fundamentally strong company`);
    else if (c.quality >= 50) reasonParts.push(`Decent quality score (${c.quality}/100) shows reasonable fundamentals`);
    else reasonParts.push(`Quality score of ${c.quality}/100 — may need extra due diligence`);

    // Margin of safety
    if (c.mos != null && c.mos > 0) reasonParts.push(`Trading ${c.mos.toFixed(0)}% below estimated intrinsic value (margin of safety)`);
    else if (c.mos != null && c.mos <= 0) reasonParts.push(`Trading near or above estimated intrinsic value — limited margin of safety`);

    // Key strengths from passed criteria
    if (passed.length > 0) {
        reasonParts.push(`Passes ${passed.length}/${c.criteria.length} Graham criteria`);
    }

    const reasonText = reasonParts.join(". ") + ".";

    // Criteria detail breakdown
    const criteriaHtml = (c.criteria || []).map(cr => {
        const icon = cr.passed ? "✓" : "✗";
        const cls = cr.passed ? "vs-crit-detail-pass" : "vs-crit-detail-fail";
        return `<div class="vs-crit-detail-row ${cls}">
            <span class="vs-crit-detail-icon">${icon}</span>
            <span class="vs-crit-detail-label">${cr.label}</span>
            <span class="vs-crit-detail-val">${cr.detail}</span>
        </div>`;
    }).join("");

    // Strengths & weaknesses tags
    const strengthsHtml = passed.map(cr => `<span class="vs-why-tag vs-why-tag-green">✓ ${cr.detail}</span>`).join("");
    const weaknessesHtml = failed.map(cr => `<span class="vs-why-tag vs-why-tag-red">✗ ${cr.detail}</span>`).join("");

    // Key metrics grid
    const metrics = [
        ["P/E Ratio", c.pe_ratio != null ? c.pe_ratio.toFixed(1) : "—"],
        ["Return on Equity", c.roe != null ? c.roe.toFixed(1) + "%" : "—"],
        ["Debt/Equity", c.debt_to_equity != null ? c.debt_to_equity.toFixed(2) : "—"],
        ["Profit Margin", c.profit_margin != null ? c.profit_margin.toFixed(1) + "%" : "—"],
        ["FCF Yield", c.fcf_yield != null ? c.fcf_yield.toFixed(1) + "%" : "—"],
        ["Dividend Yield", c.dividend_yield != null ? c.dividend_yield.toFixed(2) + "%" : "—"],
        ["Current Ratio", c.current_ratio != null ? c.current_ratio.toFixed(2) : "—"],
        ["Revenue Growth", c.revenue_growth != null ? (c.revenue_growth > 0 ? "+" : "") + c.revenue_growth.toFixed(1) + "%" : "—"],
    ].filter(r => r[1] !== "—");

    const metricsHtml = metrics.map(([label, val]) =>
        `<div class="vs-why-metric"><span class="vs-why-metric-label">${label}</span><span class="vs-why-metric-val">${val}</span></div>`
    ).join("");

    return `<div class="vs-why-panel">
        <div class="vs-why-header">
            <div class="vs-why-title">Why ${c.symbol} Was Selected</div>
            <button class="btn btn-sm" onclick="event.stopPropagation();navigateToStock('${c.symbol}')" title="Full stock detail">📈 Full Detail</button>
        </div>
        <div class="vs-why-reason">${reasonText}</div>
        <div class="vs-why-tags">${strengthsHtml}${weaknessesHtml}</div>
        <div class="vs-why-sections">
            <div class="vs-why-criteria">
                <div class="vs-why-section-title">Graham Criteria Breakdown</div>
                ${criteriaHtml}
            </div>
            <div class="vs-why-metrics">
                <div class="vs-why-section-title">Key Fundamentals</div>
                <div class="vs-why-metrics-grid">${metricsHtml}</div>
            </div>
        </div>
    </div>`;
}

function buyActionPlanBundle() {
    if (!_vapData || !_vapData.plan) return;

    const stocks = [];
    for (const group of _vapData.plan) {
        for (const s of group.stocks) {
            stocks.push({
                symbol: s.symbol,
                name: s.name,
                price: s.price,
                allocation_pct: s.allocation_pct,
            });
        }
    }

    // Close action plan modal
    const overlay = document.getElementById("vap-modal-overlay");
    if (overlay) overlay.classList.remove("open");

    // Open the existing bundle buy modal
    if (typeof buyStockBundle === "function") {
        buyStockBundle(stocks);
    }
}
