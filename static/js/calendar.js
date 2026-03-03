async function loadCalendar() {
    const container = document.getElementById("calendar-container");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading calendar events...</p></div>';

    try {
        const [earnings, economic] = await Promise.all([
            api.get("/api/calendar/earnings"),
            api.get("/api/calendar/economic"),
        ]);
        renderCalendar(earnings, economic);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load calendar.</p>';
    }
}

function renderCalendar(earnings, economic) {
    const container = document.getElementById("calendar-container");

    let html = `<div class="cal-tabs">
        <button class="cal-tab active" onclick="filterCalTab('earnings', this)">Earnings & Dividends (${earnings.length})</button>
        <button class="cal-tab" onclick="filterCalTab('economic', this)">Economic Events</button>
    </div>`;

    // Earnings Section
    html += `<div class="cal-section" id="cal-earnings">`;
    if (earnings.length === 0) {
        html += `<div class="empty-state"><p>No upcoming earnings or dividend events found. Add stocks to your watchlist or portfolio to see their events here.</p></div>`;
    } else {
        const grouped = {};
        earnings.forEach(e => {
            const date = e.date || "Unknown";
            if (!grouped[date]) grouped[date] = [];
            grouped[date].push(e);
        });

        const eventIcons = { Earnings: "📊", Dividend: "💰", "Ex-Dividend": "📅" };

        Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).forEach(([date, events]) => {
            const d = new Date(date + "T00:00:00");
            const dateStr = isNaN(d.getTime()) ? date : d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
            const isPast = d < new Date(new Date().toDateString());

            html += `<div class="cal-date-group ${isPast ? "cal-past" : ""}">
                <div class="cal-date-header">${dateStr}</div>`;
            events.forEach(e => {
                html += `
                <div class="cal-event" onclick="navigateToStock('${e.symbol}')">
                    <span class="cal-event-icon">${eventIcons[e.event] || "📌"}</span>
                    <span class="cal-event-symbol">${e.symbol}</span>
                    <span class="cal-event-name">${e.name}</span>
                    <span class="cal-event-type">${e.event}</span>
                </div>`;
            });
            html += `</div>`;
        });
    }
    html += `</div>`;

    // Economic Events Section
    html += `<div class="cal-section" id="cal-economic" style="display:none;">`;
    html += `<div class="eco-grid">`;
    economic.forEach(e => {
        const impactCls = e.impact === "High" ? "impact-high" : "impact-medium";
        html += `
        <div class="eco-card">
            <div class="eco-card-header">
                <span class="eco-name">${e.event}</span>
                <span class="eco-impact ${impactCls}">${e.impact} Impact</span>
            </div>
            <div class="eco-freq">${e.frequency}</div>
            <div class="eco-desc">${e.description}</div>
        </div>`;
    });
    html += `</div></div>`;

    container.innerHTML = html;
}

function filterCalTab(tab, btn) {
    document.querySelectorAll(".cal-tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("cal-earnings").style.display = tab === "earnings" ? "block" : "none";
    document.getElementById("cal-economic").style.display = tab === "economic" ? "block" : "none";
}
