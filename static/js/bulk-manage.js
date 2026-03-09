/* ── Bulk Manage (Edit-Mode) shared helpers ──────────────── */

let _bulkDeleteCallback = null;

/**
 * Update the Manage / Done toggle button text & style.
 * @param {"pf"|"wl"} scope
 */
function _updateManageBtn(scope) {
    const btn = document.getElementById(scope + "-manage-btn");
    if (!btn) return;
    const active = scope === "pf" ? _pfEditMode : _wlEditMode;
    btn.textContent = active ? "Done" : "Manage";
    btn.classList.toggle("btn-ghost", !active);
    btn.classList.toggle("btn-primary", active);
}

/**
 * Update the sticky bulk-action toolbar counter & button states.
 * @param {"pf"|"wl"} scope
 */
function _updateBulkToolbar(scope) {
    const selected = scope === "pf" ? _pfSelected : _wlSelected;
    const total = scope === "pf"
        ? document.querySelectorAll(".pf-h-row").length
        : document.querySelectorAll(".watchlist-card").length;

    const counter = document.getElementById("bulk-counter-" + scope);
    if (counter) counter.textContent = `${selected.size} of ${total} selected`;

    const delBtn = document.getElementById("bulk-delete-btn-" + scope);
    if (delBtn) delBtn.disabled = selected.size === 0;

    const selAllBtn = document.getElementById("bulk-selall-" + scope);
    if (selAllBtn) selAllBtn.textContent = selected.size === total && total > 0 ? "Deselect All" : "Select All";
}

/**
 * Open the confirmation modal listing symbols about to be deleted.
 * @param {"portfolio"|"watchlist"} type
 * @param {string[]} symbols
 * @param {Function} onConfirm
 */
function openBulkDeleteModal(type, symbols, onConfirm) {
    _bulkDeleteCallback = onConfirm;
    const overlay = document.getElementById("bulk-delete-modal-overlay");
    const title = document.getElementById("bulk-delete-title");
    const list = document.getElementById("bulk-delete-list");

    title.textContent = type === "portfolio"
        ? `Remove ${symbols.length} holding${symbols.length !== 1 ? "s" : ""}?`
        : `Remove ${symbols.length} item${symbols.length !== 1 ? "s" : ""} from watchlist?`;

    list.innerHTML = symbols.map(s => `<span class="bulk-chip">${s}</span>`).join("");
    overlay.classList.add("open");
}

function closeBulkDeleteModal(e) {
    if (e && e.target !== e.currentTarget && !e.currentTarget.classList.contains("btn")) return;
    document.getElementById("bulk-delete-modal-overlay").classList.remove("open");
    _bulkDeleteCallback = null;
}

function confirmBulkDelete() {
    document.getElementById("bulk-delete-modal-overlay").classList.remove("open");
    if (_bulkDeleteCallback) {
        _bulkDeleteCallback();
        _bulkDeleteCallback = null;
    }
}
