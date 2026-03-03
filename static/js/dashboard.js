let trendChart = null;
let catChart = null;

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
                { label: "Income", data: trend.map((t) => t.income), backgroundColor: "rgba(34,197,94,0.7)", borderRadius: 6 },
                { label: "Expenses", data: trend.map((t) => t.expenses), backgroundColor: "rgba(239,68,68,0.7)", borderRadius: 6 },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: "#8b8fa3", usePointStyle: true, pointStyle: "circle" } } },
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
            datasets: [{ data: breakdown.map((b) => b.total), backgroundColor: breakdown.map((b) => b.color), borderWidth: 0 }],
        },
        options: {
            responsive: true, cutout: "65%",
            plugins: { legend: { position: "bottom", labels: { color: "#8b8fa3", usePointStyle: true, pointStyle: "circle", padding: 16 } } },
        },
    });
}

function renderBudgetBars(budgets) {
    const container = document.getElementById("budget-bars");
    if (budgets.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:0.9rem;">No budgets set yet.</p>';
        return;
    }
    container.innerHTML = budgets.map((b) => {
        const pct = Math.min(b.percentage, 100);
        const color = b.percentage > 90 ? "var(--red)" : b.percentage > 70 ? "#eab308" : b.color;
        return `<div class="budget-bar-row">
            <div class="budget-bar-label">${b.category_name}</div>
            <div class="budget-bar-track"><div class="budget-bar-fill" style="width:${pct}%;background:${color};"></div></div>
            <div class="budget-bar-text">${fmt(b.spent)} / ${fmt(b.monthly_limit)}</div>
        </div>`;
    }).join("");
}
