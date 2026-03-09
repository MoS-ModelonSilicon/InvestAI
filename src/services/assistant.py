"""
AI Assistant service — two-tier model routing with tool calling.

Small model (gpt-5-nano): classification + simple Q&A (site nav, FAQ, greetings)
Large model (o3): financial reasoning, stock analysis, portfolio advice

Both models are prompted for SHORT, DIRECT answers — no fluff.
"""

import json
import logging
import os
import time
from typing import Generator

import requests

logger = logging.getLogger(__name__)

# ── Azure OpenAI config ──────────────────────────────────────
_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Model deployment names — override via env if needed
SMALL_MODEL = os.environ.get("ASSISTANT_SMALL_MODEL", "gpt-5-nano")
LARGE_MODEL = os.environ.get("ASSISTANT_LARGE_MODEL", "o3")

# Proxy config (Intel network → use proxy; Render/CI → no proxy)
_PROXIES = {}
_http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
_https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
if _http_proxy:
    _PROXIES["http"] = _http_proxy
if _https_proxy:
    _PROXIES["https"] = _https_proxy

# Auto-detect Intel network when no explicit proxy env vars set
if not _PROXIES and not (os.environ.get("RENDER") or os.environ.get("CI")):
    import socket
    try:
        socket.getaddrinfo("proxy-dmz.intel.com", 911, socket.AF_INET, socket.SOCK_STREAM)
        _PROXIES = {
            "http": "http://proxy-dmz.intel.com:911",
            "https": "http://proxy-dmz.intel.com:912",
        }
    except (socket.gaierror, OSError):
        pass  # not on Intel network


def _is_configured() -> bool:
    return bool(_ENDPOINT and _API_KEY)


# ── Site knowledge (baked into system prompt) ─────────────────

SITE_KNOWLEDGE = """
You are InvestAI Assistant — a helpful, concise AI built into the InvestAI investment platform.

## RESPONSE RULES (CRITICAL — FOLLOW EXACTLY)
- Be EXTREMELY concise. Max 2-3 sentences for simple questions.
- For stock analysis: give the key number + one-line verdict. Example: "NVDA trades at 35x forward P/E with 60% YoY revenue growth. Reasonably priced for the growth rate."
- Never say "I'd be happy to help" or "Great question" — just answer.
- Use bullet points for lists, not paragraphs.
- If you don't know something, say so in one sentence.
- Numbers > words. Give price, P/E, % change — not vague descriptions.
- If the user asks about a feature that doesn't exist on InvestAI, offer to log it as a suggestion. Call the submit_suggestion tool.

## ABOUT INVESTAI
InvestAI is a full-stack investment advisory web app. Key features:

**Portfolio & Tracking:**
- Portfolio Tracker — virtual holdings with real-time P&L, sector allocation, S&P 500 benchmark
- Watchlist — bookmark stocks with live price cards
- Price Alerts — above/below triggers with bell notifications
- DCA Planner — dollar-cost averaging with auto dip detection

**Discover & Research:**
- Stock Screener — 280+ global stocks across 12 regions, 10 filter dimensions, quick presets
- Stock Detail — full company overview, interactive charts, analyst targets, risk analysis, news
- AI Picks (Autopilot) — choose strategy + amount, backtest vs S&P 500, one-click add to portfolio
- Smart Advisor — Berkshire-style long-term analysis with Company DNA deep-dives
- Trading Advisor — short-term picks with entry/target/stop, R/R ratios
- Value Scanner — Graham-Buffett quality scores with action plans
- IL Funds — Israeli mutual fund screener (481 live funds from funder.co.il)

**Finance Tracking:**
- Transactions — income/expense with filtering and categories
- Budgets — monthly limits per category with progress bars
- Dashboard — financial overview with trend charts

**Design Decisions:**
- Vanilla JS frontend (no React/Vue) — zero build step, simple deployment
- FastAPI + SQLAlchemy backend with PostgreSQL (prod) / SQLite (local)
- Market data: Finnhub (primary, 60 calls/min) with Yahoo Finance fallback
- Cookie-based JWT auth (httponly, secure, samesite=lax)
- Background cache warmer pre-fetches all data every 15 min for instant screener
- 12 global regions: US, China/HK, Japan, Europe, India, Israel, etc.

**Navigation Tips:**
- Right-click any stock symbol for a context menu (view detail, add to watchlist, set alert)
- Use Quick Presets in Screener for instant filtered views (Value Stocks, High Dividend, etc.)
- Complete Risk Profile to unlock Personalized Recommendations
- The sidebar groups features: My Portfolio → Discover → Track & Learn → Money
"""

