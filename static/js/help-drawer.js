/* ── Help Drawer ──────────────────────────────────────────────
 *  A slide-out help panel with:
 *  1. Quick-start checklist (gamified progress)
 *  2. Feature guides grouped by section
 *  3. Hidden gems / pro tips
 *  4. "Take a Tour" button
 *
 *  Triggered by the ? button in the sidebar.
 * ──────────────────────────────────────────────────────────── */

(function () {
    "use strict";

    const LS_CHECKLIST = "investai_checklist";

    /* ── Checklist items ───────────────────────────────────── */
    const CHECKLIST = [
        { id: "add_holding", label: "Add your first stock holding", page: "portfolio", icon: "💼" },
        { id: "set_alert", label: "Set a price alert", page: "alerts", icon: "⏰" },
        { id: "run_screener", label: "Use the stock screener", page: "screener", icon: "🔍" },
        { id: "run_ai_picks", label: "Run an AI portfolio simulation", page: "autopilot", icon: "🤖" },
        { id: "try_advisor", label: "Get Smart Advisor analysis", page: "smart-advisor", icon: "🧠" },
        { id: "setup_dca", label: "Create a DCA plan", page: "dca", icon: "📈" },
        { id: "risk_profile", label: "Complete your Risk Profile", page: "profile", icon: "🎯" },
        { id: "right_click", label: "Right-click a stock symbol", page: null, icon: "🖱️" },
    ];

    /* ── Feature guide cards ───────────────────────────────── */
    const FEATURES = [
        {
            section: "My Portfolio",
            items: [
                { title: "Dashboard", desc: "Financial overview with income/expense trends, budget bars, and featured stocks with sparklines.", page: "dashboard", icon: "📊" },
                { title: "Portfolio", desc: "Track holdings with real-time P&L, sector allocation pie, and S&P 500 comparison chart.", page: "portfolio", icon: "💼" },
                { title: "Watchlist", desc: "Bookmark stocks and monitor live prices. Search by symbol, name, or sector.", page: "watchlist", icon: "⭐" },
                { title: "DCA Planner", desc: "Dollar-cost averaging plans with auto dip detection. Set monthly budgets and get AI budget tips.", page: "dca", icon: "📈" },
                { title: "Price Alerts", desc: "Set above/below price alerts. A bell badge appears in the sidebar when alerts trigger.", page: "alerts", icon: "🔔" },
            ],
        },
        {
            section: "Discover",
            items: [
                { title: "Screener", desc: "Filter 280+ stocks by 10 dimensions. Try Quick Presets (Value Stocks, High Dividend, etc.) for instant ideas.", page: "screener", icon: "🔍" },
                { title: "Value Scanner", desc: "Graham-Buffett analysis with quality scores. Generate a dollar-weighted Action Plan and buy all picks at once.", page: "value-scanner", icon: "💎" },
                { title: "AI Picks", desc: "Choose a strategy, set $ amount, backtest against S&P 500. One click adds the entire portfolio.", page: "autopilot", icon: "🤖" },
                { title: "Personalized Picks", desc: "Complete your Risk Profile first, then get AI recommendations matched to your risk tolerance.", page: "recommendations", icon: "🎯" },
                { title: "Advisor (Long-term)", desc: "Berkshire-style graded analysis with Company DNA deep-dives, support/resistance charts.", page: "smart-advisor", icon: "🧠" },
                { title: "Trading Advisor", desc: "Short-term picks with entry/target/stop, R/R ratio, Hidden Gems, Smart Money, Momentum tabs.", page: "trading-advisor", icon: "⚡" },
                { title: "IL Funds", desc: "Israeli fund screener — find cheapest Kaspit funds, kosher-only filter, fee comparison.", page: "il-funds", icon: "🏦" },
            ],
        },
        {
            section: "Track & Learn",
            items: [
                { title: "News", desc: "Aggregated news from your watchlist and portfolio holdings.", page: "news", icon: "📰" },
                { title: "Calendar", desc: "Upcoming earnings dates and economic events.", page: "calendar", icon: "📅" },
                { title: "Picks Tracker", desc: "Backtest Discord community picks. Export to CSV, add all to watchlist.", page: "picks-tracker", icon: "✅" },
                { title: "Learn", desc: "Educational articles filtered by Beginner/Intermediate/Advanced.", page: "education", icon: "📚" },
            ],
        },
    ];

    /* ── Hidden gems / pro tips ─────────────────────────────── */
    const PRO_TIPS = [
        { icon: "🖱️", tip: "<strong>Right-click any stock symbol</strong> anywhere on the site to view details, add to watchlist/portfolio, or set alerts." },
        { icon: "📊", tip: "On any <strong>Stock Detail</strong> page, toggle the <strong>SPY overlay</strong> to compare performance vs S&P 500." },
        { icon: "💰", tip: "The <strong>Value Scanner Action Plan</strong> generates a dollar-weighted buy list and can add everything to your portfolio in one click." },
        { icon: "🚀", tip: "In <strong>AI Picks</strong> and <strong>Advisor</strong>, click <strong>Buy All</strong> to add the entire suggested portfolio at once." },
        { icon: "📥", tip: "The <strong>Picks Tracker</strong> has a CSV Export button — great for spreadsheet analysis." },
        { icon: "💡", tip: "<strong>DCA Budget Tips</strong> (small button) gives AI-generated suggestions for your dollar-cost averaging strategy." },
        { icon: "🔎", tip: "The <strong>Screener search bar</strong> bypasses all filters — clear it to go back to filtered results." },
        { icon: "🌓", tip: "Toggle <strong>light/dark mode</strong> with the sun/moon icon next to the InvestAI logo." },
    ];

    /* ── Build drawer HTML ─────────────────────────────────── */
    function buildDrawerHTML() {
        const saved = JSON.parse(localStorage.getItem(LS_CHECKLIST) || "{}");
        const completed = CHECKLIST.filter((c) => saved[c.id]).length;
        const pct = Math.round((completed / CHECKLIST.length) * 100);

        let html = `
        <div class="help-drawer-header">
            <h2>Help Center</h2>
            <button class="help-drawer-close" id="help-drawer-close" title="Close">&times;</button>
        </div>
        <div class="help-drawer-content">
            <!-- Tour button -->
            <button class="help-tour-btn" id="help-tour-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Take the Guided Tour
            </button>

            <!-- Quick-start checklist -->
            <div class="help-section">
                <div class="help-section-title" data-collapse="checklist">
                    <span>🚀 Quick Start</span>
                    <span class="help-progress-label">${completed}/${CHECKLIST.length}</span>
                </div>
                <div class="help-progress-bar">
                    <div class="help-progress-fill" style="width:${pct}%"></div>
                </div>
                <div class="help-collapse-body" id="help-checklist-body">
                    ${CHECKLIST.map((c) => `
                        <label class="help-checklist-item ${saved[c.id] ? "done" : ""}" data-check-id="${c.id}" ${c.page ? `data-check-page="${c.page}"` : ""}>
                            <span class="help-check-icon">${saved[c.id] ? "✅" : "⬜"}</span>
                            <span class="help-check-label">${c.icon} ${c.label}</span>
                            ${c.page ? `<span class="help-check-go">Go →</span>` : ""}
                        </label>
                    `).join("")}
                </div>
            </div>

            <!-- Feature guide -->
            <div class="help-section">
                <div class="help-section-title" data-collapse="features">
                    <span>📖 Feature Guide</span>
                </div>
                <div class="help-collapse-body" id="help-features-body">
                    ${FEATURES.map((group) => `
                        <div class="help-feature-group">
                            <div class="help-feature-group-label">${group.section}</div>
                            ${group.items.map((f) => `
                                <div class="help-feature-card" data-help-page="${f.page}">
                                    <span class="help-feature-icon">${f.icon}</span>
                                    <div class="help-feature-info">
                                        <strong>${f.title}</strong>
                                        <span>${f.desc}</span>
                                    </div>
                                    <span class="help-feature-go">→</span>
                                </div>
                            `).join("")}
                        </div>
                    `).join("")}
                </div>
            </div>

            <!-- Pro tips -->
            <div class="help-section">
                <div class="help-section-title" data-collapse="tips">
                    <span>💡 Hidden Gems & Pro Tips</span>
                </div>
                <div class="help-collapse-body" id="help-tips-body">
                    ${PRO_TIPS.map((t) => `
                        <div class="help-tip-card">
                            <span class="help-tip-icon">${t.icon}</span>
                            <span class="help-tip-text">${t.tip}</span>
                        </div>
                    `).join("")}
                </div>
            </div>

            <!-- Keyboard shortcuts -->
            <div class="help-section">
                <div class="help-section-title" data-collapse="keyboard">
                    <span>⌨️ Tour Keyboard Shortcuts</span>
                </div>
                <div class="help-collapse-body" id="help-keyboard-body" style="display:none">
                    <div class="help-kbd-row"><kbd>→</kbd> / <kbd>Enter</kbd> — Next step</div>
                    <div class="help-kbd-row"><kbd>←</kbd> — Previous step</div>
                    <div class="help-kbd-row"><kbd>Esc</kbd> — Close tour</div>
                </div>
            </div>
        </div>`;

        return html;
    }

    /* ── Drawer element ────────────────────────────────────── */
    let drawerEl = null;
    let backdropEl = null;

    function createDrawer() {
        if (drawerEl) return;

        backdropEl = document.createElement("div");
        backdropEl.className = "help-drawer-backdrop";
        document.body.appendChild(backdropEl);

        drawerEl = document.createElement("div");
        drawerEl.className = "help-drawer";
        drawerEl.innerHTML = buildDrawerHTML();
        document.body.appendChild(drawerEl);

        // Close handlers
        drawerEl.querySelector("#help-drawer-close").addEventListener("click", closeDrawer);
        backdropEl.addEventListener("click", closeDrawer);

        // Tour button
        drawerEl.querySelector("#help-tour-btn").addEventListener("click", () => {
            closeDrawer();
            setTimeout(() => window.startTour && window.startTour(), 300);
        });

        // Collapsible sections
        drawerEl.querySelectorAll(".help-section-title[data-collapse]").forEach((title) => {
            title.style.cursor = "pointer";
            title.addEventListener("click", () => {
                const key = title.dataset.collapse;
                const body = drawerEl.querySelector(`#help-${key}-body`);
                if (body) {
                    const hidden = body.style.display === "none";
                    body.style.display = hidden ? "" : "none";
                    title.classList.toggle("collapsed", !hidden);
                }
            });
        });

        // Feature card click → navigate
        drawerEl.querySelectorAll(".help-feature-card[data-help-page]").forEach((card) => {
            card.style.cursor = "pointer";
            card.addEventListener("click", () => {
                const page = card.dataset.helpPage;
                closeDrawer();
                if (typeof navigateTo === "function") {
                    setTimeout(() => navigateTo(page), 200);
                }
            });
        });

        // Checklist "Go" button click
        drawerEl.querySelectorAll(".help-checklist-item[data-check-page]").forEach((item) => {
            const goBtn = item.querySelector(".help-check-go");
            if (goBtn) {
                goBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const page = item.dataset.checkPage;
                    closeDrawer();
                    if (typeof navigateTo === "function") {
                        setTimeout(() => navigateTo(page), 200);
                    }
                });
            }
        });

        // Checklist checkbox toggle
        drawerEl.querySelectorAll(".help-checklist-item").forEach((item) => {
            item.addEventListener("click", () => {
                const id = item.dataset.checkId;
                const saved = JSON.parse(localStorage.getItem(LS_CHECKLIST) || "{}");
                saved[id] = !saved[id];
                localStorage.setItem(LS_CHECKLIST, JSON.stringify(saved));
                refreshChecklist();
            });
        });
    }

    function refreshChecklist() {
        if (!drawerEl) return;
        const saved = JSON.parse(localStorage.getItem(LS_CHECKLIST) || "{}");
        const completed = CHECKLIST.filter((c) => saved[c.id]).length;
        const pct = Math.round((completed / CHECKLIST.length) * 100);

        drawerEl.querySelector(".help-progress-label").textContent = `${completed}/${CHECKLIST.length}`;
        drawerEl.querySelector(".help-progress-fill").style.width = pct + "%";

        drawerEl.querySelectorAll(".help-checklist-item").forEach((item) => {
            const id = item.dataset.checkId;
            const done = !!saved[id];
            item.classList.toggle("done", done);
            item.querySelector(".help-check-icon").textContent = done ? "✅" : "⬜";
        });
    }

    /* ── Open/close ────────────────────────────────────────── */
    function openDrawer() {
        createDrawer();
        requestAnimationFrame(() => {
            drawerEl.classList.add("open");
            backdropEl.classList.add("open");
        });
    }

    function closeDrawer() {
        if (drawerEl) drawerEl.classList.remove("open");
        if (backdropEl) backdropEl.classList.remove("open");
    }

    /* ── Sidebar button ────────────────────────────────────── */
    function initHelpButton() {
        const btn = document.getElementById("help-drawer-btn");
        if (btn) {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                openDrawer();
            });
        }
    }

    window._openHelpDrawer = openDrawer;
    window._closeHelpDrawer = closeDrawer;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initHelpButton);
    } else {
        initHelpButton();
    }
})();
