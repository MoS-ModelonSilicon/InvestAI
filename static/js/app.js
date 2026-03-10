// ── Theme Toggle ─────────────────────────────────────────────
(function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
})();
(function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
})();

let categories = [];

// Merged-page mapping: sub-pages → parent sidebar item
const PAGE_TO_NAV = {
    'value-scanner': 'screener',
    'trading-advisor': 'smart-advisor',
    'recommendations': 'autopilot',
};

// ── Mobile Navigation ────────────────────────────────────────
const mobileHamburger = document.getElementById('mobile-hamburger');
const sidebarOverlay = document.getElementById('sidebar-overlay');
const sidebar = document.getElementById('sidebar');
const mobileBottomNav = document.getElementById('mobile-bottom-nav');

function openMobileSidebar() {
    sidebar.classList.add('mobile-open');
    sidebarOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeMobileSidebar() {
    sidebar.classList.remove('mobile-open');
    sidebarOverlay.classList.remove('open');
    document.body.style.overflow = '';
}

if (mobileHamburger) {
    mobileHamburger.addEventListener('click', () => {
        if (sidebar.classList.contains('mobile-open')) {
            closeMobileSidebar();
        } else {
            openMobileSidebar();
        }
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeMobileSidebar);
}

// Bottom nav buttons
if (mobileBottomNav) {
    mobileBottomNav.querySelectorAll('.mob-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.dataset.page;
            if (page === 'more') {
                openMobileSidebar();
                return;
            }
            navigateTo(page);
            // Update bottom nav active state
            mobileBottomNav.querySelectorAll('.mob-nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

function updateMobileBottomNav(page) {
    if (!mobileBottomNav) return;
    const bottomPages = ['dashboard', 'portfolio', 'watchlist', 'smart-advisor'];
    const navPage = PAGE_TO_NAV[page] || page;
    mobileBottomNav.querySelectorAll('.mob-nav-btn').forEach(b => {
        b.classList.remove('active');
        if (b.dataset.page === navPage || (navPage === 'dashboard' && b.dataset.page === 'dashboard')) {
            b.classList.add('active');
        }
    });
    // If navigated to a page not in bottom nav, no button is highlighted
    // (user got there from sidebar "More")
}

document.querySelectorAll(".nav-link[data-page]").forEach((link) => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        navigateTo(link.dataset.page);
    });
});

function navigateTo(page, pushState = true) {
    // Close mobile sidebar when navigating
    closeMobileSidebar();

    // Track page visit for feature hint dots
    if (typeof window._trackPageVisit === "function") {
        window._trackPageVisit(page);
    }

    document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"));
    const navPage = PAGE_TO_NAV[page] || page;
    const active = document.querySelector(`.nav-link[data-page="${navPage}"]`);
    if (active) active.classList.add("active");

    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    const pageEl = document.getElementById("page-" + page);
    if (pageEl) pageEl.classList.add("active");

    // Update mobile bottom nav
    updateMobileBottomNav(page);

    if (pushState) {
        history.pushState({ page }, "", `#${page}`);
    }

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
    if (page === "autopilot") loadAutopilot();
    if (page === "value-scanner") loadValueScanner();
    if (page === "smart-advisor") loadSmartAdvisor();
    if (page === "trading-advisor") loadTradingAdvisor();
    if (page === "picks-tracker") loadPicksTracker();
    if (page === "dca") loadDca();
    if (page === "admin") loadAdminPanel();
    if (page === "heatmap") loadHeatmap();
    if (page === "dividends") loadDividends();
    if (page === "etf-analysis") loadEtfAnalysis();
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

// ── Browser back/forward button support ──────────────────────
window.addEventListener("popstate", (e) => {
    const page = (e.state && e.state.page) || location.hash.replace("#", "") || "dashboard";
    navigateTo(page, false);
});

(async function init() {
    const today = new Date();
    const sixMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 5, 1);
    const dashFrom = document.getElementById("dash-from");
    const dashTo = document.getElementById("dash-to");
    if (dashFrom) dashFrom.value = `${sixMonthsAgo.getFullYear()}-${String(sixMonthsAgo.getMonth() + 1).padStart(2, "0")}`;
    if (dashTo) dashTo.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

    // Restore page from URL hash or default to dashboard
    const initialPage = location.hash.replace("#", "") || "dashboard";
    history.replaceState({ page: initialPage }, "", `#${initialPage}`);
    if (initialPage !== "dashboard") {
        navigateTo(initialPage, false);
    }

    startMarketRefresh();

    try { await loadCategories(); } catch (e) { console.warn("loadCategories failed:", e); }
    try { await loadDashboard(); } catch (e) { console.warn("loadDashboard failed:", e); }

    if (typeof initWatchlistCache === "function") initWatchlistCache();
    if (typeof startAlertPolling === "function") startAlertPolling();
})();