CLASSIFICATION_PROMPT = """Classify this user message into exactly one category. Reply with ONLY the category word.

SIMPLE — greetings, small talk, site navigation, FAQ, feature explanations, how-to questions
COMPLEX — stock analysis, portfolio advice, market opinions, financial calculations, comparing investments, risk assessment, anything requiring data lookup or reasoning
SUGGESTION — user is requesting a feature, reporting a bug, or suggesting an improvement

Reply with one word: SIMPLE, COMPLEX, or SUGGESTION"""


CONCISE_INSTRUCTION = """
CRITICAL: Keep responses SHORT and DIRECT.
- Simple questions: 1-2 sentences max.
- Stock analysis: key metrics + one-line verdict. No essays.
- Lists: bullet points, not paragraphs.
- Never repeat the question back. Never say "certainly" or "of course".
- If you use a tool, summarize the result in 1-2 sentences.
"""

# ── Tool definitions ──────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Get live price, P/E, market cap, and daily change for a stock symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL, NVDA)"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_screener",
            "description": "Search/filter stocks by sector, region, market cap, P/E, dividend yield, or text query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text search (symbol or company name)"},
                    "sector": {"type": "string", "description": "Sector filter (Technology, Healthcare, etc.)"},
                    "region": {"type": "string", "description": "Region filter (US, Europe, Israel, etc.)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_suggestion",
            "description": "Log a user's feature request, bug report, or improvement suggestion. Call this when the user asks for something that doesn't exist on the site.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "One-line summary of the feature request or suggestion",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["feature", "bug", "improvement", "content"],
                        "description": "Type of suggestion",
                    },
                },
                "required": ["summary", "category"],
            },
        },
    },
]


# ── Tool execution ────────────────────────────────────────────


def execute_tool(tool_name: str, args: dict, user_id: int | None = None) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if tool_name == "get_stock_quote":
            return _tool_stock_quote(args.get("symbol", ""))
        elif tool_name == "search_screener":
            return _tool_search_screener(args)
        elif tool_name == "submit_suggestion":
            return _tool_submit_suggestion(args, user_id)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.exception("Tool execution failed: %s", tool_name)
        return json.dumps({"error": str(e)})


def _tool_stock_quote(symbol: str) -> str:
    from src.services.stock_detail import get_stock_detail

    symbol = symbol.upper().strip()
    info = get_stock_detail(symbol)
    if not info:
        return json.dumps({"error": f"No data for {symbol}"})
    # Return only the key fields the AI needs
    return json.dumps(
        {
            "symbol": symbol,
            "name": info.get("name", ""),
            "price": info.get("price"),
            "change_pct": info.get("change_pct"),
            "market_cap_fmt": info.get("market_cap_fmt", ""),
            "pe_ratio": info.get("pe_ratio"),
            "forward_pe": info.get("forward_pe"),
            "dividend_yield": info.get("dividend_yield"),
            "beta": info.get("beta"),
            "sector": info.get("sector", ""),
            "52w_high": info.get("week52_high"),
            "52w_low": info.get("week52_low"),
            "recommendation": info.get("recommendation", ""),
        }
    )


def _tool_search_screener(args: dict) -> str:
    from src.services.screener import screen_instruments

    results = screen_instruments(
        query=args.get("query"),
        sector=args.get("sector"),
        region=args.get("region"),
    )
    # Return top 5 to keep response short
    top = results[:5]
    summary = [
        {
            "symbol": r.get("symbol"),
            "name": r.get("name"),
            "price": r.get("price"),
            "pe": r.get("pe_ratio"),
            "sector": r.get("sector"),
            "signal": r.get("signal", ""),
        }
        for r in top
    ]
    return json.dumps({"count": len(results), "top_5": summary})


def _tool_submit_suggestion(args: dict, user_id: int | None) -> str:
    """Save a suggestion to the database."""
    from sqlalchemy.orm import Session as _Session

    from src.database import SessionLocal
    from src.models import Suggestion

    summary = args.get("summary", "").strip()
    category = args.get("category", "feature")
    if not summary:
        return json.dumps({"error": "Empty suggestion"})

    try:
        db: _Session = SessionLocal()
        suggestion = Suggestion(
            user_id=user_id or 0,
            message=summary,
            ai_summary=summary,
            category=category,
            status="new",
        )
        db.add(suggestion)
        db.commit()
        db.close()
        return json.dumps({"success": True, "message": "Suggestion logged successfully"})
    except Exception as e:
        logger.exception("Failed to save suggestion")
        return json.dumps({"error": str(e)})


