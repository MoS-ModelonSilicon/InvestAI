/* ── DCA Planner Page ──────────────────────────────────────── */

let _dcaData = null;
let _wizardStep = 0;
let _wizardState = {};
let _presets = [];

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
    const execStats = data.execution_stats || [];
    const rebalance = data.rebalance_suggestions || [];

    // Build plan_id → exec stats lookup
    const statsMap = {};
    execStats.forEach(s => { statsMap[s.plan_id] = s; });

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

    /* ── Rebalance Suggestions ────────────────────── */
    if (rebalance.length > 0) {
        html += `<div class="dca-section dca-rebalance-section">
            <h3>⚖️ Rebalance Suggestions</h3>
            <div class="dca-suggestions">`;
        rebalance.forEach(r => {
            html += `<div class="dca-suggestion">${r.message}</div>`;
        });
        html += `</div></div>`;
    }

    /* ── Actionable Monthly Cards ─────────────────── */
    if (alloc.allocations && alloc.allocations.length > 0) {
        html += `<div class="dca-section">
            <h3>📅 This Month's Actions — ${alloc.month || ''}</h3>`;

        if (alloc.suggestions && alloc.suggestions.length > 0) {
            html += `<div class="dca-suggestions">`;
            alloc.suggestions.forEach(s => {
                html += `<div class="dca-suggestion">${s}</div>`;
            });
            html += `</div>`;
        }

        html += `<div class="dca-action-cards">`;
        alloc.allocations.forEach(a => {
            const dipCls = a.dip_detected ? "dca-action-dip" : "";
            const multiplierBadge = a.multiplier_applied > 1
                ? `<span class="dca-badge-dip">${a.multiplier_applied}× DIP BUY</span>`
                : '<span class="dca-badge-normal">Regular</span>';

            html += `
            <div class="dca-action-card ${dipCls}">
                <div class="dca-action-top">
                    <div>
                        <span class="dca-action-symbol" onclick="navigateToStock('${a.symbol}')">${a.symbol}</span>
                        <span class="dca-action-name text-muted">${a.name}</span>
                    </div>
                    ${multiplierBadge}
                </div>
                <div class="dca-action-details">
                    <div class="dca-action-amount">
                        <span class="dca-action-label">Invest</span>
                        <span class="dca-action-value ${a.dip_detected ? 'stock-down' : ''}">${fmt(a.recommended_amount)}</span>
                    </div>
                    <div class="dca-action-shares">
                        <span class="dca-action-label">Shares</span>
                        <span class="dca-action-value">${a.shares_to_buy ? a.shares_to_buy.toFixed(2) : '—'}</span>
                    </div>
                    <div class="dca-action-price">
                        <span class="dca-action-label">Price</span>
                        <span class="dca-action-value">${a.current_price ? fmt(a.current_price) : '—'}</span>
                    </div>
                </div>
                ${a.dip_detected ? `<div class="dca-action-dip-info">🔻 ${a.dip_pct.toFixed(1)}% below avg cost</div>` : ''}
                <div class="dca-action-reason text-muted">${a.reason}</div>
                <div class="dca-action-buttons">
                    <button class="btn btn-sm btn-primary" onclick="markBought('${a.symbol}', ${a.recommended_amount}, ${a.shares_to_buy || 0}, ${a.current_price || 0}, ${a.dip_detected})">✅ Mark as Bought</button>
                    <button class="btn btn-sm btn-ghost" onclick="logCustomAmount('${a.symbol}', ${a.current_price || 0}, ${a.dip_detected})">📝 Custom</button>
                    <button class="btn btn-sm btn-ghost" onclick="skipMonth('${a.symbol}')">⏭ Skip</button>
                </div>
            </div>`;
        });
        html += `</div></div>`;
    }

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

    /* ── Plans List ───────────────────────────────── */
    html += `<div class="dca-section">
        <div class="dca-section-header">
            <h3>📋 DCA Plans</h3>
            <div style="display:flex;gap:8px;">
                <button class="btn btn-sm btn-ghost" onclick="loadBudgetSuggestions()">💡 Budget Tips</button>
                <button class="btn btn-sm btn-ghost" onclick="showExecutionHistory()">📊 History</button>
            </div>
        </div>
        <div id="dca-budget-tips"></div>
        <div id="dca-exec-history"></div>`;

    if (plans.length === 0) {
        html += `<div class="empty-state"><p>No DCA plans yet. Click <b>+ New DCA Plan</b> to start the guided setup wizard.</p></div>`;
    } else {
        html += `<div class="dca-plans-grid">`;
        plans.forEach(p => {
            const activeCls = p.active ? "" : "dca-plan-inactive";
            const stats = statsMap[p.id];
            const streakHtml = stats && stats.streak > 0
                ? `<span class="dca-badge-streak">🔥 ${stats.streak} month streak</span>`
                : '';

            html += `
            <div class="dca-plan-card ${activeCls}">
                <div class="dca-plan-top">
                    <span class="dca-plan-symbol" onclick="navigateToStock('${p.symbol}')">${p.symbol}</span>
                    <span class="dca-plan-name">${p.name || ''}</span>
                    <div class="dca-plan-badges">
                        ${p.is_long_term ? '<span class="dca-badge-lt">Long-term</span>' : ''}
                        ${!p.active ? '<span class="dca-badge-paused">Paused</span>' : ''}
                        ${streakHtml}
                    </div>
                </div>
                <div class="dca-plan-details">
                    <div><span class="text-muted">Monthly:</span> <b>${fmt(p.monthly_budget)}</b></div>
                    <div><span class="text-muted">Dip Trigger:</span> <b>${p.dip_threshold}%</b></div>
                    <div><span class="text-muted">Dip Multiplier:</span> <b>${p.dip_multiplier}×</b></div>
                </div>
                ${stats ? `<div class="dca-plan-exec-stats">
                    <span class="text-muted">Invested: <b>${fmt(stats.total_invested)}</b></span>
                    <span class="text-muted">Shares: <b>${stats.total_shares.toFixed(2)}</b></span>
                    <span class="text-muted">Buys: <b>${stats.buy_count}</b></span>
                    ${stats.dip_buy_count > 0 ? `<span class="text-muted">Dip Buys: <b>${stats.dip_buy_count}</b></span>` : ''}
                </div>` : ''}
                ${p.notes ? `<div class="dca-plan-notes text-muted">${p.notes}</div>` : ''}
                <div class="dca-plan-actions">
                    <button class="btn btn-sm btn-ghost" onclick="openBacktest('${p.symbol}', ${p.monthly_budget}, ${p.dip_threshold}, ${p.dip_multiplier})">📈 Backtest</button>
                    <button class="btn btn-sm ${p.active ? 'btn-ghost' : 'btn-primary'}" onclick="toggleDcaPlan(${p.id}, ${!p.active})">${p.active ? '⏸ Pause' : '▶ Activate'}</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDcaPlan(${p.id}, '${p.symbol}')">🗑</button>
                </div>
            </div>`;
        });
        html += `</div>`;
    }
    html += `</div>`;

    /* ── Backtest Results Container ───────────────── */
    html += `<div id="dca-backtest-container"></div>`;

    container.innerHTML = html;
}

