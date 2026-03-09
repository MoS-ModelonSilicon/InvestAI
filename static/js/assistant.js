/* ── AI Chat Widget ────────────────────────────────────────────
 *  Floating chat bubble with:
 *  1. Two-tier AI (nano for simple, o3 for complex)
 *  2. SSE streaming responses
 *  3. Built-in suggestion submission
 *  4. Tool call indicators
 *  5. Markdown-lite rendering (bold, bullets, code)
 * ──────────────────────────────────────────────────────────── */
(function () {
    "use strict";

    const MAX_HISTORY = 20; // keep last N messages for context
    let chatHistory = [];
    let isOpen = false;
    let isStreaming = false;
    let suggestionMode = false;

    // ── Create DOM ────────────────────────────────────────────

    function createWidget() {
        // Floating button
        const fab = document.createElement("button");
        fab.id = "ai-chat-fab";
        fab.title = "Ask InvestAI Assistant";
        fab.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
        document.body.appendChild(fab);

        // Chat panel
        const panel = document.createElement("div");
        panel.id = "ai-chat-panel";
        panel.innerHTML = `
            <div class="ai-chat-header">
                <div class="ai-chat-header-left">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10H12V2z"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
                    <span>InvestAI Assistant</span>
                    <span class="ai-chat-model-badge" id="ai-chat-model"></span>
                </div>
                <div class="ai-chat-header-right">
                    <button class="ai-chat-suggest-btn" id="ai-chat-suggest-toggle" title="Submit a suggestion">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                    </button>
                    <button class="ai-chat-close-btn" id="ai-chat-close" title="Close">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>
            </div>
            <div class="ai-chat-messages" id="ai-chat-messages">
                <div class="ai-msg ai-msg-assistant">
                    <div class="ai-msg-content">Hi! I'm the InvestAI assistant. Ask me about stocks, the site features, or anything investment-related. I can also look up live prices for you.</div>
                </div>
            </div>
            <div class="ai-chat-suggestion-form" id="ai-chat-suggestion-form" style="display:none">
                <div class="ai-suggest-label">💡 Submit a Suggestion</div>
                <textarea id="ai-suggest-text" placeholder="Describe the feature, bug, or improvement..." rows="3" maxlength="2000"></textarea>
                <div class="ai-suggest-row">
                    <select id="ai-suggest-category">
                        <option value="feature">Feature Request</option>
                        <option value="improvement">Improvement</option>
                        <option value="bug">Bug Report</option>
                        <option value="content">Content Idea</option>
                    </select>
                    <button id="ai-suggest-submit" class="ai-suggest-submit-btn">Submit</button>
                    <button id="ai-suggest-cancel" class="ai-suggest-cancel-btn">Cancel</button>
                </div>
            </div>
            <div class="ai-chat-input-row" id="ai-chat-input-row">
                <input type="text" id="ai-chat-input" placeholder="Ask anything..." autocomplete="off" maxlength="1000" />
                <button id="ai-chat-send" title="Send">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
            </div>
        `;
        document.body.appendChild(panel);

        // Events
        fab.addEventListener("click", toggleChat);
        document.getElementById("ai-chat-close").addEventListener("click", toggleChat);
        document.getElementById("ai-chat-send").addEventListener("click", sendMessage);
        document.getElementById("ai-chat-input").addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        document.getElementById("ai-chat-suggest-toggle").addEventListener("click", toggleSuggestion);
        document.getElementById("ai-chat-suggest-submit").addEventListener("click", submitSuggestion);
        document.getElementById("ai-chat-suggest-cancel").addEventListener("click", toggleSuggestion);
    }

    function toggleChat() {
        isOpen = !isOpen;
        const panel = document.getElementById("ai-chat-panel");
        const fab = document.getElementById("ai-chat-fab");
        panel.classList.toggle("open", isOpen);
        fab.classList.toggle("active", isOpen);
        if (isOpen) {
            document.getElementById("ai-chat-input").focus();
        }
    }

    function toggleSuggestion() {
        suggestionMode = !suggestionMode;
        document.getElementById("ai-chat-suggestion-form").style.display = suggestionMode ? "block" : "none";
        document.getElementById("ai-chat-input-row").style.display = suggestionMode ? "none" : "flex";
        if (suggestionMode) {
            document.getElementById("ai-suggest-text").focus();
        }
    }

    // ── Send message ──────────────────────────────────────────

    async function sendMessage() {
        if (isStreaming) return;

        const input = document.getElementById("ai-chat-input");
        const text = input.value.trim();
        if (!text) return;

        input.value = "";

        // Add user message to UI & history
        appendMessage("user", text);
        chatHistory.push({ role: "user", content: text });

        // Trim history to last N
        if (chatHistory.length > MAX_HISTORY) {
            chatHistory = chatHistory.slice(-MAX_HISTORY);
        }

        // Create assistant placeholder
        const assistantEl = appendMessage("assistant", "");
        const contentEl = assistantEl.querySelector(".ai-msg-content");

        isStreaming = true;
        setSendEnabled(false);

        try {
            const response = await fetch("/api/assistant/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ messages: chatHistory }),
            });

            if (response.status === 401) {
                window.location.href = "/login";
                return;
            }

            if (!response.ok) {
                contentEl.textContent = "Sorry, something went wrong. Please try again.";
                isStreaming = false;
                setSendEnabled(true);
                return;
            }

            // Read SSE stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let fullText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    const jsonStr = line.slice(6);
                    try {
                        const event = JSON.parse(jsonStr);
                        switch (event.type) {
                            case "text":
                                fullText += event.content;
                                contentEl.innerHTML = renderMarkdown(fullText);
                                scrollToBottom();
                                break;
                            case "model":
                                showModelBadge(event.model, event.category);
                                break;
                            case "tool":
                                showToolIndicator(contentEl, event.name, event.args);
                                break;
                            case "error":
                                contentEl.textContent = event.content;
                                break;
                            case "done":
                                break;
                        }
                    } catch (e) {
                        // ignore parse errors
                    }
                }
            }

            // Save assistant response to history
            if (fullText) {
                chatHistory.push({ role: "assistant", content: fullText });
            }
        } catch (err) {
            contentEl.textContent = "Connection error. Please try again.";
        }

        isStreaming = false;
        setSendEnabled(true);
    }

    // ── Submit suggestion ──────────────────────────────────────

    async function submitSuggestion() {
        const text = document.getElementById("ai-suggest-text").value.trim();
        const category = document.getElementById("ai-suggest-category").value;
        if (!text) return;

        try {
            const res = await fetch("/api/assistant/suggest", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, category }),
            });
            if (res.ok) {
                appendMessage("assistant", "✅ Suggestion submitted! The team will review it. Thank you!");
                document.getElementById("ai-suggest-text").value = "";
                toggleSuggestion();
            } else {
                appendMessage("assistant", "❌ Failed to submit suggestion. Please try again.");
            }
        } catch (err) {
            appendMessage("assistant", "❌ Connection error. Please try again.");
        }
    }

    // ── UI helpers ────────────────────────────────────────────

    function appendMessage(role, content) {
        const container = document.getElementById("ai-chat-messages");
        const div = document.createElement("div");
        div.className = `ai-msg ai-msg-${role}`;
        const inner = document.createElement("div");
        inner.className = "ai-msg-content";
        if (content) {
            inner.innerHTML = role === "assistant" ? renderMarkdown(content) : escapeHtml(content);
        }
        div.appendChild(inner);
        container.appendChild(div);
        scrollToBottom();
        return div;
    }

    function showModelBadge(model, category) {
        const badge = document.getElementById("ai-chat-model");
        const isReasoning = model.includes("o3") || model.includes("o1");
        badge.textContent = isReasoning ? "🧠 Reasoning" : "⚡ Fast";
        badge.className = "ai-chat-model-badge " + (isReasoning ? "reasoning" : "fast");
        badge.title = `Model: ${model} | Category: ${category}`;
    }

    function showToolIndicator(contentEl, toolName, args) {
        const toolDiv = document.createElement("div");
        toolDiv.className = "ai-tool-indicator";
        const labels = {
            get_stock_quote: `Looking up ${args.symbol || "stock"}...`,
            search_screener: `Searching stocks${args.query ? ": " + args.query : ""}...`,
            submit_suggestion: "Logging your suggestion...",
        };
        toolDiv.textContent = "🔧 " + (labels[toolName] || `Using ${toolName}...`);
        contentEl.appendChild(toolDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        const container = document.getElementById("ai-chat-messages");
        container.scrollTop = container.scrollHeight;
    }

    function setSendEnabled(enabled) {
        const btn = document.getElementById("ai-chat-send");
        const input = document.getElementById("ai-chat-input");
        btn.disabled = !enabled;
        input.disabled = !enabled;
        if (enabled) input.focus();
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function renderMarkdown(text) {
        // Simple markdown: bold, bullets, inline code, line breaks
        let html = escapeHtml(text);
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        // Inline code
        html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
        // Bullet points (lines starting with - or *)
        html = html.replace(/^[-*] (.+)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");
        // Line breaks
        html = html.replace(/\n/g, "<br>");
        // Clean up double br in lists
        html = html.replace(/<ul><br>/g, "<ul>");
        html = html.replace(/<br><\/ul>/g, "</ul>");
        return html;
    }

    // ── Init ──────────────────────────────────────────────────
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createWidget);
    } else {
        createWidget();
    }
})();
