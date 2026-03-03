let alertPollInterval = null;

async function loadAlerts() {
    const container = document.getElementById("alerts-container");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading alerts...</p></div>';

    try {
        const alerts = await api.get("/api/alerts");
        renderAlerts(alerts);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load alerts.</p>';
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById("alerts-container");
    const count = document.getElementById("alerts-count");
    const triggered = alerts.filter(a => a.triggered);
    const active = alerts.filter(a => a.active && !a.triggered);

    if (count) count.textContent = `${active.length} active · ${triggered.length} triggered`;
    updateBellBadge(triggered.length);

    if (alerts.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No alerts set. Create one to get notified when a stock hits your target price.</p></div>`;
        return;
    }

    let html = "";

    if (triggered.length > 0) {
        html += `<h3 class="alerts-section-title">Triggered</h3><div class="alerts-grid">`;
        triggered.forEach(a => {
            html += renderAlertCard(a, true);
        });
        html += `</div>`;
    }

    if (active.length > 0) {
        html += `<h3 class="alerts-section-title">Active</h3><div class="alerts-grid">`;
        active.forEach(a => {
            html += renderAlertCard(a, false);
        });
        html += `</div>`;
    }

    const dismissed = alerts.filter(a => !a.active);
    if (dismissed.length > 0) {
        html += `<h3 class="alerts-section-title text-muted">Dismissed</h3><div class="alerts-grid">`;
        dismissed.forEach(a => {
            html += renderAlertCard(a, false, true);
        });
        html += `</div>`;
    }

    container.innerHTML = html;
}

function renderAlertCard(a, isTriggered, isDismissed = false) {
    const condIcon = a.condition === "above" ? "▲" : "▼";
    const condText = a.condition === "above" ? "rises above" : "drops below";
    const statusCls = isTriggered ? "alert-triggered" : isDismissed ? "alert-dismissed" : "alert-active";

    return `
    <div class="alert-card ${statusCls}" onclick="navigateToStock('${a.symbol}')">
        <div class="alert-card-top">
            <div>
                <span class="alert-symbol">${a.symbol}</span>
                <span class="alert-name">${a.name}</span>
            </div>
            <div class="alert-current">${a.current_price ? fmt(a.current_price) : "—"}</div>
        </div>
        <div class="alert-condition">
            <span class="alert-cond-icon">${condIcon}</span>
            Notify when ${condText} <strong>${fmt(a.target_price)}</strong>
        </div>
        ${isTriggered ? `<div class="alert-triggered-badge">TRIGGERED${a.triggered_at ? " · " + new Date(a.triggered_at).toLocaleDateString() : ""}</div>` : ""}
        <div class="alert-actions">
            ${isTriggered ? `<button class="btn btn-sm" onclick="event.stopPropagation();dismissAlert(${a.id})">Dismiss</button>` : ""}
            <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();deleteAlert(${a.id})">Delete</button>
        </div>
    </div>`;
}

function openAlertModal() {
    document.getElementById("alert-modal-overlay").classList.add("open");
    document.getElementById("alert-symbol").value = "";
    document.getElementById("alert-price").value = "";
    document.getElementById("alert-condition").value = "above";
}

function closeAlertModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("alert-modal-overlay").classList.remove("open");
}

async function submitAlert(e) {
    e.preventDefault();
    const symbol = document.getElementById("alert-symbol").value.toUpperCase();
    const payload = {
        symbol: symbol,
        name: "",
        condition: document.getElementById("alert-condition").value,
        target_price: parseFloat(document.getElementById("alert-price").value),
    };

    try {
        const info = await api.get(`/api/stock/${symbol}`);
        if (info) payload.name = info.name || symbol;
    } catch (e) { /* use empty name */ }

    try {
        await api.post("/api/alerts", payload);
        closeAlertModal();
        loadAlerts();
    } catch (e) {
        alert("Failed to create alert");
    }
}

async function deleteAlert(id) {
    try {
        await api.del(`/api/alerts/${id}`);
        loadAlerts();
    } catch (e) { alert("Failed to delete alert"); }
}

async function dismissAlert(id) {
    try {
        await api.post(`/api/alerts/${id}/dismiss`, {});
        loadAlerts();
    } catch (e) { alert("Failed to dismiss alert"); }
}

function updateBellBadge(count) {
    const badge = document.getElementById("bell-badge");
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = "flex";
        } else {
            badge.style.display = "none";
        }
    }
}

async function checkTriggeredAlerts() {
    try {
        const triggered = await api.get("/api/alerts/triggered");
        updateBellBadge(triggered.length);
    } catch (e) { /* ignore */ }
}

function startAlertPolling() {
    checkTriggeredAlerts();
    if (!alertPollInterval) {
        alertPollInterval = setInterval(checkTriggeredAlerts, 60000);
    }
}
