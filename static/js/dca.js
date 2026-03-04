/* ── DCA Planner Page ──────────────────────────────────────── */

let _dcaData = null;

async function loadDca() {
    const container = document.getElementById("dca-container");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading DCA plans...</p></div>';

    try {
        _dcaData = await api.get("/api/dca/dashboard");
        renderDca(_dcaData);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load DCA planner.</p>';
    }
}

function renderDca(data) {
    const container = document.getElementById("dca-container");
    const alloc = data.monthly_allocation || {};
    const opps = data.opportunities || [];
    const plans = data.plans || [];

    let html = "";

    /* ── Top stats ────────────────────────────────── */
    html += `
    <div class="pf-stats">
        <div class="pf-stat-card">
            <div class="pf-stat-label">Monthly DCA Budget</div>
            <div class="pf-stat-value">${fmt(alloc.total_monthly_budget || 0)}</div>
        </div>
        <div class="pf-stat-card">
            <div class="pf-stat-label">This Month Recommended</div>
            <div class="pf-stat-value ${alloc.over_budget ? 'stock-down' : ''}">${fmt(alloc.total_recommended || 0)}</div>
        </div>
        <div class="pf-stat-card">
            <div class="pf-stat-label">Active Plans</div>
            <div class="pf-stat-value">${plans.filter(p => p.active).length}</div>
        </div>
        <div class="pf-stat-card">
            <div class="pf-stat-label">Next Buy Date</div>
            <div class="pf-stat-value" style="font-size:1.1rem">${data.next_buy_date || '—'}</div>
        </div>
    </div>`;

    /* ── Dip Opportunities ────────────────────────── */
    if (opps.length > 0) {
        html += `<div class="dca-section dca-opportunities">
            <h3>🔻 Dip Opportunities — Buy More Now</h3>
            <div class="dca-opp-grid">`;

        opps.forEach(o => {
            const urgCls = o.urgency === "high" ? "dca-urg-high" : o.urgency === "medium" ? "dca-urg-med" : "dca-urg-low";
            html += `
            <div class="dca-opp-card ${urgCls}">
                <div class="dca-opp-header">
                    <span class="dca-opp-symbol" onclick="navigateToStock('${o.symbol}')">${o.symbol}</span>
                    <span class="dca-opp-urgency">${o.urgency.toUpperCase()}</span>
                </div>
                <div class="dca-opp-name">${o.name}</div>
                <div class="dca-opp-prices">
                    <span>Avg Cost: <b>${fmt(o.avg_cost)}</b></span>
                    <span>Now: <b class="stock-down">${fmt(o.current_price)}</b></span>
                </div>
                <div class="dca-opp-drop stock-down">${o.drop_from_cost.toFixed(1)}% from cost${o.drop_from_high ? ` · ${o.drop_from_high.toFixed(1)}% from 52w high` : ''}</div>
                <div class="dca-opp-action">
                    <span>Recommend: <b>${fmt(o.recommended_buy)}</b> (${o.multiplier}×)</span>
                    <span class="text-muted">≈ ${o.shares_to_buy.toFixed(2)} shares</span>
                </div>
                <div class="dca-opp-reason">${o.reason}</div>
            </div>`;
        });
        html += `</div></div>`;
    }

    /* ── Monthly Allocation ───────────────────────── */
    if (alloc.allocations && alloc.allocations.length > 0) {
        html += `<div class="dca-section">
            <h3>📅 Monthly Allocation — ${alloc.month || ''}</h3>`;

        if (alloc.suggestions && alloc.suggestions.length > 0) {
            html += `<div class="dca-suggestions">`;
            alloc.suggestions.forEach(s => {
                html += `<div class="dca-suggestion">${s}</div>`;
            });
            html += `</div>`;
        }

        html += `<div class="dca-alloc-table">
            <div class="dca-alloc-header">
                <span>Symbol</span><span>Normal</span><span>Dip?</span><span>Multiplier</span><span>Recommended</span><span>Shares</span><span>Reason</span>
            </div>`;

        alloc.allocations.forEach(a => {
            const dipCls = a.dip_detected ? "dca-dip-yes" : "";
            html += `
            <div class="dca-alloc-row ${dipCls}">
                <span class="dca-alloc-symbol" onclick="navigateToStock('${a.symbol}')">${a.symbol}<br><small class="text-muted">${a.name}</small></span>
                <span>${fmt(a.normal_amount)}</span>
                <span>${a.dip_detected ? `<span class="dca-badge-dip">${a.dip_pct.toFixed(1)}%</span>` : '<span class="text-muted">—</span>'}</span>
                <span>${a.multiplier_applied > 1 ? `<b class="stock-down">${a.multiplier_applied}×</b>` : '1×'}</span>
                <span class="${a.dip_detected ? 'stock-down' : ''}">${fmt(a.recommended_amount)}</span>
                <span class="text-muted">${a.shares_to_buy ? a.shares_to_buy.toFixed(2) : '—'}</span>
                <span class="dca-alloc-reason text-muted">${a.reason}</span>
            </div>`;
        });

        html += `</div></div>`;
    }

    /* ── Plans List ───────────────────────────────── */
    html += `<div class="dca-section">
        <div class="dca-section-header">
            <h3>📋 DCA Plans</h3>
            <button class="btn btn-sm btn-ghost" onclick="loadBudgetSuggestions()">💡 Budget Tips</button>
        </div>
        <div id="dca-budget-tips"></div>`;

    if (plans.length === 0) {
        html += `<div class="empty-state"><p>No DCA plans yet. Click <b>+ New DCA Plan</b> to start investing regularly in stocks you believe in long-term.</p></div>`;
    } else {
        html += `<div class="dca-plans-grid">`;
        plans.forEach(p => {
            const activeCls = p.active ? "" : "dca-plan-inactive";
            html += `
            <div class="dca-plan-card ${activeCls}">
                <div class="dca-plan-top">
                    <span class="dca-plan-symbol" onclick="navigateToStock('${p.symbol}')">${p.symbol}</span>
                    <span class="dca-plan-name">${p.name || ''}</span>
                    <div class="dca-plan-badges">
                        ${p.is_long_term ? '<span class="dca-badge-lt">Long-term</span>' : ''}
                        ${!p.active ? '<span class="dca-badge-paused">Paused</span>' : ''}
                    </div>
                </div>
                <div class="dca-plan-details">
                    <div><span class="text-muted">Monthly:</span> <b>${fmt(p.monthly_budget)}</b></div>
                    <div><span class="text-muted">Dip Trigger:</span> <b>${p.dip_threshold}%</b></div>
                    <div><span class="text-muted">Dip Multiplier:</span> <b>${p.dip_multiplier}×</b></div>
                </div>
                ${p.notes ? `<div class="dca-plan-notes text-muted">${p.notes}</div>` : ''}
                <div class="dca-plan-actions">
                    <button class="btn btn-sm ${p.active ? 'btn-ghost' : 'btn-primary'}" onclick="toggleDcaPlan(${p.id}, ${!p.active})">${p.active ? '⏸ Pause' : '▶ Activate'}</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDcaPlan(${p.id}, '${p.symbol}')">🗑 Delete</button>
                </div>
            </div>`;
        });
        html += `</div>`;
    }
    html += `</div>`;

    container.innerHTML = html;
}

