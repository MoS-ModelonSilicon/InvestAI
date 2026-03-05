// ── State ────────────────────────────────────────────────────
let categories = [];
let trendChart = null;
let catChart = null;

// ── API helpers ──────────────────────────────────────────────
const api = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },
    async post(url, data) {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },
    async put(url, data) {
        const res = await fetch(url, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },
    async del(url) {
        const res = await fetch(url, { method: "DELETE" });
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    },
};

const fmt = (n) => "$" + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ── Navigation ───────────────────────────────────────────────
document.querySelectorAll(".nav-link[data-page]").forEach((link) => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"));
        link.classList.add("active");
        document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
        document.getElementById("page-" + page).classList.add("active");
        if (page === "dashboard") loadDashboard();
        if (page === "transactions") loadTransactions();
        if (page === "budgets") loadBudgets();
        if (page === "admin") loadAdminPanel();
    });
});

// ── Categories ───────────────────────────────────────────────
async function loadCategories() {
    categories = await api.get("/api/categories");
    populateCategoryFilters();
}

function populateCategoryFilters() {
    const filterCat = document.getElementById("filter-category");
    filterCat.innerHTML = '<option value="">All Categories</option>';
    categories.forEach((c) => {
        filterCat.innerHTML += `<option value="${c.id}">${c.name}</option>`;
    });
}

function filterCategoriesByType() {
    const type = document.getElementById("tx-type").value;
    const sel = document.getElementById("tx-category");
    const currentVal = sel.value;
    sel.innerHTML = "";
    const filtered = categories.filter((c) => c.type === type);
    filtered.forEach((c) => {
        sel.innerHTML += `<option value="${c.id}">${c.name}</option>`;
    });
    const stillExists = filtered.find((c) => String(c.id) === currentVal);
    if (stillExists) sel.value = currentVal;
}

// ── Dashboard ────────────────────────────────────────────────
async function loadDashboard() {
    const from = document.getElementById("dash-from").value;
    const to = document.getElementById("dash-to").value;

    let url = "/api/dashboard?";
    if (from) url += `date_from=${from}-01&`;
    if (to) {
        const [y, m] = to.split("-");
        const last = new Date(y, m, 0).getDate();
        url += `date_to=${to}-${last}&`;
    }

    const data = await api.get(url);

    document.getElementById("stat-income").textContent = fmt(data.total_income);
    document.getElementById("stat-expenses").textContent = fmt(data.total_expenses);

    const balEl = document.getElementById("stat-balance");
    balEl.textContent = (data.net_balance >= 0 ? "+" : "-") + fmt(data.net_balance);
    balEl.style.color = data.net_balance >= 0 ? "var(--green)" : "var(--red)";

    renderTrendChart(data.monthly_trend);
    renderCategoryChart(data.category_breakdown);
    renderBudgetBars(data.budget_status);
}

function renderTrendChart(trend) {
    const ctx = document.getElementById("chart-trend").getContext("2d");
    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: trend.map((t) => t.month),
            datasets: [
                {
                    label: "Income",
                    data: trend.map((t) => t.income),
                    backgroundColor: "rgba(34, 197, 94, 0.7)",
                    borderRadius: 6,
                },
                {
                    label: "Expenses",
                    data: trend.map((t) => t.expenses),
                    backgroundColor: "rgba(239, 68, 68, 0.7)",
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: "#8b8fa3", usePointStyle: true, pointStyle: "circle" } },
            },
            scales: {
                x: { ticks: { color: "#8b8fa3" }, grid: { color: "rgba(42,45,62,0.5)" } },
                y: { ticks: { color: "#8b8fa3", callback: (v) => "$" + v.toLocaleString() }, grid: { color: "rgba(42,45,62,0.5)" } },
            },
        },
    });
}