# ── Model classification ──────────────────────────────────────


def classify_message(message: str) -> str:
    """Use the small model to classify a message as SIMPLE, COMPLEX, or SUGGESTION."""
    if not _is_configured():
        return "SIMPLE"

    try:
        url = f"{_ENDPOINT}/openai/deployments/{SMALL_MODEL}/chat/completions?api-version={_API_VERSION}"
        payload = {
            "messages": [
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": message},
            ],
            "max_completion_tokens": 500,
        }
        resp = requests.post(
            url,
            headers={"api-key": _API_KEY, "Content-Type": "application/json"},
            json=payload,
            proxies=_PROXIES,
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
        text = result["choices"][0]["message"]["content"].strip().upper()
        if "COMPLEX" in text:
            return "COMPLEX"
        if "SUGGESTION" in text:
            return "SUGGESTION"
        return "SIMPLE"
    except Exception as e:
        logger.warning("Classification failed, defaulting to SIMPLE: %s", e)
        return "SIMPLE"


# ── Chat completion (streaming) ───────────────────────────────


def chat_stream(
    messages: list[dict],
    user_id: int | None = None,
) -> Generator[str, None, None]:
    """
    Stream a chat response. Handles model routing + tool calls.
    Yields SSE-formatted strings: 'data: {...}\n\n'
    """
    if not _is_configured():
        yield _sse({"type": "error", "content": "AI assistant not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables."})
        yield _sse({"type": "done"})
        return

    # Get the last user message for classification
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    # Classify to pick model
    category = classify_message(last_user_msg)
    model = LARGE_MODEL if category == "COMPLEX" else SMALL_MODEL

    yield _sse({"type": "model", "model": model, "category": category})

    # Build system prompt
    system_msg = SITE_KNOWLEDGE + "\n" + CONCISE_INSTRUCTION

    full_messages = [{"role": "system", "content": system_msg}] + messages

    # First call — may include tool calls
    response_message = _call_model(model, full_messages, use_tools=True)
    if response_message is None:
        yield _sse({"type": "error", "content": "Failed to get AI response. Please try again."})
        yield _sse({"type": "done"})
        return

    # Handle tool calls (one round of tool use)
    if response_message.get("tool_calls"):
        tool_results = []
        for tc in response_message["tool_calls"]:
            fn = tc["function"]
            tool_name = fn["name"]
            try:
                tool_args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                tool_args = {}

            yield _sse({"type": "tool", "name": tool_name, "args": tool_args})

            result = execute_tool(tool_name, tool_args, user_id)
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                }
            )

        # Second call with tool results — stream the final answer
        full_messages.append(response_message)
        full_messages.extend(tool_results)
        yield from _stream_response(model, full_messages)
    else:
        # No tool calls — stream the content directly
        content = response_message.get("content", "")
        if content:
            yield _sse({"type": "text", "content": content})

    yield _sse({"type": "done"})


def _call_model(model: str, messages: list[dict], use_tools: bool = False) -> dict | None:
    """Non-streaming call to get tool decisions."""
    url = f"{_ENDPOINT}/openai/deployments/{model}/chat/completions?api-version={_API_VERSION}"
    payload: dict = {
        "messages": messages,
        "max_completion_tokens": 2000,
    }
    if use_tools:
        payload["tools"] = TOOLS
        payload["tool_choice"] = "auto"

    try:
        resp = requests.post(
            url,
            headers={"api-key": _API_KEY, "Content-Type": "application/json"},
            json=payload,
            proxies=_PROXIES,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]
    except Exception as e:
        logger.exception("Model call failed (%s): %s", model, e)
        return None


def _stream_response(model: str, messages: list[dict]) -> Generator[str, None, None]:
    """Stream the final text response from the model."""
    url = f"{_ENDPOINT}/openai/deployments/{model}/chat/completions?api-version={_API_VERSION}"
    payload: dict = {
        "messages": messages,
        "max_completion_tokens": 2000,
        "stream": True,
    }

    try:
        resp = requests.post(
            url,
            headers={"api-key": _API_KEY, "Content-Type": "application/json"},
            json=payload,
            proxies=_PROXIES,
            timeout=60,
            stream=True,
        )
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                choices = chunk.get("choices", [])
                if not choices:
                    continue  # usage-only chunk at end of stream
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield _sse({"type": "text", "content": content})
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.exception("Stream failed (%s): %s", model, e)
        yield _sse({"type": "error", "content": "Stream interrupted. Please try again."})


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
