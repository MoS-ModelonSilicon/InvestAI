/* AutoPilot – AI Smart Portfolios */

let apProfiles = [];
let apSelectedProfile = null;
let apAmount = 10000;
let apPeriod = "1y";
let apChart = null;

const RISK_COLORS = { High: "#ef4444", Medium: "#f59e0b", Low: "#22c55e" };
const RISK_ICONS = {
    High: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    Medium: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>',
    Low: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
};

async function loadAutopilot() {
    const container = document.getElementById("ap-profiles");
    try {
        apProfiles = await api.get("/api/autopilot/profiles");
        renderProfileCards();
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><p>Failed to load strategies.</p></div>';
    }
}

function renderProfileCards() {
    const container = document.getElementById("ap-profiles");
    if (!apProfiles.length) {
        container.innerHTML = '<div class="empty-state"><p>No strategies available.</p></div>';
        return;
    }

    container.innerHTML = apProfiles.map((p) => {
        const color = RISK_COLORS[p.risk_level] || "#8b5cf6";
        const icon = RISK_ICONS[p.risk_level] || "";
        const selected = apSelectedProfile === p.id;
        return `
        <div class="ap-card ${selected ? "ap-card-selected" : ""}" data-profile="${p.id}" onclick="selectProfile('${p.id}')" style="--accent:${color}">
            <div class="ap-card-header">
                <div class="ap-card-icon" style="color:${color}">${icon}</div>
                <div class="ap-card-risk" style="background:${color}20;color:${color}">${p.risk_level} Risk</div>
            </div>
            <h3 class="ap-card-name">${p.name}</h3>
            <div class="ap-card-subtitle">${p.subtitle}</div>
            <p class="ap-card-desc">${p.description}</p>
            <div class="ap-card-meta">
                <div><span class="ap-meta-label">Strategy</span><span class="ap-meta-value">${p.strategy}</span></div>
                <div><span class="ap-meta-label">Rebalance</span><span class="ap-meta-value">${p.rebalance}</span></div>
                <div><span class="ap-meta-label">Expected Return</span><span class="ap-meta-value" style="color:#22c55e">${p.expected_return}</span></div>
                <div><span class="ap-meta-label">Max Drawdown</span><span class="ap-meta-value" style="color:#ef4444">${p.expected_drawdown}</span></div>
            </div>
            <div class="ap-card-sleeves">
                ${p.sleeves.map((s) => `<div class="ap-sleeve-pill">${s.label} <strong>${s.pct}%</strong></div>`).join("")}
            </div>
            <button class="btn ${selected ? "btn-primary" : "btn-ghost"} ap-select-btn">${selected ? "Selected" : "Select Strategy"}</button>
        </div>`;
    }).join("");
}

function selectProfile(id) {
    apSelectedProfile = id;
    renderProfileCards();
    document.getElementById("ap-config").style.display = "";
    document.getElementById("ap-results").style.display = "none";
    document.getElementById("ap-error").style.display = "none";
}

function setApAmount(val) {
    apAmount = val;
    document.getElementById("ap-amount").value = val;
    document.querySelectorAll(".ap-presets .btn").forEach((b) => b.classList.remove("ap-preset-active"));
    document.querySelectorAll(".ap-presets .btn").forEach((b) => {
        if (parseInt(b.textContent.replace(/[$K,]/g, "")) * (b.textContent.includes("K") ? 1000 : 1) === val) {
            b.classList.add("ap-preset-active");
        }
    });
}

function setApPeriod(val) {
    apPeriod = val;
    document.querySelectorAll(".ap-period-row .btn").forEach((b) => b.classList.remove("ap-preset-active"));
    const active = document.querySelector(`.ap-period-row .btn[data-period="${val}"]`);
    if (active) active.classList.add("ap-preset-active");
}