function renderCategoryChart(breakdown) {
    const ctx = document.getElementById("chart-categories").getContext("2d");
    if (catChart) catChart.destroy();

    if (breakdown.length === 0) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.fillStyle = "#8b8fa3";
        ctx.font = "14px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No expense data", ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }

    catChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: breakdown.map((b) => b.category_name),
            datasets: [{
                data: breakdown.map((b) => b.total),
                backgroundColor: breakdown.map((b) => b.color),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            cutout: "65%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#8b8fa3", usePointStyle: true, pointStyle: "circle", padding: 16 },
                },
            },
        },
    });
}

function renderBudgetBars(budgets) {
    const container = document.getElementById("budget-bars");
    if (budgets.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">No budgets set yet.</p>';
        return;
    }

    container.innerHTML = budgets.map((b) => {
        const pct = Math.min(b.percentage, 100);
        const color = b.percentage > 90 ? "var(--red)" : b.percentage > 70 ? "#eab308" : b.color;
        return `
            <div class="budget-bar-row">
                <div class="budget-bar-label">${b.category_name}</div>
                <div class="budget-bar-track">
                    <div class="budget-bar-fill" style="width: ${pct}%; background: ${color};"></div>
                </div>
                <div class="budget-bar-text">${fmt(b.spent)} / ${fmt(b.monthly_limit)}</div>
            </div>`;
    }).join("");
}

// ── Transactions ─────────────────────────────────────────────
async function loadTransactions() {
    const type = document.getElementById("filter-type").value;
    const catId = document.getElementById("filter-category").value;
    const from = document.getElementById("filter-from").value;
    const to = document.getElementById("filter-to").value;

    let url = "/api/transactions?limit=200";
    if (type) url += `&type=${type}`;
    if (catId) url += `&category_id=${catId}`;
    if (from) url += `&date_from=${from}`;
    if (to) url += `&date_to=${to}`;

    const txs = await api.get(url);
    const tbody = document.getElementById("tx-body");
    const empty = document.getElementById("tx-empty");

    if (txs.length === 0) {
        tbody.innerHTML = "";
        empty.style.display = "block";
        return;
    }

    empty.style.display = "none";
    tbody.innerHTML = txs.map((t) => `
        <tr>
            <td>${new Date(t.date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</td>
            <td>${t.description || "<em style='color:var(--text-muted)'>No description</em>"}</td>
            <td><span class="category-dot" style="background:${t.category.color}"></span>${t.category.name}</td>
            <td><span class="badge badge-${t.type}">${t.type}</span></td>
            <td class="text-right amount-${t.type}">${t.type === "income" ? "+" : "-"}${fmt(t.amount)}</td>
            <td class="text-right">
                <button class="action-btn" onclick="editTransaction(${t.id})" title="Edit">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="action-btn delete" onclick="deleteTransaction(${t.id})" title="Delete">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </td>
        </tr>
    `).join("");
}

function clearFilters() {
    document.getElementById("filter-type").value = "";
    document.getElementById("filter-category").value = "";
    document.getElementById("filter-from").value = "";
    document.getElementById("filter-to").value = "";
    loadTransactions();
}

// ── Transaction Modal ────────────────────────────────────────
function openTransactionModal(tx = null) {
    document.getElementById("modal-title").textContent = tx ? "Edit Transaction" : "Add Transaction";
    document.getElementById("tx-id").value = tx ? tx.id : "";
    document.getElementById("tx-type").value = tx ? tx.type : "expense";
    document.getElementById("tx-amount").value = tx ? tx.amount : "";
    document.getElementById("tx-date").value = tx ? tx.date : new Date().toISOString().split("T")[0];
    document.getElementById("tx-desc").value = tx ? tx.description : "";

    filterCategoriesByType();
    if (tx) document.getElementById("tx-category").value = tx.category_id;

    document.getElementById("modal-overlay").classList.add("open");
}

function closeModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("modal-overlay").classList.remove("open");
}

