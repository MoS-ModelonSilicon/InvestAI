let categories = [];

document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        navigateTo(link.dataset.page);
    });
});

function navigateTo(page) {
    document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"));
    const active = document.querySelector(`.nav-link[data-page="${page}"]`);
    if (active) active.classList.add("active");

    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    const pageEl = document.getElementById("page-" + page);
    if (pageEl) pageEl.classList.add("active");

    if (page === "dashboard") { loadDashboard(); startMarketRefresh(); }
    else { stopMarketRefresh(); }

    if (page === "transactions") loadTransactions();
    if (page === "budgets") loadBudgets();
    if (page === "profile") loadProfile();
    if (page === "screener") initScreener();
    if (page === "recommendations") loadRecommendations();
    if (page === "watchlist") loadWatchlist();
    if (page === "stock-detail") loadStockDetail();
    if (page === "portfolio") loadPortfolio();
    if (page === "news") loadNews();
    if (page === "comparison") loadComparison();
    if (page === "alerts") loadAlerts();
    if (page === "education") loadEducation();
    if (page === "calendar") loadCalendar();
    if (page === "il-funds") loadILFunds();
}

async function loadCategories() {
    categories = await api.get("/api/categories");
    populateCategoryFilters();
}

function populateCategoryFilters() {
    const filterCat = document.getElementById("filter-category");
    if (!filterCat) return;
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

(async function init() {
    const today = new Date();
    const sixMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 5, 1);
    const dashFrom = document.getElementById("dash-from");
    const dashTo = document.getElementById("dash-to");
    if (dashFrom) dashFrom.value = `${sixMonthsAgo.getFullYear()}-${String(sixMonthsAgo.getMonth() + 1).padStart(2, "0")}`;
    if (dashTo) dashTo.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

    startMarketRefresh();

    try { await loadCategories(); } catch (e) { console.warn("loadCategories failed:", e); }
    try { await loadDashboard(); } catch (e) { console.warn("loadDashboard failed:", e); }

    if (typeof startAlertPolling === "function") startAlertPolling();
})();