/* ── Modal ────────────────────────────────────────────────── */

function openDcaModal(symbol, name) {
    document.getElementById("dca-symbol").value = symbol || "";
    document.getElementById("dca-name").value = name || "";
    document.getElementById("dca-budget").value = "";
    document.getElementById("dca-threshold").value = "-15";
    document.getElementById("dca-multiplier").value = "2";
    document.getElementById("dca-notes").value = "";
    document.getElementById("dca-long-term").checked = true;
    document.getElementById("dca-modal-overlay").classList.add("open");
}

function closeDcaModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("dca-modal-overlay").classList.remove("open");
}

async function submitDcaPlan(e) {
    e.preventDefault();
    const payload = {
        symbol: document.getElementById("dca-symbol").value.toUpperCase().trim(),
        name: document.getElementById("dca-name").value.trim(),
        monthly_budget: parseFloat(document.getElementById("dca-budget").value),
        dip_threshold: parseFloat(document.getElementById("dca-threshold").value),
        dip_multiplier: parseFloat(document.getElementById("dca-multiplier").value),
        is_long_term: document.getElementById("dca-long-term").checked,
        notes: document.getElementById("dca-notes").value.trim(),
    };

    try {
        await api.post("/api/dca/plans", payload);
        closeDcaModal();
        if (typeof showToast === "function") showToast(`DCA plan for ${payload.symbol} created`);
        loadDca();
    } catch (e) {
        alert("Failed to create DCA plan: " + (e.message || e));
    }
}

/* ── Actions ──────────────────────────────────────────────── */

async function toggleDcaPlan(id, activate) {
    try {
        await api.put(`/api/dca/plans/${id}`, { active: activate });
        loadDca();
    } catch (e) {
        alert("Failed to update plan");
    }
}

async function deleteDcaPlan(id, symbol) {
    if (!confirm(`Delete DCA plan for ${symbol}?`)) return;
    try {
        await api.del(`/api/dca/plans/${id}`);
        if (typeof showToast === "function") showToast(`DCA plan for ${symbol} removed`);
        loadDca();
    } catch (e) {
        alert("Failed to delete plan");
    }
}

async function loadBudgetSuggestions() {
    const el = document.getElementById("dca-budget-tips");
    el.innerHTML = '<div class="loading-spinner" style="padding:12px"><div class="spinner" style="width:20px;height:20px;border-width:2px"></div> Analyzing your profile...</div>';

    try {
        const data = await api.get("/api/dca/budget-suggestion");
        let html = `<div class="dca-budget-card">
            <div class="dca-budget-header">
                <h4>💡 Investment Budget Recommendations</h4>
                <span class="text-muted">Based on your ${data.risk_profile || 'moderate'} risk profile</span>
            </div>
            <div class="dca-budget-stats">
                <div><span class="text-muted">Target Monthly:</span> <b>${fmt(data.monthly_budget)}</b></div>
                <div><span class="text-muted">Currently Allocated:</span> <b>${fmt(data.current_dca_allocated)}</b></div>
                <div><span class="text-muted">Remaining:</span> <b class="${data.remaining_budget > 0 ? 'stock-up' : ''}">${fmt(data.remaining_budget)}</b></div>
                <div><span class="text-muted">Portfolio Value:</span> <b>${fmt(data.portfolio_value)}</b></div>
            </div>
            <div class="dca-budget-alloc">
                <div class="dca-alloc-bar">
                    <div class="dca-alloc-seg dca-seg-stock" style="width:${data.suggested_stock_pct}%">${data.suggested_stock_pct}% Stocks</div>
                    <div class="dca-alloc-seg dca-seg-etf" style="width:${data.suggested_etf_pct}%">${data.suggested_etf_pct}% ETFs</div>
                    <div class="dca-alloc-seg dca-seg-cash" style="width:${data.suggested_cash_reserve_pct}%">${data.suggested_cash_reserve_pct}% Cash</div>
                </div>
            </div>
            <div class="dca-suggestions">`;

        (data.suggestions || []).forEach(s => {
            html += `<div class="dca-suggestion">${s}</div>`;
        });

        html += `</div></div>`;
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = '<p style="color:var(--red);padding:8px;">Failed to load suggestions.</p>';
    }
}
