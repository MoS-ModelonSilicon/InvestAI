async function loadBudgets() {
    const budgets = await api.get("/api/budgets");
    const grid = document.getElementById("budgets-grid");
    const empty = document.getElementById("budgets-empty");

    if (budgets.length === 0) { grid.innerHTML = ""; empty.style.display = "block"; return; }
    empty.style.display = "none";

    const now = new Date();
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    const monthEnd = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}`;
    const txs = await api.get(`/api/transactions?type=expense&date_from=${monthStart}&date_to=${monthEnd}&limit=1000`);

    grid.innerHTML = budgets.map((b) => {
        const spent = txs.filter((t) => t.category_id === b.category_id).reduce((s, t) => s + t.amount, 0);
        const pct = b.monthly_limit > 0 ? Math.round((spent / b.monthly_limit) * 100) : 0;
        const clampPct = Math.min(pct, 100);
        const color = pct > 90 ? "var(--red)" : pct > 70 ? "#eab308" : b.category.color;
        return `<div class="budget-card">
            <div class="budget-card-header">
                <div class="budget-card-title"><span class="category-dot" style="background:${b.category.color}"></span>${b.category.name}</div>
                <button class="action-btn delete" onclick="deleteBudget(${b.id})" title="Remove">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </div>
            <div class="budget-progress"><div class="budget-progress-fill" style="width:${clampPct}%;background:${color};"></div></div>
            <div class="budget-card-amounts"><span>${fmt(spent)} spent</span><span>${fmt(b.monthly_limit)} limit &middot; ${pct}%</span></div>
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