async function submitTransaction(e) {
    e.preventDefault();
    const id = document.getElementById("tx-id").value;
    const data = {
        type: document.getElementById("tx-type").value,
        amount: parseFloat(document.getElementById("tx-amount").value),
        category_id: parseInt(document.getElementById("tx-category").value),
        date: document.getElementById("tx-date").value,
        description: document.getElementById("tx-desc").value,
    };

    if (id) {
        await api.put(`/api/transactions/${id}`, data);
    } else {
        await api.post("/api/transactions", data);
    }

    closeModal();
    loadTransactions();
}

async function editTransaction(id) {
    const txs = await api.get(`/api/transactions?limit=1000`);
    const tx = txs.find((t) => t.id === id);
    if (tx) openTransactionModal(tx);
}

async function deleteTransaction(id) {
    if (!confirm("Delete this transaction?")) return;
    await api.del(`/api/transactions/${id}`);
    loadTransactions();
}

// ── Budgets ──────────────────────────────────────────────────
async function loadBudgets() {
    const budgets = await api.get("/api/budgets");
    const grid = document.getElementById("budgets-grid");
    const empty = document.getElementById("budgets-empty");

    if (budgets.length === 0) {
        grid.innerHTML = "";
        empty.style.display = "block";
        return;
    }

    empty.style.display = "none";
    const now = new Date();
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    const monthEnd = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}`;

    const txs = await api.get(`/api/transactions?type=expense&date_from=${monthStart}&date_to=${monthEnd}&limit=1000`);

    grid.innerHTML = budgets.map((b) => {
        const spent = txs.filter((t) => t.category_id === b.category_id).reduce((sum, t) => sum + t.amount, 0);
        const pct = b.monthly_limit > 0 ? Math.round((spent / b.monthly_limit) * 100) : 0;
        const clampPct = Math.min(pct, 100);
        const color = pct > 90 ? "var(--red)" : pct > 70 ? "#eab308" : b.category.color;

        return `
            <div class="budget-card">
                <div class="budget-card-header">
                    <div class="budget-card-title">
                        <span class="category-dot" style="background:${b.category.color}"></span>
                        ${b.category.name}
                    </div>
                    <button class="action-btn delete" onclick="deleteBudget(${b.id})" title="Remove budget">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
                <div class="budget-progress">
                    <div class="budget-progress-fill" style="width: ${clampPct}%; background: ${color};"></div>
                </div>
                <div class="budget-card-amounts">
                    <span>${fmt(spent)} spent</span>
                    <span>${fmt(b.monthly_limit)} limit &middot; ${pct}%</span>
                </div>
            </div>`;
    }).join("");
}

function openBudgetModal() {
    const sel = document.getElementById("budget-category");
    sel.innerHTML = "";
    categories.filter((c) => c.type === "expense").forEach((c) => {
        sel.innerHTML += `<option value="${c.id}">${c.name}</option>`;
    });
    document.getElementById("budget-limit").value = "";
    document.getElementById("budget-modal-overlay").classList.add("open");
}

function closeBudgetModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("budget-modal-overlay").classList.remove("open");
}

async function submitBudget(e) {
    e.preventDefault();
    await api.post("/api/budgets", {
        category_id: parseInt(document.getElementById("budget-category").value),
        monthly_limit: parseFloat(document.getElementById("budget-limit").value),
    });
    closeBudgetModal();
    loadBudgets();
}

async function deleteBudget(id) {
    if (!confirm("Remove this budget?")) return;
    await api.del(`/api/budgets/${id}`);
    loadBudgets();
}

// ── Init ─────────────────────────────────────────────────────
(async function init() {
    const today = new Date();
    const sixMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 5, 1);
    document.getElementById("dash-from").value = `${sixMonthsAgo.getFullYear()}-${String(sixMonthsAgo.getMonth() + 1).padStart(2, "0")}`;
    document.getElementById("dash-to").value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

    await loadCategories();
    await loadDashboard();
})();