/* ── Wizard Modal ─────────────────────────────────────────── */

async function openDcaModal(symbol, name) {
    _wizardStep = 1;
    _wizardState = { symbol: symbol || "", name: name || "" };

    // Pre-fetch presets
    if (_presets.length === 0) {
        try {
            const data = await api.get("/api/dca/wizard/presets");
            _presets = data.presets || [];
        } catch (e) {
            _presets = [
                { key: "conservative", label: "🛡️ Conservative", dip_threshold: -10, dip_multiplier: 1.5, description: "Buy 1.5× on 10%+ dip" },
                { key: "balanced", label: "⚖️ Balanced", dip_threshold: -15, dip_multiplier: 2.0, description: "Double down on 15%+ dip" },
                { key: "aggressive", label: "🔥 Aggressive", dip_threshold: -25, dip_multiplier: 3.0, description: "Triple down on 25%+ dip" },
            ];
        }
    }

    renderWizardStep();
    document.getElementById("dca-modal-overlay").classList.add("open");
}

function closeDcaModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("dca-modal-overlay").classList.remove("open");
    _wizardStep = 0;
}

function renderWizardStep() {
    const modalContent = document.querySelector("#dca-modal-overlay .modal");
    if (!modalContent) return;

    const steps = [
        { num: 1, label: "Pick Stock" },
        { num: 2, label: "Set Budget" },
        { num: 3, label: "Strategy" },
        { num: 4, label: "Preview" },
        { num: 5, label: "Confirm" },
    ];

    const progressHtml = `<div class="dca-wizard-progress">
        ${steps.map(s => `<div class="dca-wizard-step ${s.num < _wizardStep ? 'completed' : ''} ${s.num === _wizardStep ? 'active' : ''}">${s.num < _wizardStep ? '✓' : s.num}</div>`).join('<div class="dca-wizard-line"></div>')}
    </div>
    <div class="dca-wizard-labels">
        ${steps.map(s => `<span class="${s.num === _wizardStep ? 'active' : ''}">${s.label}</span>`).join('')}
    </div>`;

    let bodyHtml = "";

    if (_wizardStep === 1) {
        bodyHtml = `
        <div class="dca-wizard-body">
            <h3>Pick a Stock</h3>
            <p class="text-muted">Search for the stock you want to DCA into</p>
            <div class="form-group">
                <input type="text" id="wizard-symbol" placeholder="e.g. AAPL, NVDA, SPY" value="${_wizardState.symbol || ''}" class="dca-wizard-input" onkeydown="if(event.key==='Enter'){event.preventDefault();wizardLookup();}">
                <button class="btn btn-primary btn-sm" onclick="wizardLookup()" style="margin-top:8px;">Look up</button>
            </div>
            <div id="wizard-preview"></div>
        </div>`;
    } else if (_wizardStep === 2) {
        const range = _wizardState.suggestedRange || [25, 500];
        bodyHtml = `
        <div class="dca-wizard-body">
            <h3>Set Monthly Budget</h3>
            <p class="text-muted">How much to invest in <b>${_wizardState.symbol}</b> each month?</p>
            <div class="dca-wizard-budget-info">
                <span>Suggested range: <b>${fmt(range[0])} — ${fmt(range[1])}</b>/mo</span>
            </div>
            <div class="form-group">
                <input type="range" id="wizard-budget-slider" min="${range[0]}" max="${Math.max(range[1] * 2, 1000)}" step="25" value="${_wizardState.budget || _wizardState.suggestedBudget || 200}" oninput="document.getElementById('wizard-budget-display').textContent=fmt(this.value);_wizardState.budget=parseFloat(this.value);">
                <div class="dca-wizard-budget-display" id="wizard-budget-display">${fmt(_wizardState.budget || _wizardState.suggestedBudget || 200)}</div>
            </div>
            <div class="form-group">
                <label>Or enter exact amount:</label>
                <input type="number" id="wizard-budget-exact" min="1" step="1" value="${_wizardState.budget || _wizardState.suggestedBudget || 200}" onchange="_wizardState.budget=parseFloat(this.value);document.getElementById('wizard-budget-slider').value=this.value;document.getElementById('wizard-budget-display').textContent=fmt(this.value);">
            </div>
        </div>`;
    } else if (_wizardStep === 3) {
        bodyHtml = `
        <div class="dca-wizard-body">
            <h3>Choose Dip Strategy</h3>
            <p class="text-muted">When <b>${_wizardState.symbol}</b> dips, how aggressively should you buy extra?</p>
            <div class="dca-preset-cards">
                ${_presets.map(p => `
                <div class="dca-preset-card ${_wizardState.preset === p.key ? 'selected' : ''}" onclick="selectPreset('${p.key}')">
                    <div class="dca-preset-label">${p.label}</div>
                    <div class="dca-preset-detail">Dip trigger: <b>${p.dip_threshold}%</b></div>
                    <div class="dca-preset-detail">Multiplier: <b>${p.dip_multiplier}×</b></div>
                    <div class="dca-preset-desc">${p.description}</div>
                </div>`).join('')}
            </div>
            <div class="dca-preset-custom" style="margin-top:14px;">
                <label><input type="checkbox" id="wizard-custom-toggle" ${_wizardState.customStrategy ? 'checked' : ''} onchange="toggleCustomStrategy(this.checked)"> Custom values</label>
                <div id="wizard-custom-fields" style="display:${_wizardState.customStrategy ? 'flex' : 'none'};gap:12px;margin-top:8px;">
                    <div class="form-group"><label>Dip Threshold (%)</label><input type="number" id="wizard-custom-threshold" step="1" max="0" value="${_wizardState.dipThreshold || -15}"></div>
                    <div class="form-group"><label>Multiplier (×)</label><input type="number" id="wizard-custom-multiplier" step="0.5" min="1" value="${_wizardState.dipMultiplier || 2}"></div>
                </div>
            </div>
        </div>`;
    } else if (_wizardStep === 4) {
        bodyHtml = `
        <div class="dca-wizard-body">
            <h3>📈 Backtest Preview</h3>
            <p class="text-muted">See how this strategy would have performed historically</p>
            <div id="wizard-backtest" class="dca-wizard-backtest">
                <div class="loading-spinner"><div class="spinner" style="width:24px;height:24px;border-width:2px"></div> Running backtest...</div>
            </div>
        </div>`;
        // Fire backtest
        setTimeout(() => runWizardBacktest(), 100);
    } else if (_wizardStep === 5) {
        const preset = _presets.find(p => p.key === _wizardState.preset);
        const threshold = _wizardState.customStrategy ? _wizardState.dipThreshold : (preset?.dip_threshold ?? -15);
        const multiplier = _wizardState.customStrategy ? _wizardState.dipMultiplier : (preset?.dip_multiplier ?? 2);
        bodyHtml = `
        <div class="dca-wizard-body">
            <h3>✅ Confirm Your Plan</h3>
            <div class="dca-wizard-summary">
                <div class="dca-summary-row"><span class="text-muted">Stock</span><b>${_wizardState.symbol}</b> <span class="text-muted">${_wizardState.name}</span></div>
                <div class="dca-summary-row"><span class="text-muted">Monthly Budget</span><b>${fmt(_wizardState.budget || 200)}</b></div>
                <div class="dca-summary-row"><span class="text-muted">Strategy</span><b>${preset ? preset.label : 'Custom'}</b></div>
                <div class="dca-summary-row"><span class="text-muted">Dip Trigger</span><b>${threshold}%</b></div>
                <div class="dca-summary-row"><span class="text-muted">Dip Multiplier</span><b>${multiplier}×</b></div>
                <div class="dca-summary-row"><span class="text-muted">Next Buy Date</span><b>${_dcaData?.next_buy_date || 'Next 1st'}</b></div>
            </div>
            <div class="form-group" style="margin-top:12px;">
                <label>Notes (optional)</label>
                <input type="text" id="wizard-notes" placeholder="Long-term hold, buying dips..." value="${_wizardState.notes || ''}">
            </div>
            <div class="form-group">
                <label><input type="checkbox" id="wizard-long-term" checked style="margin-right:6px;">Long-term investment</label>
            </div>
        </div>`;
    }

    const isFirst = _wizardStep === 1;
    const isLast = _wizardStep === 5;

    modalContent.innerHTML = `
        <div class="modal-header"><h2>New DCA Plan</h2><button class="modal-close" onclick="closeDcaModal()">&times;</button></div>
        ${progressHtml}
        ${bodyHtml}
        <div class="dca-wizard-nav">
            ${!isFirst ? '<button class="btn btn-ghost" onclick="wizardBack()">← Back</button>' : '<span></span>'}
            ${isLast
                ? '<button class="btn btn-primary" onclick="wizardSubmit()">🚀 Create Plan</button>'
                : '<button class="btn btn-primary" onclick="wizardNext()">Next →</button>'}
        </div>`;
}

