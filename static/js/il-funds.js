let _ilMeta = null;
let _ilResults = [];
let _ilPage = 1;
const _ilPerPage = 50;

async function loadILFunds() {
    const container = document.getElementById("il-funds-container");
    if (!container) return;

    container.querySelector("#il-results-area").innerHTML =
        '<div class="text-center" style="padding:40px;"><div class="spinner"></div><p style="margin-top:12px;color:var(--text-muted);">Fetching live fund data from funder.co.il...</p></div>';

    try {
        if (!_ilMeta) {
            _ilMeta = await api.get("/api/il-funds/meta");
            buildILFilters();
        }
    } catch (e) { /* ignore */ }

    await Promise.all([loadBestDeals(), runILSearch()]);
}

async function loadBestDeals() {
    const el = document.getElementById("il-kaspit-highlight");
    if (!el) return;
    try {
        const cat = document.getElementById("il-filter-type")?.value || "";
        const url = cat ? `/api/il-funds/best?category=${encodeURIComponent(cat)}&top_n=3` : "/api/il-funds/best?category=Kaspit (Money Market)&top_n=3";
        const data = await api.get(url);
        renderBestDeals(el, data);
    } catch (e) {
        el.innerHTML = "";
    }
}

function renderBestDeals(el, data) {
    const best = data.top_funds?.[0];
    const st = data.stats || {};
    if (!best) { el.innerHTML = ""; return; }

    el.innerHTML = `
        <div class="il-highlight-card">
            <div class="il-hl-header">
                <span class="il-hl-title">Best Deal — Lowest Fee</span>
                <span class="il-hl-badge">#1</span>
            </div>
            <div class="il-hl-body">
                <div class="il-hl-fund-name">${best.name}</div>
                <div class="il-hl-manager">${best.manager} · ${best.category}</div>
                <div class="il-hl-stats">
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val il-fee-best">${best.fee}%</span>
                        <span class="il-hl-stat-label">Management Fee</span>
                    </div>
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val">${best.annual_return != null ? best.annual_return + "%" : "—"}</span>
                        <span class="il-hl-stat-label">Annual Return</span>
                    </div>
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val">${fmtILS(best.size_m)}M</span>
                        <span class="il-hl-stat-label">Fund Size (₪)</span>
                    </div>
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val il-savings">₪${best.savings_vs_avg_100k || 0}</span>
                        <span class="il-hl-stat-label">Save /₪100K vs avg</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="il-highlight-card il-hl-summary">
            <div class="il-hl-header"><span class="il-hl-title">Market Overview</span></div>
            <div class="il-hl-body">
                <div class="il-hl-stats">
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val">${st.total_funds || 0}</span>
                        <span class="il-hl-stat-label">Funds in Category</span>
                    </div>
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val">${st.avg_fee || 0}%</span>
                        <span class="il-hl-stat-label">Avg Fee</span>
                    </div>
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val">${st.min_fee || 0}% — ${st.max_fee || 0}%</span>
                        <span class="il-hl-stat-label">Fee Range</span>
                    </div>
                    <div class="il-hl-stat">
                        <span class="il-hl-stat-val il-savings">₪${st.savings_best_vs_worst_100k || 0}</span>
                        <span class="il-hl-stat-label">Best vs Worst /₪100K</span>
                    </div>
                </div>
            </div>
        </div>`;
}

function buildILFilters() {
    if (!_ilMeta) return;
    const typeSel = document.getElementById("il-filter-type");
    const mgrSel = document.getElementById("il-filter-manager");
    if (typeSel) {
        typeSel.innerHTML = '<option value="">All Types</option>';
        (_ilMeta.categories || []).forEach(t => { typeSel.innerHTML += `<option value="${t}">${t}</option>`; });
    }
    if (mgrSel) {
        mgrSel.innerHTML = '<option value="">All Managers</option>';
        (_ilMeta.managers || []).forEach(m => { mgrSel.innerHTML += `<option value="${m}">${m}</option>`; });
    }
}

async function runILSearch(page) {
    if (page !== undefined) _ilPage = page;
    else _ilPage = 1;

    const params = new URLSearchParams();
    const v = id => { const el = document.getElementById(id); return el ? el.value : ""; };

    if (v("il-filter-type")) params.set("fund_type", v("il-filter-type"));
    if (v("il-filter-manager")) params.set("manager", v("il-filter-manager"));
    if (v("il-filter-sort")) params.set("sort_by", v("il-filter-sort"));
    if (v("il-filter-max-fee")) params.set("max_fee", v("il-filter-max-fee"));
    if (v("il-filter-min-return")) params.set("min_return", v("il-filter-min-return"));
    if (v("il-filter-min-size")) params.set("min_size", v("il-filter-min-size"));
    if (document.getElementById("il-filter-kosher")?.checked) params.set("kosher_only", "true");
    params.set("page", _ilPage);
    params.set("per_page", _ilPerPage);

    const resultsEl = document.getElementById("il-results-area");
    const countEl = document.getElementById("il-result-count");
    if (!resultsEl) return;

    try {
        const data = await api.get(`/api/il-funds?${params}`);
        const funds = data.items || [];
        _ilResults = funds;
        if (countEl) countEl.textContent = `${data.total} funds`;
        renderILResults(resultsEl, funds, data);
        renderPagination("il-pagination", data, "ilGoPage");
    } catch (e) {
        resultsEl.innerHTML = '<p style="color:var(--red);padding:20px;">Error loading funds. Check connection.</p>';
    }
}

