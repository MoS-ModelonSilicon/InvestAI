const api = (() => {
    function _checkAuth(res) {
        if (res.status === 401) {
            window.location.href = "/login";
            throw new Error("Session expired");
        }
    }
    return {
        async get(url) {
            const res = await fetch(url);
            _checkAuth(res);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        },
        async post(url, data) {
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            _checkAuth(res);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        },
        async put(url, data) {
            const res = await fetch(url, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            _checkAuth(res);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        },
        async del(url) {
            const res = await fetch(url, { method: "DELETE" });
            _checkAuth(res);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        },
        async delBulk(url, data) {
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            _checkAuth(res);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        },
    };
})();

const fmt = (n) =>
    "$" + Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const fmtPct = (n) => (n != null ? n.toFixed(1) + "%" : "—");

// ── Page Search Utilities ────────────────────────────────────
function clearPageSearch(inputId, filterFn) {
    const el = document.getElementById(inputId);
    if (el) { el.value = ""; }
    if (typeof filterFn === "function") filterFn("");
}
