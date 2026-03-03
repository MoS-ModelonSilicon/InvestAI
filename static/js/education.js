let eduData = null;
let currentCategory = "all";

async function loadEducation() {
    const container = document.getElementById("edu-container");
    if (eduData) {
        renderEducation();
        return;
    }

    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading articles...</p></div>';

    try {
        eduData = await api.get("/api/education");
        renderEducation();
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load education content.</p>';
    }
}

function renderEducation() {
    const container = document.getElementById("edu-container");

    let html = `<div class="edu-tabs">
        <button class="edu-tab ${currentCategory === "all" ? "active" : ""}" onclick="filterEdu('all', this)">All</button>`;
    eduData.categories.forEach(cat => {
        html += `<button class="edu-tab ${currentCategory === cat ? "active" : ""}" onclick="filterEdu('${cat}', this)">${cat}</button>`;
    });
    html += `</div>`;

    const levels = { Beginner: "🟢", Intermediate: "🟡", Advanced: "🔴" };

    html += `<div class="edu-grid">`;
    eduData.articles.forEach(article => {
        const show = currentCategory === "all" || article.category === currentCategory;
        html += `
        <div class="edu-card" data-category="${article.category}" style="${show ? "" : "display:none"}">
            <div class="edu-card-header">
                <span class="edu-icon">${article.icon}</span>
                <span class="edu-level">${levels[article.level] || ""} ${article.level}</span>
            </div>
            <div class="edu-card-title">${article.title}</div>
            <div class="edu-card-summary">${article.summary}</div>
            <button class="btn btn-sm" onclick="toggleEduContent(this)">Read More ▾</button>
            <div class="edu-full-content" style="display:none;">
                ${article.content.map(p => `<p>${p}</p>`).join("")}
            </div>
        </div>`;
    });
    html += `</div>`;

    container.innerHTML = html;
}

function filterEdu(category, btn) {
    currentCategory = category;
    document.querySelectorAll(".edu-tab").forEach(t => t.classList.remove("active"));
    if (btn) btn.classList.add("active");
    document.querySelectorAll(".edu-card").forEach(card => {
        const cat = card.dataset.category;
        card.style.display = (category === "all" || cat === category) ? "" : "none";
    });
}

function toggleEduContent(btn) {
    const content = btn.nextElementSibling;
    if (content.style.display === "none") {
        content.style.display = "block";
        btn.textContent = "Show Less ▴";
    } else {
        content.style.display = "none";
        btn.textContent = "Read More ▾";
    }
}
