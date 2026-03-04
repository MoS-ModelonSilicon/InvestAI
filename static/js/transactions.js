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

    if (txs.length === 0) { tbody.innerHTML = ""; empty.style.display = "block"; return; }

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
    if (id) await api.put(`/api/transactions/${id}`, data);
    else await api.post("/api/transactions", data);
    closeModal();
    loadTransactions();
}

async function editTransaction(id) {
    const txs = await api.get("/api/transactions?limit=1000");
    const tx = txs.find((t) => t.id === id);
    if (tx) openTransactionModal(tx);
}

async function deleteTransaction(id) {
    if (!confirm("Delete this transaction?")) return;
    await api.del(`/api/transactions/${id}`);
    loadTransactions();
}

function filterTransactions(query) {
    const q = (query || "").toLowerCase().trim();
    const rows = document.querySelectorAll("#tx-body tr");
    let visible = 0;
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const match = !q || text.includes(q);
        row.style.display = match ? "" : "none";
        if (match) visible++;
    });
    let noRes = document.getElementById("tx-no-results");
    if (!q || visible > 0) {
        if (noRes) noRes.remove();
    } else {
        if (!noRes) {
            noRes = document.createElement("div");
            noRes.id = "tx-no-results";
            noRes.className = "search-no-results";
            const wrapper = document.querySelector("#page-transactions .table-wrapper");
            if (wrapper) wrapper.parentElement.appendChild(noRes);
        }
        noRes.textContent = `No transactions matching "${query}"`;
    }
}