async function wizardLookup() {
    const sym = (document.getElementById("wizard-symbol")?.value || "").toUpperCase().trim();
    if (!sym) return;
    const preview = document.getElementById("wizard-preview");
    preview.innerHTML = '<div class="loading-spinner" style="padding:8px"><div class="spinner" style="width:20px;height:20px;border-width:2px"></div></div>';

    try {
        const data = await api.get(`/api/dca/wizard/preview?symbol=${encodeURIComponent(sym)}`);
        if (data.error) {
            preview.innerHTML = `<p style="color:var(--red)">${data.error}</p>`;
            return;
        }
        _wizardState.symbol = data.symbol;
        _wizardState.name = data.name;
        _wizardState.suggestedBudget = data.suggested_budget;
        _wizardState.suggestedRange = data.suggested_budget_range;

        preview.innerHTML = `
        <div class="dca-wizard-stock-preview">
            <div class="dca-wizard-stock-header">
                <b>${data.symbol}</b> <span class="text-muted">${data.name}</span>
            </div>
            <div class="dca-wizard-stock-stats">
                <span>Price: <b>${fmt(data.price)}</b></span>
                ${data.pct_from_high != null ? `<span>From 52w High: <b class="${data.pct_from_high < 0 ? 'stock-down' : 'stock-up'}">${data.pct_from_high.toFixed(1)}%</b></span>` : ''}
                ${data.sector ? `<span>Sector: <b>${data.sector}</b></span>` : ''}
                ${data.pe_ratio ? `<span>P/E: <b>${data.pe_ratio.toFixed(1)}</b></span>` : ''}
            </div>
        </div>`;
    } catch (e) {
        preview.innerHTML = `<p style="color:var(--red)">Failed to look up ${sym}</p>`;
    }
}

