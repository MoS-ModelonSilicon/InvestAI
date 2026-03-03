/**
 * Reusable pagination component.
 * renderPagination(containerId, {page, total_pages, total}, onPageChange)
 */
function renderPagination(containerId, paginationData, onPageChange) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const { page, total_pages, total, per_page } = paginationData;
    if (total_pages <= 1) { el.innerHTML = ""; return; }

    const start = (page - 1) * per_page + 1;
    const end = Math.min(page * per_page, total);

    let html = '<div class="pag-bar">';
    html += `<span class="pag-info">Showing ${start}–${end} of ${total}</span>`;
    html += '<div class="pag-buttons">';

    // Prev
    if (page > 1) {
        html += `<button class="pag-btn" onclick="${onPageChange}(${page - 1})">‹ Prev</button>`;
    } else {
        html += `<button class="pag-btn pag-disabled" disabled>‹ Prev</button>`;
    }

    // Page numbers
    const maxVisible = 7;
    let pages = [];
    if (total_pages <= maxVisible) {
        for (let i = 1; i <= total_pages; i++) pages.push(i);
    } else {
        pages.push(1);
        let rangeStart = Math.max(2, page - 2);
        let rangeEnd = Math.min(total_pages - 1, page + 2);
        if (page <= 3) { rangeStart = 2; rangeEnd = 5; }
        if (page >= total_pages - 2) { rangeStart = total_pages - 4; rangeEnd = total_pages - 1; }
        if (rangeStart > 2) pages.push("...");
        for (let i = rangeStart; i <= rangeEnd; i++) pages.push(i);
        if (rangeEnd < total_pages - 1) pages.push("...");
        pages.push(total_pages);
    }

    for (const p of pages) {
        if (p === "...") {
            html += `<span class="pag-ellipsis">…</span>`;
        } else if (p === page) {
            html += `<button class="pag-btn pag-active">${p}</button>`;
        } else {
            html += `<button class="pag-btn" onclick="${onPageChange}(${p})">${p}</button>`;
        }
    }

    // Next
    if (page < total_pages) {
        html += `<button class="pag-btn" onclick="${onPageChange}(${page + 1})">Next ›</button>`;
    } else {
        html += `<button class="pag-btn pag-disabled" disabled>Next ›</button>`;
    }

    html += '</div></div>';
    el.innerHTML = html;
}