async function runAutopilot() {
    if (!apSelectedProfile) return;

    const amountEl = document.getElementById("ap-amount");
    apAmount = parseFloat(amountEl.value) || 10000;

    const resultsEl = document.getElementById("ap-results");
    const errorEl = document.getElementById("ap-error");
    const runBtn = document.querySelector(".ap-run-btn");

    runBtn.disabled = true;
    runBtn.textContent = "Simulating...";
    resultsEl.style.display = "none";
    errorEl.style.display = "none";

    try {
        const data = await api.get(
            `/api/autopilot/simulate?profile=${apSelectedProfile}&amount=${apAmount}&period=${apPeriod}`
        );

        if (data.error) {
            errorEl.style.display = "";
            errorEl.innerHTML = `<p>${data.error}</p>`;
            return;
        }

        renderResults(data);
        resultsEl.style.display = "";
    } catch (e) {
        errorEl.style.display = "";
        errorEl.innerHTML = `<p>Simulation failed: ${e.message}</p>`;
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = "Run Simulation";
    }
}

function renderResults(data) {
    renderStats(data.stats);
    renderChart(data.chart, data.profile);
    renderSleeves(data.sleeves, data.cash);
    renderHoldings(data.holdings);
    renderMethodology(data.profile);
}

function renderStats(s) {
    const row = document.getElementById("ap-stats-row");
    const returnColor = s.total_return_pct >= 0 ? "var(--green)" : "var(--red)";
    const alphaColor = s.alpha >= 0 ? "var(--green)" : "var(--red)";

    row.innerHTML = `
        <div class="ap-stat">
            <div class="ap-stat-label">Total Return</div>
            <div class="ap-stat-value" style="color:${returnColor}">${s.total_return_pct >= 0 ? "+" : ""}${s.total_return_pct.toFixed(2)}%</div>
            <div class="ap-stat-sub">${fmt(s.total_return)}</div>
        </div>
        <div class="ap-stat">
            <div class="ap-stat-label">Alpha vs S&P</div>
            <div class="ap-stat-value" style="color:${alphaColor}">${s.alpha >= 0 ? "+" : ""}${s.alpha.toFixed(2)}%</div>
            <div class="ap-stat-sub">Bench: ${s.bench_return_pct >= 0 ? "+" : ""}${s.bench_return_pct.toFixed(2)}%</div>
        </div>
        <div class="ap-stat">
            <div class="ap-stat-label">Sharpe Ratio</div>
            <div class="ap-stat-value">${s.sharpe_ratio.toFixed(2)}</div>
            <div class="ap-stat-sub">${s.sharpe_ratio >= 1 ? "Good" : s.sharpe_ratio >= 0.5 ? "Fair" : "Low"}</div>
        </div>
        <div class="ap-stat">
            <div class="ap-stat-label">Max Drawdown</div>
            <div class="ap-stat-value" style="color:var(--red)">-${s.max_drawdown.toFixed(2)}%</div>
            <div class="ap-stat-sub">Worst peak-to-trough</div>
        </div>
        <div class="ap-stat">
            <div class="ap-stat-label">Win Rate</div>
            <div class="ap-stat-value">${s.win_rate.toFixed(1)}%</div>
            <div class="ap-stat-sub">${s.trading_days} trading days</div>
        </div>
        <div class="ap-stat">
            <div class="ap-stat-label">Final Value</div>
            <div class="ap-stat-value" style="color:${returnColor}">${fmt(s.final_value)}</div>
            <div class="ap-stat-sub">from ${fmt(s.starting_amount)}</div>
        </div>
    `;
}

function renderChart(chart, profile) {
    const ctx = document.getElementById("ap-chart").getContext("2d");
    if (apChart) apChart.destroy();

    const color = RISK_COLORS[profile.risk_level] || "#8b5cf6";
    const labels = chart.dates.map((d) => {
        const dt = new Date(d);
        return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    });

    apChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Portfolio",
                    data: chart.portfolio,
                    borderColor: color,
                    backgroundColor: color + "18",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    borderWidth: 2.5,
                },
                {
                    label: "S&P 500",
                    data: chart.benchmark,
                    borderColor: "#64748b",
                    backgroundColor: "transparent",
                    borderDash: [6, 3],
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    borderWidth: 1.5,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: "rgba(255,255,255,0.04)" },
                    ticks: { color: "#94a3b8", maxTicksLimit: 12, font: { size: 11 } },
                },
                y: {
                    grid: { color: "rgba(255,255,255,0.04)" },
                    ticks: {
                        color: "#94a3b8",
                        font: { size: 11 },
                        callback: (v) => "$" + v.toLocaleString(),
                    },
                },
            },
        },
    });
}