function selectPreset(key) {
    _wizardState.preset = key;
    _wizardState.customStrategy = false;
    const preset = _presets.find(p => p.key === key);
    if (preset) {
        _wizardState.dipThreshold = preset.dip_threshold;
        _wizardState.dipMultiplier = preset.dip_multiplier;
    }
    renderWizardStep();
}

function toggleCustomStrategy(checked) {
    _wizardState.customStrategy = checked;
    const fields = document.getElementById("wizard-custom-fields");
    if (fields) fields.style.display = checked ? "flex" : "none";
}

function wizardBack() {
    saveCurrentStepData();
    _wizardStep = Math.max(1, _wizardStep - 1);
    renderWizardStep();
}

function wizardNext() {
    saveCurrentStepData();

    // Validate current step
    if (_wizardStep === 1) {
        if (!_wizardState.symbol) {
            if (typeof showToast === "function") showToast("Please look up a stock first", "error");
            return;
        }
    } else if (_wizardStep === 2) {
        if (!_wizardState.budget || _wizardState.budget <= 0) {
            if (typeof showToast === "function") showToast("Please set a monthly budget", "error");
            return;
        }
    } else if (_wizardStep === 3) {
        if (!_wizardState.preset && !_wizardState.customStrategy) {
            if (typeof showToast === "function") showToast("Please select a dip strategy", "error");
            return;
        }
    }

    _wizardStep = Math.min(5, _wizardStep + 1);
    renderWizardStep();
}

