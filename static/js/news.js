let _newsArticles = [];

async function loadNews() {
    const container = document.getElementById("news-container");
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading market news...</p></div>';

    try {
        const articles = await api.get("/api/news");
        _newsArticles = articles;
        renderNews(articles);
    } catch (e) {
        container.innerHTML = '<p style="color:var(--red);padding:20px;">Failed to load news.</p>';
    }
}

function renderNews(articles) {
    const container = document.getElementById("news-container");
    const count = document.getElementById("news-count");
    if (count) count.textContent = `${articles.length} articles`;

    if (articles.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No news available. Add stocks to your watchlist or portfolio to get personalized news.</p></div>';
        return;
    }

    let html = '<div class="news-list">';
    articles.forEach(article => {
        const date = article.published ? new Date(article.published * 1000) : null;
        const timeAgo = date ? getTimeAgo(date) : "";
        const thumb = article.thumbnail ? `<div class="news-thumb" style="background-image:url(${article.thumbnail})"></div>` : "";
        const symbolAttr = article.symbol ? ` data-symbol="${article.symbol}" data-stock-name="${article.symbol}"` : "";

        html += `
        <a href="${article.link}" target="_blank" class="news-card"${symbolAttr}>
            ${thumb}
            <div class="news-body">
                <div class="news-title">${article.title}</div>
                ${article.summary ? `<div class="news-summary">${article.summary}</div>` : ""}
                <div class="news-meta">
                    ${article.symbol ? `<span class="news-symbol">${article.symbol}</span>` : ""}
                    <span>${article.publisher}</span>
                    <span>${timeAgo}</span>
                </div>
            </div>
        </a>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function getTimeAgo(date) {
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return date.toLocaleDateString();
}

function filterNews(query) {
    const q = (query || "").toLowerCase().trim();
    const cards = document.querySelectorAll(".news-card");
    let visible = 0;
    cards.forEach(card => {
        const title = (card.querySelector(".news-title")?.textContent || "").toLowerCase();
        const symbol = (card.dataset.symbol || "").toLowerCase();
        const publisher = (card.querySelector(".news-meta")?.textContent || "").toLowerCase();
        const match = !q || title.includes(q) || symbol.includes(q) || publisher.includes(q);
        card.style.display = match ? "" : "none";
        if (match) visible++;
    });
    let noRes = document.getElementById("news-no-results");
    if (!q || visible > 0) {
        if (noRes) noRes.remove();
    } else {
        if (!noRes) {
            noRes = document.createElement("div");
            noRes.id = "news-no-results";
            noRes.className = "search-no-results";
            const container = document.getElementById("news-container");
            if (container) container.appendChild(noRes);
        }
        noRes.textContent = `No articles matching "${query}"`;
    }
}
