// ── Admin Panel ──────────────────────────────────────────────
let adminCurrentPage = 1;
let adminSearchTimeout = null;

async function loadAdminPanel() {
    // Fire all three independent loads in parallel
    const [statsRes, usersRes, suggestionsRes] = await Promise.allSettled([
        loadAdminStats(),
        loadAdminUsers(),
        loadAdminSuggestions(),
    ]);
    if (statsRes.status === "rejected") {
        console.error("Admin stats error:", statsRes.reason);
        const c = document.getElementById("admin-stats");
        if (c) c.innerHTML = `<div class="card" style="padding:20px;color:#ef4444">Failed to load stats: ${statsRes.reason?.message || statsRes.reason}</div>`;
    }
    if (usersRes.status === "rejected") {
        console.error("Admin users error:", usersRes.reason);
        const tbody = document.getElementById("admin-users-body");
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="color:#ef4444;text-align:center;padding:20px">Failed to load users: ${usersRes.reason?.message || usersRes.reason}</td></tr>`;
    }
    if (suggestionsRes.status === "rejected") {
        console.error("Admin suggestions error:", suggestionsRes.reason);
    }
}

// ── Stats ────────────────────────────────────────────────────
async function loadAdminStats() {
    const stats = await api.get("/api/admin/stats");
    const container = document.getElementById("admin-stats");
    if (!container) return;

    const cards = [
        { label: "Total Users", value: stats.total_users, icon: "👥", color: "#6366f1" },
        { label: "Active Users", value: stats.active_users, icon: "✅", color: "#22c55e" },
        { label: "Disabled", value: stats.disabled_users, icon: "🚫", color: "#ef4444" },
        { label: "Admins", value: stats.admin_count, icon: "🛡️", color: "#f59e0b" },
        { label: "New (7d)", value: stats.new_users_7d, icon: "📈", color: "#06b6d4" },
        { label: "New (30d)", value: stats.new_users_30d, icon: "📊", color: "#8b5cf6" },
        { label: "Transactions", value: stats.total_transactions, icon: "💰", color: "#10b981" },
        { label: "Holdings", value: stats.total_holdings, icon: "📦", color: "#3b82f6" },
        { label: "Alerts", value: stats.total_alerts, icon: "🔔", color: "#ec4899" },
        { label: "DCA Plans", value: stats.total_dca_plans, icon: "🎯", color: "#14b8a6" },
        { label: "Watchlist", value: stats.total_watchlist, icon: "👀", color: "#eab308" },
        { label: "Suggestions", value: stats.total_suggestions, icon: "💡", color: "#a855f7" },
        { label: "New Requests", value: stats.new_suggestions, icon: "📬", color: "#f43f5e" },
    ];

    container.innerHTML = cards.map(c => `
        <div class="card" style="padding:20px;text-align:center;border-left:4px solid ${c.color}">
            <div style="font-size:1.8rem;margin-bottom:4px">${c.icon}</div>
            <div style="font-size:2rem;font-weight:700;color:var(--text-primary)">${c.value.toLocaleString()}</div>
            <div style="font-size:.8rem;color:var(--text-muted);margin-top:4px">${c.label}</div>
        </div>
    `).join("");
}

// ── Users Table ──────────────────────────────────────────────
async function loadAdminUsers(page = 1) {
    adminCurrentPage = page;
    const search = (document.getElementById("admin-user-search")?.value || "").trim();
    const params = new URLSearchParams({ page, per_page: 25 });
    if (search) params.set("search", search);

    const data = await api.get(`/api/admin/users?${params}`);
    const tbody = document.getElementById("admin-users-body");
    const countEl = document.getElementById("admin-user-count");

    if (countEl) countEl.textContent = `${data.total} user${data.total !== 1 ? "s" : ""}`;

    tbody.innerHTML = data.users.map(u => {
        const isActive = u.is_active;
        const isAdmin = u.is_admin;
        const statusBadge = isActive
            ? '<span style="color:#22c55e;font-weight:600">● Active</span>'
            : '<span style="color:#ef4444;font-weight:600">● Disabled</span>';
        const roleBadge = isAdmin
            ? '<span style="background:#f59e0b22;color:#f59e0b;padding:2px 8px;border-radius:6px;font-size:.75rem;font-weight:600">ADMIN</span>'
            : '<span style="color:var(--text-muted);font-size:.85rem">User</span>';
        const joined = u.created_at ? new Date(u.created_at).toLocaleDateString() : "—";

        return `<tr>
            <td style="color:var(--text-muted)">#${u.id}</td>
            <td><strong style="color:var(--text-primary)">${escapeHtml(u.email)}</strong></td>
            <td>${escapeHtml(u.name) || '<span style="color:var(--text-muted)">—</span>'}</td>
            <td>${statusBadge}</td>
            <td>${roleBadge}</td>
            <td style="color:var(--text-muted)">${joined}</td>
            <td style="text-align:center">${u.transaction_count}</td>
            <td style="text-align:center">${u.holding_count}</td>
            <td>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                    <button class="btn btn-ghost" style="padding:4px 10px;font-size:.75rem" onclick="viewUserDetail(${u.id})">👁 View</button>
                    <button class="btn btn-ghost" style="padding:4px 10px;font-size:.75rem" onclick="toggleUserActive(${u.id})">${isActive ? '🚫 Disable' : '✅ Enable'}</button>
                    <button class="btn btn-ghost" style="padding:4px 10px;font-size:.75rem" onclick="toggleUserAdmin(${u.id})">${isAdmin ? '👤 Demote' : '🛡️ Promote'}</button>
                    <button class="btn btn-ghost" style="padding:4px 10px;font-size:.75rem" onclick="openAdminResetPw(${u.id}, '${escapeHtml(u.email)}')">🔑 Reset PW</button>
                    <button class="btn btn-ghost" style="padding:4px 10px;font-size:.75rem;color:#ef4444" onclick="deleteUser(${u.id}, '${escapeHtml(u.email)}')">🗑️ Delete</button>
                </div>
            </td>
        </tr>`;
    }).join("");

    // Pagination
    const totalPages = Math.ceil(data.total / data.per_page);
    const pagDiv = document.getElementById("admin-pagination");
    if (totalPages <= 1) {
        pagDiv.innerHTML = "";
        return;
    }
    let btns = "";
    for (let i = 1; i <= totalPages; i++) {
        const active = i === page ? 'background:var(--accent);color:#fff;' : '';
        btns += `<button class="btn btn-ghost" style="padding:6px 12px;${active}" onclick="loadAdminUsers(${i})">${i}</button>`;
    }
    pagDiv.innerHTML = btns;
}

function searchAdminUsers() {
    clearTimeout(adminSearchTimeout);
    adminSearchTimeout = setTimeout(() => loadAdminUsers(1), 300);
}

// ── User Detail Modal ────────────────────────────────────────
async function viewUserDetail(userId) {
    const data = await api.get(`/api/admin/users/${userId}`);
    document.getElementById("admin-user-modal-title").textContent = `User #${data.id} — ${data.email}`;

    const isActive = data.is_active;
    const isAdmin = data.is_admin;

    document.getElementById("admin-user-modal-body").innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
            <div class="card" style="padding:12px"><span style="color:var(--text-muted);font-size:.8rem">Email</span><br><strong>${escapeHtml(data.email)}</strong></div>
            <div class="card" style="padding:12px"><span style="color:var(--text-muted);font-size:.8rem">Name</span><br><strong>${escapeHtml(data.name) || "—"}</strong></div>
            <div class="card" style="padding:12px"><span style="color:var(--text-muted);font-size:.8rem">Status</span><br><strong style="color:${isActive ? '#22c55e' : '#ef4444'}">${isActive ? 'Active' : 'Disabled'}</strong></div>
            <div class="card" style="padding:12px"><span style="color:var(--text-muted);font-size:.8rem">Role</span><br><strong style="color:${isAdmin ? '#f59e0b' : 'var(--text-primary)'}">${isAdmin ? 'Admin' : 'User'}</strong></div>
            <div class="card" style="padding:12px"><span style="color:var(--text-muted);font-size:.8rem">Joined</span><br><strong>${data.created_at ? new Date(data.created_at).toLocaleString() : "—"}</strong></div>
        </div>
        <h3 style="color:var(--text-primary);margin-bottom:12px">Activity</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px">
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.transactions}</div><div style="font-size:.75rem;color:var(--text-muted)">Transactions</div></div>
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.holdings}</div><div style="font-size:.75rem;color:var(--text-muted)">Holdings</div></div>
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.watchlist}</div><div style="font-size:.75rem;color:var(--text-muted)">Watchlist</div></div>
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.alerts}</div><div style="font-size:.75rem;color:var(--text-muted)">Alerts</div></div>
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.dca_plans}</div><div style="font-size:.75rem;color:var(--text-muted)">DCA Plans</div></div>
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.budgets}</div><div style="font-size:.75rem;color:var(--text-muted)">Budgets</div></div>
            <div class="card" style="padding:12px;text-align:center"><div style="font-size:1.5rem;font-weight:700">${data.risk_profiles}</div><div style="font-size:.75rem;color:var(--text-muted)">Risk Profiles</div></div>
        </div>
    `;
    document.getElementById("admin-user-modal").style.display = "flex";
}

// ── Toggle Actions ───────────────────────────────────────────
async function toggleUserActive(userId) {
    try {
        const res = await api.post("/api/admin/toggle-active", { user_id: userId });
        loadAdminUsers(adminCurrentPage);
        loadAdminStats();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function toggleUserAdmin(userId) {
    if (!confirm("Are you sure you want to change this user's admin status?")) return;
    try {
        await api.post("/api/admin/toggle-admin", { user_id: userId });
        loadAdminUsers(adminCurrentPage);
        loadAdminStats();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

// ── Reset Password ───────────────────────────────────────────
function openAdminResetPw(userId, email) {
    document.getElementById("admin-reset-user-id").value = userId;
    document.getElementById("admin-reset-email").textContent = email;
    document.getElementById("admin-reset-new-pw").value = "";
    document.getElementById("admin-reset-modal").style.display = "flex";
}

async function submitAdminResetPassword(e) {
    e.preventDefault();
    const userId = parseInt(document.getElementById("admin-reset-user-id").value);
    const newPw = document.getElementById("admin-reset-new-pw").value;
    try {
        await api.post("/api/admin/reset-password", { user_id: userId, new_password: newPw });
        document.getElementById("admin-reset-modal").style.display = "none";
        alert("Password reset successfully!");
    } catch (e) {
        alert("Error: " + e.message);
    }
}

// ── Delete User ──────────────────────────────────────────────
async function deleteUser(userId, email) {
    if (!confirm(`⚠️ PERMANENTLY delete ${email} and ALL their data?\n\nThis cannot be undone!`)) return;
    if (!confirm(`Final confirmation: Delete ${email}?`)) return;
    try {
        await api.del(`/api/admin/users/${userId}`);
        loadAdminUsers(adminCurrentPage);
        loadAdminStats();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

// ── Suggestions Management ───────────────────────────────────
let suggestionsCurrentPage = 1;

async function loadAdminSuggestions(page = 1) {
    suggestionsCurrentPage = page;
    const status = document.getElementById("admin-suggestion-filter")?.value || "";
    const params = new URLSearchParams({ page, per_page: 15 });
    if (status) params.set("status", status);

    try {
        const [data, stats] = await Promise.all([
            api.get(`/api/assistant/suggestions?${params}`),
            api.get("/api/assistant/suggestions/stats"),
        ]);

        // Stats badges
        const statsEl = document.getElementById("admin-suggestion-stats");
        if (statsEl) {
            statsEl.innerHTML = [
                { label: "New", val: stats.new, color: "#6366f1" },
                { label: "Planned", val: stats.planned, color: "#f59e0b" },
                { label: "Done", val: stats.done, color: "#22c55e" },
                { label: "Total", val: stats.total, color: "var(--text-muted)" },
            ].map(s => `<span style="font-size:.75rem;padding:2px 8px;border-radius:6px;background:${s.color}22;color:${s.color}">${s.val} ${s.label}</span>`).join("");
        }

        const list = document.getElementById("admin-suggestions-list");
        if (!data.items || data.items.length === 0) {
            list.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:32px">No suggestions found</div>`;
        } else {
            list.innerHTML = data.items.map(s => {
                const statusColors = {
                    new: "#6366f1", reviewed: "#3b82f6", planned: "#f59e0b",
                    done: "#22c55e", declined: "#ef4444"
                };
                const catIcons = { feature: "🚀", bug: "🐛", improvement: "✨", content: "📝" };
                const color = statusColors[s.status] || "var(--text-muted)";
                const date = s.created_at ? new Date(s.created_at).toLocaleDateString() : "—";

                return `<div class="card" style="padding:16px;border-left:4px solid ${color};cursor:pointer" onclick="viewSuggestionDetail(${s.id})">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
                        <div style="flex:1;min-width:0">
                            <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap">
                                <span style="font-size:1.1rem">${catIcons[s.category] || "💡"}</span>
                                <span style="font-weight:600;color:var(--text-primary)">${escapeHtml(s.message.slice(0, 120))}${s.message.length > 120 ? "..." : ""}</span>
                            </div>
                            <div style="display:flex;gap:12px;font-size:.8rem;color:var(--text-muted);flex-wrap:wrap">
                                <span>${escapeHtml(s.user_email || "Unknown")}</span>
                                <span>${date}</span>
                                <span>👍 ${s.votes}</span>
                                ${s.github_issue_url ? `<a href="${s.github_issue_url}" target="_blank" style="color:#6366f1;text-decoration:none" onclick="event.stopPropagation()">🔗 GitHub #${s.github_issue_number || ''}</a>` : ''}
                            </div>
                        </div>
                        <div style="display:flex;gap:6px;align-items:center;flex-shrink:0">
                            <span style="font-size:.75rem;padding:2px 10px;border-radius:6px;background:${color}22;color:${color};font-weight:600;text-transform:uppercase">${s.status}</span>
                        </div>
                    </div>
                    ${s.admin_notes ? `<div style="margin-top:8px;padding:8px 12px;background:rgba(255,255,255,.03);border-radius:6px;font-size:.85rem;color:var(--text-muted)">📝 ${escapeHtml(s.admin_notes)}</div>` : ""}
                </div>`;
            }).join("");
        }

        // Pagination
        const totalPages = Math.ceil(data.total / data.per_page);
        const pagDiv = document.getElementById("admin-suggestion-pagination");
        if (totalPages <= 1) { pagDiv.innerHTML = ""; return; }
        let btns = "";
        for (let i = 1; i <= totalPages; i++) {
            const active = i === page ? "background:var(--accent);color:#fff;" : "";
            btns += `<button class="btn btn-ghost" style="padding:6px 12px;${active}" onclick="loadAdminSuggestions(${i})">${i}</button>`;
        }
        pagDiv.innerHTML = btns;
    } catch (e) {
        const list = document.getElementById("admin-suggestions-list");
        if (list) list.innerHTML = `<div style="color:#ef4444;text-align:center;padding:20px">Failed to load suggestions: ${e.message}</div>`;
    }
}

async function viewSuggestionDetail(id) {
    try {
        // Fetch the full list and find the item (API doesn't have single GET)
        const data = await api.get(`/api/assistant/suggestions?per_page=100`);
        const s = data.items.find(i => i.id === id);
        if (!s) { alert("Suggestion not found"); return; }

        const statusColors = {
            new: "#6366f1", reviewed: "#3b82f6", planned: "#f59e0b",
            done: "#22c55e", declined: "#ef4444"
        };
        const catIcons = { feature: "🚀", bug: "🐛", improvement: "✨", content: "📝" };
        const date = s.created_at ? new Date(s.created_at).toLocaleString() : "—";

        document.getElementById("admin-suggestion-modal-title").textContent = `${catIcons[s.category] || "💡"} Suggestion #${s.id}`;
        document.getElementById("admin-suggestion-modal-body").innerHTML = `
            <div class="card" style="padding:16px;margin-bottom:16px;background:rgba(255,255,255,.02)">
                <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:8px">From: <strong>${escapeHtml(s.user_email || "Unknown")}</strong> · ${date} · 👍 ${s.votes} votes</div>
                <div style="color:var(--text-primary);line-height:1.5">${escapeHtml(s.message)}</div>
                ${s.github_issue_url ? `<div style="margin-top:10px"><a href="${s.github_issue_url}" target="_blank" style="color:#6366f1;font-size:.85rem;text-decoration:none">🔗 View GitHub Issue #${s.github_issue_number || ''}</a></div>` : '<div style="margin-top:10px;font-size:.8rem;color:var(--text-muted)">⚠️ No GitHub Issue (submitted before integration)</div>'}
            </div>

            <div style="margin-bottom:16px">
                <label style="font-size:.85rem;color:var(--text-muted);display:block;margin-bottom:4px">Status</label>
                <select id="suggestion-status-select" style="padding:8px 14px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:var(--card-bg);color:var(--text-primary);width:100%">
                    ${["new","reviewed","planned","done","declined"].map(st =>
                        `<option value="${st}" ${st === s.status ? "selected" : ""}>${st.charAt(0).toUpperCase() + st.slice(1)}</option>`
                    ).join("")}
                </select>
            </div>

            <div style="margin-bottom:16px">
                <label style="font-size:.85rem;color:var(--text-muted);display:block;margin-bottom:4px">Admin Notes</label>
                <textarea id="suggestion-admin-notes" rows="3" style="width:100%;padding:8px 14px;border-radius:8px;border:1px solid rgba(255,255,255,.1);background:var(--card-bg);color:var(--text-primary);resize:vertical">${escapeHtml(s.admin_notes || "")}</textarea>
            </div>

            <div class="form-actions">
                <button class="btn btn-ghost" onclick="document.getElementById('admin-suggestion-modal').style.display='none'">Cancel</button>
                <button class="btn btn-primary" onclick="updateSuggestionStatus(${s.id})">💾 Save</button>
            </div>
        `;
        document.getElementById("admin-suggestion-modal").style.display = "flex";
    } catch (e) {
        alert("Error loading suggestion: " + e.message);
    }
}

async function updateSuggestionStatus(id) {
    const status = document.getElementById("suggestion-status-select").value;
    const admin_notes = document.getElementById("suggestion-admin-notes").value;
    try {
        await api.put(`/api/assistant/suggestions/${id}`, { status, admin_notes });
        document.getElementById("admin-suggestion-modal").style.display = "none";
        loadAdminSuggestions(suggestionsCurrentPage);
    } catch (e) {
        alert("Error updating suggestion: " + e.message);
    }
}

// ── Helper ───────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}