function saveCurrentStepData() {
    if (_wizardStep === 1) {
        const sym = document.getElementById("wizard-symbol");
        if (sym) _wizardState.symbol = sym.value.toUpperCase().trim();
    } else if (_wizardStep === 2) {
        const exact = document.getElementById("wizard-budget-exact");
        if (exact) _wizardState.budget = parseFloat(exact.value) || 200;
    } else if (_wizardStep === 3) {
        if (_wizardState.customStrategy) {
            const th = document.getElementById("wizard-custom-threshold");
            const mult = document.getElementById("wizard-custom-multiplier");
            if (th) _wizardState.dipThreshold = parseFloat(th.value);
            if (mult) _wizardState.dipMultiplier = parseFloat(mult.value);
        }
    } else if (_wizardStep === 5) {
        const notes = document.getElementById("wizard-notes");
        if (notes) _wizardState.notes = notes.value.trim();
    }
}

async function runWizardBacktest() {
    const preset = _presets.find(p => p.key === _wizardState.preset);
    const threshold = _wizardState.customStrategy ? _wizardState.dipThreshold : (preset?.dip_threshold ?? -15);
    const multiplier = _wizardState.customStrategy ? _wizardState.dipMultiplier : (preset?.dip_multiplier ?? 2);
    const budget = _wizardState.budget || 200;

    const el = document.getElementById("wizard-backtest");
    try {
        const result = await api.get(`/api/dca/backtest?symbol=${_wizardState.symbol}&monthly=${budget}&dip_threshold=${threshold}&dip_multiplier=${multiplier}&months=24`);
        if (result.error) {
            el.innerHTML = `<p class="text-muted">${result.error}. You can still create the plan.</p>`;
            return;
        }
        el.innerHTML = renderBacktestResult(result, true);
    } catch (e) {
        el.innerHTML = `<p class="text-muted">Backtest unavailable. You can still create the plan.</p>`;
    }
}