function renderSleeves(sleeves, cash) {
    const el = document.getElementById("ap-sleeves");
    let html = sleeves.map((s) => {
        const gl = s.gain_loss;
        const glColor = gl >= 0 ? "var(--green)" : "var(--red)";
        return `
        <div class="ap-sleeve-row">
            <div class="ap-sleeve-info">
                <span class="ap-sleeve-label">${s.label}</span>
                <span class="ap-sleeve-pct">${s.pct.toFixed(1)}%</span>
            </div>
            <div class="ap-sleeve-bar-track">
                <div class="ap-sleeve-bar" style="width:${Math.min(s.pct, 100)}%"></div>
            </div>
            <div class="ap-sleeve-values">
                <span>${fmt(s.current_value)}</span>
                <span style="color:${glColor}">${gl >= 0 ? "+" : ""}${fmt(gl)}</span>
            </div>
        </div>`;
    }).join("");

    if (cash > 0) {
        html += `
        <div class="ap-sleeve-row">
            <div class="ap-sleeve-info"><span class="ap-sleeve-label">Cash</span><span class="ap-sleeve-pct">—</span></div>
            <div class="ap-sleeve-bar-track"><div class="ap-sleeve-bar ap-sleeve-bar-cash" style="width:3%"></div></div>
            <div class="ap-sleeve-values"><span>${fmt(cash)}</span><span style="color:var(--text-muted)">—</span></div>
        </div>`;
    }

    el.innerHTML = html;
}

function renderHoldings(holdings) {
    const body = document.getElementById("ap-holdings-body");
    const count = document.getElementById("ap-holdings-count");
    count.textContent = `${holdings.length} holdings`;

    body.innerHTML = holdings.map((h) => {
        const glColor = h.gain_loss >= 0 ? "var(--green)" : "var(--red)";
        return `<tr>
            <td><a href="#" onclick="navigateTo('stock-detail');loadStockDetail('${h.symbol}');return false;" class="stock-link">${h.symbol}</a></td>
            <td class="text-muted">${h.sleeve}</td>
            <td class="text-right">${h.shares.toFixed(2)}</td>
            <td class="text-right">${fmt(h.buy_price)}</td>
            <td class="text-right">${fmt(h.current_price)}</td>
            <td class="text-right" style="color:${glColor}">${h.gain_loss >= 0 ? "+" : ""}${fmt(h.gain_loss)}</td>
            <td class="text-right" style="color:${glColor}">${h.gain_loss_pct >= 0 ? "+" : ""}${h.gain_loss_pct.toFixed(2)}%</td>
        </tr>`;
    }).join("");
}

function renderMethodology(profile) {
    const p = apProfiles.find((x) => x.id === profile.id);
    if (!p) return;
    const el = document.getElementById("ap-meth-content");
    el.innerHTML = `
        <div class="ap-meth-section">
            <h4>${p.name} — ${p.strategy}</h4>
            <p>${p.description}</p>
            <div class="ap-meth-grid">
                ${p.sleeves.map((s) => `
                    <div class="ap-meth-item">
                        <strong>${s.label} (${s.pct}%)</strong>
                        <span>${s.symbols.length ? s.symbols.join(", ") : "Uninvested cash reserve"}</span>
                    </div>
                `).join("")}
            </div>
            <p class="ap-meth-note">Rebalancing: ${p.rebalance}. Expected annual return: ${p.expected_return}. Historical max drawdown: ${p.expected_drawdown}. Past performance does not guarantee future results.</p>
        </div>
    `;
}

function toggleApMethodology() {
    const content = document.getElementById("ap-meth-content");
    const arrow = document.getElementById("ap-meth-arrow");
    const visible = content.style.display !== "none";
    content.style.display = visible ? "none" : "";
    arrow.style.transform = visible ? "" : "rotate(180deg)";
}
