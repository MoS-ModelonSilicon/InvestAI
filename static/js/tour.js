/* ── Guided Product Tour ──────────────────────────────────────
 *  A lightweight interactive onboarding walkthrough built without
 *  external dependencies.  Uses CSS spotlight overlays to guide
 *  new users through the main features of InvestAI.
 *
 *  Auto-triggers once on first login (localStorage flag).
 *  Can also be started manually via window.startTour().
 * ──────────────────────────────────────────────────────────── */

(function () {
    "use strict";

    const LS_KEY = "investai_tour_completed";
    const LS_VISITED = "investai_visited_pages";

    /* ── Tour step definitions ─────────────────────────────── */
    const STEPS = [
        {
            title: "Welcome to InvestAI! 🎉",
            body: "Let's take a quick tour of the key features so you can get the most out of the platform. This will only take about 30 seconds.",
            selector: ".logo",
            position: "bottom-right",
        },
        {
            title: "🎯 Build Your Risk Profile",
            body: "Start here! Answer 6 quick questions to get your personal risk score and investor profile. This powers personalized recommendations, DCA budgets, and match scores across the entire platform.",
            selector: '[data-page="profile"]',
            position: "right",
        },
        {
            title: "📊 Dashboard",
            body: "Your financial overview — income, expenses, monthly trends, and budget status all in one place. Use the date range picker to zoom in on any period.",
            selector: '[data-page="dashboard"]',
            position: "right",
        },
        {
            title: "💼 Portfolio",
            body: "Track your holdings with real-time prices, gain/loss calculations, and sector allocation charts. Compare your performance against the S&P 500.",
            selector: '[data-page="portfolio"]',
            position: "right",
        },
        {
            title: "🔍 Screener",
            body: "Filter 280+ stocks & ETFs by sector, market cap, P/E, dividend yield, and more. Try the Value Investing tab for Graham-Buffett style analysis.",
            selector: '[data-page="screener"]',
            position: "right",
        },
        {
            title: "🤖 AI Picks",
            body: "Let AI build a portfolio for you! Choose a strategy, set an investment amount, run a backtest, and see how it compares to the S&P 500. One click adds everything to your portfolio.",
            selector: '[data-page="autopilot"]',
            position: "right",
        },
        {
            title: "🧠 Smart Advisor",
            body: "Get Berkshire-style analysis with ranked stocks, Company DNA deep-dives, and a Short-term Trading tab with entry/target/stop prices and R/R ratios.",
            selector: '[data-page="smart-advisor"]',
            position: "right",
        },
        {
            title: "⏰ Price Alerts",
            body: "Set price alerts on any stock — you'll see a notification bell badge when they trigger. Works across the whole site.",
            selector: '[data-page="alerts"]',
            position: "right",
        },
        {
            title: "📈 DCA Planner",
            body: "Plan your dollar-cost averaging strategy. Set monthly budgets per stock, and the system automatically spots dip opportunities below your cost basis.",
            selector: '[data-page="dca"]',
            position: "right",
        },
        {
            title: "🎯 Right-Click Power Menu",
            body: "Here's a hidden gem — right-click on ANY stock symbol anywhere on the site to instantly view details, add to watchlist, add to portfolio, or set a price alert!",
            selector: ".ticker-bar",
            position: "bottom",
        },
        {
            title: "💡 Need Help Anytime?",
            body: "Click the <strong>?</strong> help button at the bottom of the sidebar to open the Help Center — with feature guides, a quick-start checklist, and hidden tips!",
            selector: "#help-drawer-btn",
            position: "right",
        },
    ];

    /* ── Overlay + popover DOM ─────────────────────────────── */
    let overlayEl = null;
    let popoverEl = null;
    let spotlightEl = null;
    let currentStep = 0;
    let isActive = false;

    function createDOM() {
        // Backdrop overlay
        overlayEl = document.createElement("div");
        overlayEl.className = "tour-overlay";
        overlayEl.addEventListener("click", closeTour);

        // Spotlight cut-out
        spotlightEl = document.createElement("div");
        spotlightEl.className = "tour-spotlight";

        // Popover
        popoverEl = document.createElement("div");
        popoverEl.className = "tour-popover";
        popoverEl.innerHTML = `
            <div class="tour-popover-arrow"></div>
            <div class="tour-popover-header">
                <span class="tour-popover-title"></span>
                <button class="tour-popover-close" title="Close tour">&times;</button>
            </div>
            <div class="tour-popover-body"></div>
            <div class="tour-popover-footer">
                <span class="tour-popover-progress"></span>
                <div class="tour-popover-actions">
                    <button class="tour-btn tour-btn-skip">Skip Tour</button>
                    <button class="tour-btn tour-btn-prev">← Back</button>
                    <button class="tour-btn tour-btn-next">Next →</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlayEl);
        document.body.appendChild(spotlightEl);
        document.body.appendChild(popoverEl);

        popoverEl.querySelector(".tour-popover-close").addEventListener("click", closeTour);
        popoverEl.querySelector(".tour-btn-skip").addEventListener("click", closeTour);
        popoverEl.querySelector(".tour-btn-prev").addEventListener("click", prevStep);
        popoverEl.querySelector(".tour-btn-next").addEventListener("click", nextStep);

        // Prevent clicks inside popover from closing
        popoverEl.addEventListener("click", (e) => e.stopPropagation());
        spotlightEl.addEventListener("click", (e) => e.stopPropagation());
    }

    function removeDOM() {
        if (overlayEl) overlayEl.remove();
        if (spotlightEl) spotlightEl.remove();
        if (popoverEl) popoverEl.remove();
        overlayEl = spotlightEl = popoverEl = null;
    }

    /* ── Step rendering ────────────────────────────────────── */
    function showStep(idx) {
        currentStep = idx;
        const step = STEPS[idx];
        const target = document.querySelector(step.selector);

        // Update popover content
        popoverEl.querySelector(".tour-popover-title").textContent = step.title;
        popoverEl.querySelector(".tour-popover-body").innerHTML = step.body;
        popoverEl.querySelector(".tour-popover-progress").textContent = `${idx + 1} of ${STEPS.length}`;

        // Button visibility
        const prevBtn = popoverEl.querySelector(".tour-btn-prev");
        const nextBtn = popoverEl.querySelector(".tour-btn-next");
        const skipBtn = popoverEl.querySelector(".tour-btn-skip");
        prevBtn.style.display = idx === 0 ? "none" : "";
        skipBtn.style.display = idx === STEPS.length - 1 ? "none" : "";
        nextBtn.textContent = idx === STEPS.length - 1 ? "Done ✓" : "Next →";

        if (target) {
            // Scroll target into view
            target.scrollIntoView({ behavior: "smooth", block: "center" });

            requestAnimationFrame(() => {
                const rect = target.getBoundingClientRect();
                const pad = 6;

                // Position spotlight
                spotlightEl.style.display = "block";
                spotlightEl.style.top = (rect.top - pad + window.scrollY) + "px";
                spotlightEl.style.left = (rect.left - pad) + "px";
                spotlightEl.style.width = (rect.width + pad * 2) + "px";
                spotlightEl.style.height = (rect.height + pad * 2) + "px";

                // Position popover
                positionPopover(rect, step.position);
            });
        } else {
            // No target found — center the popover
            spotlightEl.style.display = "none";
            popoverEl.style.top = "50%";
            popoverEl.style.left = "50%";
            popoverEl.style.transform = "translate(-50%, -50%)";
        }
    }

    function positionPopover(targetRect, position) {
        const gap = 14;
        popoverEl.style.transform = "";

        // Reset all position props
        popoverEl.style.top = "";
        popoverEl.style.left = "";
        popoverEl.style.bottom = "";
        popoverEl.style.right = "";

        const pw = popoverEl.offsetWidth;
        const ph = popoverEl.offsetHeight;
        const scrollY = window.scrollY;

        switch (position) {
            case "bottom":
            case "bottom-right":
                popoverEl.style.top = (targetRect.bottom + gap + scrollY) + "px";
                popoverEl.style.left = Math.max(10, Math.min(targetRect.left, window.innerWidth - pw - 20)) + "px";
                break;
            case "bottom-left":
                popoverEl.style.top = (targetRect.bottom + gap + scrollY) + "px";
                popoverEl.style.left = Math.max(10, targetRect.right - pw) + "px";
                break;
            case "top":
                popoverEl.style.top = (targetRect.top - ph - gap + scrollY) + "px";
                popoverEl.style.left = Math.max(10, targetRect.left) + "px";
                break;
            case "right":
            default:
                popoverEl.style.top = (targetRect.top + scrollY) + "px";
                popoverEl.style.left = (targetRect.right + gap) + "px";
                // If overflows right, flip to bottom
                if (targetRect.right + gap + pw > window.innerWidth) {
                    popoverEl.style.left = Math.max(10, targetRect.left) + "px";
                    popoverEl.style.top = (targetRect.bottom + gap + scrollY) + "px";
                }
                break;
        }
    }

    /* ── Navigation ────────────────────────────────────────── */
    function nextStep() {
        if (currentStep < STEPS.length - 1) {
            showStep(currentStep + 1);
        } else {
            closeTour();
        }
    }

    function prevStep() {
        if (currentStep > 0) {
            showStep(currentStep - 1);
        }
    }

    function closeTour() {
        if (!isActive) return;
        isActive = false;
        localStorage.setItem(LS_KEY, "true");
        document.body.classList.remove("tour-active");
        removeDOM();
    }

    /* ── Public API ────────────────────────────────────────── */
    function startTour() {
        if (isActive) return;
        isActive = true;
        currentStep = 0;
        document.body.classList.add("tour-active");
        createDOM();
        overlayEl.classList.add("open");
        showStep(0);
    }

    // Keyboard navigation
    document.addEventListener("keydown", (e) => {
        if (!isActive) return;
        if (e.key === "Escape") closeTour();
        if (e.key === "ArrowRight" || e.key === "Enter") nextStep();
        if (e.key === "ArrowLeft") prevStep();
    });

    // Expose globally
    window.startTour = startTour;

    /* ── Auto-trigger on first visit ──────────────────────── */
    function autoTrigger() {
        if (localStorage.getItem(LS_KEY)) return;
        // Small delay so the page is fully rendered
        setTimeout(startTour, 1200);
    }

    /* ── Page-visit tracking (for feature hints) ──────────── */
    function trackVisit(page) {
        const visited = JSON.parse(localStorage.getItem(LS_VISITED) || "{}");
        if (!visited[page]) {
            visited[page] = Date.now();
            localStorage.setItem(LS_VISITED, JSON.stringify(visited));
            // Remove hint dot for this page
            const dot = document.querySelector(`.nav-link[data-page="${page}"] .feature-hint-dot`);
            if (dot) dot.remove();
        }
    }
    window._trackPageVisit = trackVisit;

    /* ── Feature hint dots (pulsing) ──────────────────────── */
    function initFeatureHints() {
        const hintPages = [
            "screener", "autopilot", "smart-advisor", "dca",
            "alerts", "picks-tracker", "il-funds", "profile",
        ];
        const visited = JSON.parse(localStorage.getItem(LS_VISITED) || "{}");

        hintPages.forEach((page) => {
            if (visited[page]) return; // Already visited
            const link = document.querySelector(`.nav-link[data-page="${page}"]`);
            if (!link) return;
            // Don't add if already has one
            if (link.querySelector(".feature-hint-dot")) return;
            const dot = document.createElement("span");
            dot.className = "feature-hint-dot";
            dot.title = "New — click to explore!";
            link.appendChild(dot);
        });
    }

    // Initialize after DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            initFeatureHints();
            autoTrigger();
        });
    } else {
        // DOM already loaded
        setTimeout(() => {
            initFeatureHints();
            autoTrigger();
        }, 500);
    }
})();
