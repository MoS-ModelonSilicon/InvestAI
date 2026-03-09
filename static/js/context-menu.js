/* ── Universal Stock Context Menu ─────────────────────────── */
/* Right-click any element with data-symbol to get quick actions */

(function () {
    let _menu = null;
    let _currentSymbol = null;
    let _currentName = null;
    let _currentPrice = null;

    function createMenu() {
        if (_menu) return _menu;
        _menu = document.createElement("div");
        _menu.id = "stock-context-menu";
        _menu.className = "ctx-menu";
        _menu.innerHTML = `
            <div class="ctx-menu-header">
                <span class="ctx-menu-symbol" id="ctx-symbol"></span>
                <span class="ctx-menu-name" id="ctx-name"></span>
            </div>
            <div class="ctx-menu-divider"></div>
            <button class="ctx-menu-item" onclick="ctxAction('detail')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                View Details
            </button>
            <button class="ctx-menu-item" onclick="ctxAction('watchlist')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
                Add to Watchlist
            </button>
            <button class="ctx-menu-item" onclick="ctxAction('portfolio')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                Add to Portfolio (Buy)
            </button>
            <div class="ctx-menu-divider"></div>
            <button class="ctx-menu-item" onclick="ctxAction('alert')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                Set Price Alert
            </button>
            <div class="ctx-menu-divider"></div>
            <button class="ctx-menu-item" onclick="ctxAction('technical')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 8 13 13 9 9 2 16"/><line x1="2" y1="20" x2="22" y2="20"/><line x1="22" y1="4" x2="22" y2="20"/></svg>
                Technical Analysis
            </button>
        `;
        document.body.appendChild(_menu);
        return _menu;
    }

    // Close menu on click outside or Escape
    document.addEventListener("click", (e) => {
        if (_menu && !_menu.contains(e.target)) {
            _menu.classList.remove("ctx-menu-visible");
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && _menu) {
            _menu.classList.remove("ctx-menu-visible");
        }
    });

    // Listen for right-click on any element with data-symbol
    document.addEventListener("contextmenu", (e) => {
        const target = e.target.closest("[data-symbol]");
        if (!target) return; // Let browser default menu show

        e.preventDefault();
        e.stopPropagation();

        _currentSymbol = target.dataset.symbol;
        _currentName = target.dataset.stockName || _currentSymbol;
        _currentPrice = target.dataset.stockPrice ? parseFloat(target.dataset.stockPrice) : null;

        const menu = createMenu();
        document.getElementById("ctx-symbol").textContent = _currentSymbol;
        document.getElementById("ctx-name").textContent = _currentName !== _currentSymbol ? _currentName : "";

        // Position the menu
        menu.classList.add("ctx-menu-visible");
        const menuW = menu.offsetWidth;
        const menuH = menu.offsetHeight;
        let x = e.clientX;
        let y = e.clientY;

        if (x + menuW > window.innerWidth) x = window.innerWidth - menuW - 8;
        if (y + menuH > window.innerHeight) y = window.innerHeight - menuH - 8;
        if (x < 0) x = 8;
        if (y < 0) y = 8;

        menu.style.left = x + "px";
        menu.style.top = y + "px";
    });

    // Expose global action handler
    window.ctxAction = function (action) {
        if (!_currentSymbol) return;
        const sym = _currentSymbol;
        const name = _currentName || sym;
        const price = _currentPrice;

        // Hide menu
        if (_menu) _menu.classList.remove("ctx-menu-visible");

        switch (action) {
            case "detail":
                navigateToStock(sym);
                break;
            case "watchlist":
                if (typeof addToWatchlistFromDetail === "function") {
                    addToWatchlistFromDetail(sym, name);
                } else if (typeof addToWLFromScreener === "function") {
                    addToWLFromScreener(sym, name);
                }
                break;
            case "portfolio":
                if (typeof openAddHoldingModal === "function") {
                    openAddHoldingModal(sym, name, price || undefined);
                }
                break;
            case "alert":
                if (typeof openAlertModal === "function") {
                    openAlertModal();
                    // Pre-fill the symbol field
                    setTimeout(() => {
                        const alertSym = document.getElementById("alert-symbol");
                        if (alertSym) alertSym.value = sym;
                    }, 50);
                }
                break;
            case "technical":
                if (typeof showTADetail === "function") {
                    showTADetail(sym);
                }
                break;
        }
    };

    // ── Quick Action Buttons Helper ────────────────────────────
    // Creates inline quick-action buttons for any stock element
    window.stockQuickActions = function (symbol, name, price, opts = {}) {
        const safeName = (name || "").replace(/'/g, "\\'");
        const priceVal = price ? price.toFixed(2) : "null";
        const showWatch = opts.hideWatch !== true;
        const showBuy = opts.hideBuy !== true;
        const showDetail = opts.hideDetail !== true;

        let html = '<span class="stock-quick-actions">';
        if (showDetail) {
            html += `<button class="btn btn-sm sq-btn sq-detail" onclick="event.stopPropagation();navigateToStock('${symbol}')" title="View details">📈</button>`;
        }
        if (showWatch) {
            const _w = typeof isInWatchlist === "function" && isInWatchlist(symbol);
            html += `<button class="btn btn-sm sq-btn sq-watch${_w ? ' wl-watched' : ''}" data-wl-symbol="${symbol}" onclick="event.stopPropagation();addToWatchlistFromDetail('${symbol}','${safeName}')" title="${_w ? symbol + ' is in your watchlist' : 'Add to watchlist'}">${_w ? '✓' : '👁'}</button>`;
        }
        if (showBuy) {
            html += `<button class="btn btn-sm sq-btn sq-buy" onclick="event.stopPropagation();openAddHoldingModal('${symbol}','${safeName}',${priceVal})" title="Add to portfolio">💰</button>`;
        }
        html += '</span>';
        return html;
    };

    // ── Buy Bundle Helper ──────────────────────────────────────
    // Opens a modal to buy multiple stocks at once
    window.buyStockBundle = function (stocks) {
        // stocks: array of { symbol, name, price, allocation_pct? }
        if (!stocks || stocks.length === 0) return;

        let overlay = document.getElementById("bundle-modal-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "bundle-modal-overlay";
            overlay.className = "modal-overlay";
            overlay.onclick = (e) => { if (e.target === overlay) overlay.classList.remove("open"); };
            document.body.appendChild(overlay);
        }

        const rows = stocks.map((s, i) => {
            const priceFmt = s.price ? currSym(s.currency) + s.price.toFixed(2) : "N/A";
            const allocPct = s.allocation_pct ? s.allocation_pct.toFixed(1) + "%" : "—";
            return `<tr>
                <td><input type="checkbox" class="bundle-check" data-idx="${i}" checked></td>
                <td><strong>${s.symbol}</strong></td>
                <td class="text-muted">${s.name || ""}</td>
                <td class="text-right">${priceFmt}</td>
                <td class="text-right">${allocPct}</td>
                <td><input type="number" class="bundle-qty" data-idx="${i}" value="1" min="0.01" step="0.01" style="width:70px;"></td>
            </tr>`;
        }).join("");

        overlay.innerHTML = `
            <div class="modal bundle-modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>Buy Stock Bundle (${stocks.length} stocks)</h2>
                    <button class="modal-close" onclick="document.getElementById('bundle-modal-overlay').classList.remove('open')">&times;</button>
                </div>
                <div class="bundle-body">
                    <p class="bundle-subtitle">Select which stocks to add to your portfolio. Adjust quantities as needed.</p>
                    <div class="bundle-controls">
                        <button class="btn btn-sm" onclick="bundleSelectAll(true)">Select All</button>
                        <button class="btn btn-sm" onclick="bundleSelectAll(false)">Deselect All</button>
                    </div>
                    <div class="table-wrapper">
                        <table class="tx-table bundle-table">
                            <thead><tr>
                                <th style="width:40px;"><input type="checkbox" id="bundle-check-all" checked onchange="bundleSelectAll(this.checked)"></th>
                                <th>Symbol</th><th>Name</th><th class="text-right">Price</th><th class="text-right">Alloc</th><th>Qty</th>
                            </tr></thead>
                            <tbody id="bundle-stocks-body">${rows}</tbody>
                        </table>
                    </div>
                </div>
                <div class="bundle-footer">
                    <button type="button" class="btn btn-ghost" onclick="document.getElementById('bundle-modal-overlay').classList.remove('open')">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="executeBundleBuy()">Add Selected to Portfolio</button>
                </div>
            </div>`;

        // Store stocks data for execution
        overlay._stocks = stocks;
        overlay.classList.add("open");
    };

    window.bundleSelectAll = function (checked) {
        document.querySelectorAll(".bundle-check").forEach(cb => cb.checked = checked);
        const master = document.getElementById("bundle-check-all");
        if (master) master.checked = checked;
    };

    window.executeBundleBuy = function () {
        const overlay = document.getElementById("bundle-modal-overlay");
        if (!overlay || !overlay._stocks) return;

        const stocks = overlay._stocks;
        const checks = document.querySelectorAll(".bundle-check");
        const qtys = document.querySelectorAll(".bundle-qty");

        // Collect selected holdings
        const holdings = [];
        for (let i = 0; i < checks.length; i++) {
            if (!checks[i].checked) continue;
            const s = stocks[i];
            const qty = parseFloat(qtys[i].value) || 1;
            holdings.push({
                symbol: s.symbol,
                name: s.name || s.symbol,
                quantity: qty,
                buy_price: s.price || 0,
                buy_date: new Date().toISOString().split("T")[0],
                notes: "Added via bundle buy",
            });
        }

        if (holdings.length === 0) {
            if (typeof showToast === "function") showToast("No stocks selected", "error");
            return;
        }

        // Close modal immediately — work happens in background
        overlay.classList.remove("open");
        if (typeof showToast === "function") showToast(`Adding ${holdings.length} stocks…`, "info");

        // Fire bulk request in background (no await — user is free)
        api.post("/api/portfolio/holdings/bulk", { holdings })
            .then((res) => {
                if (typeof showToast === "function") {
                    if (res.added > 0 && res.failed === 0) {
                        showToast(`✓ ${res.added} stocks added to portfolio!`);
                    } else if (res.added > 0) {
                        showToast(`${res.added} added, ${res.failed} failed`, "info");
                    } else {
                        showToast("No stocks were added", "error");
                    }
                }
            })
            .catch(() => {
                if (typeof showToast === "function") showToast("Bundle buy failed", "error");
            });
    };
})();