function ilGoPage(p) {
    runILSearch(p);
    document.getElementById("page-il-funds")?.scrollTo({ top: 0, behavior: "smooth" });
}

function renderILResults(el, funds, pageData) {
    if (funds.length === 0) {
        el.innerHTML = '<div class="empty-state"><p>No funds match your filters.</p></div>';
        return;
    }

    const offset = pageData ? (pageData.page - 1) * pageData.per_page : 0;
    const fees = funds.map(f => f.fee).filter(f => f != null);
    const avgFee = fees.length ? fees.reduce((a, b) => a + b, 0) / fees.length : 0;

    let html = '<div class="il-table"><div class="il-table-header">';
    html += '<span class="il-col-rank">#</span>';
    html += '<span class="il-col-name">Fund</span>';
    html += '<span class="il-col-cat">Category</span>';
    html += '<span class="il-col-fee">Fee %</span>';
    html += '<span class="il-col-fee">Entry %</span>';
    html += '<span class="il-col-ret">Annual</span>';
    html += '<span class="il-col-ret">YTD</span>';
    html += '<span class="il-col-size">Size (₪M)</span>';
    html += '<span class="il-col-save">Cost /₪100K</span>';
    html += '</div>';

    funds.forEach((f, i) => {
        const feeClass = f.fee <= avgFee * 0.6 ? "il-fee-best" : f.fee >= avgFee * 1.4 ? "il-fee-worst" : "";
        const costPer100k = (f.fee / 100 * 100000).toFixed(0);
        const kosherTag = f.kosher ? ' <span class="il-kosher-tag">כשר</span>' : "";
        const annRet = f.annual_return != null ? f.annual_return.toFixed(2) + "%" : "—";
        const ytdRet = f.ytd_return != null ? f.ytd_return.toFixed(2) + "%" : "—";
        const entryFee = f.entry_fee ? f.entry_fee + "%" : "0";
        const catShort = f.category.length > 15 ? f.category.substring(0, 14) + "…" : f.category;

        html += `<div class="il-table-row" onclick="window.open('${f.funder_url}','_blank')">
            <span class="il-col-rank">${offset + i + 1}</span>
            <span class="il-col-name">
                <div class="il-fund-name">${f.name}${kosherTag}</div>
                <div class="il-fund-manager">${f.manager}</div>
            </span>
            <span class="il-col-cat"><span class="il-cat-badge">${catShort}</span></span>
            <span class="il-col-fee"><span class="il-fee-pill ${feeClass}">${f.fee}%</span></span>
            <span class="il-col-fee">${entryFee}</span>
            <span class="il-col-ret">${annRet}</span>
            <span class="il-col-ret">${ytdRet}</span>
            <span class="il-col-size">${fmtILS(f.size_m)}</span>
            <span class="il-col-save">₪${costPer100k}</span>
        </div>`;
    });

    html += '</div>';
    html += `<div class="il-footer-note">Data from <a href="https://www.funder.co.il" target="_blank" style="color:var(--primary)">funder.co.il</a> · Click any row to view on Funder</div>`;
    el.innerHTML = html;
}

function fmtILS(val) {
    if (!val) return "0";
    if (val >= 1000) return (val / 1000).toFixed(1) + "B";
    return val.toFixed(0);
}

function clearILFilters() {
    ["il-filter-type", "il-filter-manager", "il-filter-max-fee", "il-filter-min-return", "il-filter-min-size"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
    const sortEl = document.getElementById("il-filter-sort");
    if (sortEl) sortEl.value = "fee";
    const kosherEl = document.getElementById("il-filter-kosher");
    if (kosherEl) kosherEl.checked = false;
    loadBestDeals();
    runILSearch();
}

function applyILPreset(name) {
    clearILFilters();
    const typeEl = document.getElementById("il-filter-type");
    const sortEl = document.getElementById("il-filter-sort");
    const feeEl = document.getElementById("il-filter-max-fee");
    const kosherEl = document.getElementById("il-filter-kosher");

    if (name === "cheapest-kaspit") {
        if (typeEl) typeEl.value = "Kaspit (Money Market)";
        if (sortEl) sortEl.value = "fee";
    } else if (name === "best-return") {
        if (sortEl) sortEl.value = "annual_return";
    } else if (name === "index-funds") {
        if (typeEl) typeEl.value = "Index Tracking";
    } else if (name === "kosher") {
        if (kosherEl) kosherEl.checked = true;
    } else if (name === "low-fee") {
        if (feeEl) feeEl.value = "0.2";
    } else if (name === "big-funds") {
        if (sortEl) sortEl.value = "size_m";
    }
    loadBestDeals();
    runILSearch();
}