async function wizardSubmit() {
    saveCurrentStepData();
    const preset = _presets.find(p => p.key === _wizardState.preset);
    const threshold = _wizardState.customStrategy ? _wizardState.dipThreshold : (preset?.dip_threshold ?? -15);
    const multiplier = _wizardState.customStrategy ? _wizardState.dipMultiplier : (preset?.dip_multiplier ?? 2);
    const longTerm = document.getElementById("wizard-long-term")?.checked ?? true;

    const payload = {
        symbol: _wizardState.symbol,
        name: _wizardState.name || "",
        monthly_budget: _wizardState.budget || 200,
        dip_threshold: threshold,
        dip_multiplier: multiplier,
        is_long_term: longTerm,
        notes: _wizardState.notes || "",
    };

    try {
        await api.post("/api/dca/plans", payload);
        closeDcaModal();
        if (typeof showToast === "function") showToast(`DCA plan for ${payload.symbol} created! 🎉`);
        loadDca();
    } catch (e) {
        alert("Failed to create DCA plan: " + (e.message || e));
    }
}

/* ── Backtest ─────────────────────────────────────────────── */

function renderBacktestResult(r, compact) {
    const advantage = r.dca_return_pct - r.plain_dca_return_pct;
    const advantageCls = advantage >= 0 ? "stock-up" : "stock-down";
    const prefix = compact ? "wiz" : "bt";

    let html = `<div class="dca-backtest-result ${compact ? 'compact' : ''}">
        <div class="dca-bt-header">
            <span><b>${r.symbol}</b> · ${r.months} months · ${fmt(r.monthly_budget)}/mo</span>
        </div>
        <div class="dca-bt-comparison">
            <div class="dca-bt-col dca-bt-smart">
                <div class="dca-bt-col-title">🧠 Smart DCA</div>
                <div class="dca-bt-stat"><span>Invested</span><b>${fmt(r.total_invested_dca)}</b></div>
                <div class="dca-bt-stat"><span>Value</span><b>${fmt(r.portfolio_value_dca)}</b></div>
                <div class="dca-bt-stat"><span>Return</span><b class="${r.dca_return_pct >= 0 ? 'stock-up' : 'stock-down'}">${r.dca_return_pct >= 0 ? '+' : ''}${r.dca_return_pct.toFixed(1)}%</b></div>
                <div class="dca-bt-stat"><span>Shares</span><b>${r.total_shares_dca.toFixed(2)}</b></div>
                <div class="dca-bt-stat"><span>Dip Buys</span><b>${r.dip_buys_count}</b></div>
            </div>
            <div class="dca-bt-vs">VS</div>
            <div class="dca-bt-col dca-bt-plain">
                <div class="dca-bt-col-title">📊 Plain DCA</div>
                <div class="dca-bt-stat"><span>Invested</span><b>${fmt(r.total_invested_plain)}</b></div>
                <div class="dca-bt-stat"><span>Value</span><b>${fmt(r.portfolio_value_plain)}</b></div>
                <div class="dca-bt-stat"><span>Return</span><b class="${r.plain_dca_return_pct >= 0 ? 'stock-up' : 'stock-down'}">${r.plain_dca_return_pct >= 0 ? '+' : ''}${r.plain_dca_return_pct.toFixed(1)}%</b></div>
                <div class="dca-bt-stat"><span>Shares</span><b>${r.total_shares_plain.toFixed(2)}</b></div>
            </div>
        </div>
        <div class="dca-bt-advantage ${advantageCls}">
            Smart DCA advantage: <b>${advantage >= 0 ? '+' : ''}${advantage.toFixed(1)}%</b> return
            · <b>${(r.total_shares_dca - r.total_shares_plain).toFixed(2)}</b> extra shares
        </div>
    </div>`;
    return html;
}

