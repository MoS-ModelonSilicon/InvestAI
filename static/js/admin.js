// ── Admin Panel ──────────────────────────────────────────────
let adminCurrentPage = 1;
let adminSearchTimeout = null;

async function loadAdminPanel() {
    try {
        await Promise.all([loadAdminStats(), loadAdminUsers()]);
    } catch (e) {
        console.error("Admin load error:", e);
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

// ── Helper ───────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}