async function openBacktest(symbol, budget, threshold, multiplier) {
    const container = document.getElementById("dca-backtest-container");
    container.innerHTML = '<div class="dca-section"><div class="loading-spinner"><div class="spinner" style="width:24px;height:24px;border-width:2px"></div> Running backtest for ' + symbol + '...</div></div>';
    container.scrollIntoView({ behavior: "smooth" });

    try {
        const result = await api.get(`/api/dca/backtest?symbol=${symbol}&monthly=${budget}&dip_threshold=${threshold}&dip_multiplier=${multiplier}&months=24`);
        if (result.error) {
            container.innerHTML = `<div class="dca-section"><p style="color:var(--red)">${result.error}</p></div>`;
            return;
        }
        container.innerHTML = `<div class="dca-section">
            <div class="dca-section-header">
                <h3>📈 Backtest: ${symbol}</h3>
                <button class="btn btn-sm btn-ghost" onclick="document.getElementById('dca-backtest-container').innerHTML=''">✕ Close</button>
            </div>
            ${renderBacktestResult(result, false)}
        </div>`;
    } catch (e) {
        container.innerHTML = `<div class="dca-section"><p style="color:var(--red)">Backtest failed.</p></div>`;
    }
}

/* ── Execution Actions ────────────────────────────────────── */

async function markBought(symbol, amount, shares, price, wasDip) {
    const plans = _dcaData?.plans || [];
    const plan = plans.find(p => p.symbol === symbol && p.active);
    if (!plan) { alert("Plan not found"); return; }

    try {
        await api.post("/api/dca/executions", {
            plan_id: plan.id,
            amount_invested: amount,
            shares_bought: shares,
            price: price,
            was_dip_buy: wasDip,
            skipped: false,
        });
        if (typeof showToast === "function") showToast(`Logged ${fmt(amount)} buy for ${symbol} ✅`);
        loadDca();
    } catch (e) {
        alert("Failed to log execution: " + (e.message || e));
    }
}

async function logCustomAmount(symbol, currentPrice, wasDip) {
    const plans = _dcaData?.plans || [];
    const plan = plans.find(p => p.symbol === symbol && p.active);
    if (!plan) { alert("Plan not found"); return; }

    const amountStr = prompt(`Enter amount invested in ${symbol}:`, plan.monthly_budget);
    if (!amountStr) return;
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) { alert("Invalid amount"); return; }

    const shares = currentPrice > 0 ? amount / currentPrice : 0;

    try {
        await api.post("/api/dca/executions", {
            plan_id: plan.id,
            amount_invested: amount,
            shares_bought: Math.round(shares * 10000) / 10000,
            price: currentPrice,
            was_dip_buy: wasDip,
            skipped: false,
        });
        if (typeof showToast === "function") showToast(`Logged ${fmt(amount)} buy for ${symbol} ✅`);
        loadDca();
    } catch (e) {
        alert("Failed to log execution: " + (e.message || e));
    }
}

async function skipMonth(symbol) {
    const plans = _dcaData?.plans || [];
    const plan = plans.find(p => p.symbol === symbol && p.active);
    if (!plan) { alert("Plan not found"); return; }

    const reason = prompt(`Why skip ${symbol} this month? (optional)`);
    if (reason === null) return; // cancelled

    try {
        await api.post("/api/dca/executions", {
            plan_id: plan.id,
            amount_invested: 0,
            shares_bought: 0,
            price: 0,
            was_dip_buy: false,
            skipped: true,
            skip_reason: reason || "",
        });
        if (typeof showToast === "function") showToast(`Skipped ${symbol} this month ⏭`);
        loadDca();
    } catch (e) {
        alert("Failed to log skip: " + (e.message || e));
    }
}

/* ── Execution History ────────────────────────────────────── */

async function showExecutionHistory() {
    const el = document.getElementById("dca-exec-history");
    if (el.innerHTML.includes("dca-history-table")) {
        el.innerHTML = "";
        return;
    }

    el.innerHTML = '<div class="loading-spinner" style="padding:12px"><div class="spinner" style="width:20px;height:20px;border-width:2px"></div> Loading history...</div>';

    try {
        const data = await api.get("/api/dca/executions");
        const execs = data.executions || [];

        if (execs.length === 0) {
            el.innerHTML = '<div class="dca-suggestion" style="margin:12px 0;">No execution history yet. Mark buys or skips from the monthly action cards above.</div>';
            return;
        }

        // Get symbol names from plans
        const planSymbols = {};
        (_dcaData?.plans || []).forEach(p => { planSymbols[p.id] = p.symbol; });

        let html = `<div class="dca-history-table" style="margin:12px 0;">
            <div class="dca-alloc-header" style="grid-template-columns: 80px 80px 90px 80px 80px 80px 1fr;">
                <span>Date</span><span>Symbol</span><span>Amount</span><span>Shares</span><span>Price</span><span>Type</span><span>Note</span>
            </div>`;

        execs.slice(0, 20).forEach(ex => {
            const sym = planSymbols[ex.plan_id] || '?';
            const typeBadge = ex.skipped
                ? '<span class="dca-badge-paused">Skipped</span>'
                : ex.was_dip_buy
                    ? '<span class="dca-badge-dip">Dip Buy</span>'
                    : '<span class="dca-badge-normal">Regular</span>';

            html += `
            <div class="dca-alloc-row" style="grid-template-columns: 80px 80px 90px 80px 80px 80px 1fr;">
                <span class="text-muted">${ex.date}</span>
                <span class="dca-alloc-symbol">${sym}</span>
                <span>${ex.skipped ? '—' : fmt(ex.amount_invested)}</span>
                <span>${ex.skipped ? '—' : ex.shares_bought.toFixed(2)}</span>
                <span>${ex.skipped ? '—' : fmt(ex.price)}</span>
                <span>${typeBadge}</span>
                <span class="text-muted">${ex.skip_reason || ''}</span>
            </div>`;
        });

        if (execs.length > 20) {
            html += `<div class="text-muted" style="text-align:center;padding:8px;">Showing 20 of ${execs.length} entries</div>`;
        }

        html += `</div>`;
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = '<p style="color:var(--red);padding:8px;">Failed to load history.</p>';
    }
}

/* ── Existing Actions ─────────────────────────────────────── */

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
    if (el.innerHTML.includes("dca-budget-card")) {
        el.innerHTML = "";
        return;
    }

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
