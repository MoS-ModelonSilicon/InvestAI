"""
AI Assistant service — two-tier model routing with tool calling.

Small model (gpt-5-nano): classification + simple Q&A (site nav, FAQ, greetings)
Large model (o3): financial reasoning, stock analysis, portfolio advice

Both models are prompted for SHORT, DIRECT answers — no fluff.
"""

import json
import logging
import os
from collections.abc import Generator

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

## YOUR CAPABILITIES (Tools you can use)
You have WRITE access — you can take actions on behalf of the user:
- **add_to_portfolio** — add stock holdings ("buy 10 shares of AAPL at $150")
- **add_to_watchlist** / **remove_from_watchlist** — manage watchlist
- **create_alert** — set price alerts ("alert me when NVDA drops below $100")
- **add_transaction** — record income/expenses ("I spent $50 on groceries")
- **navigate_to** — open any page ("show me my portfolio", "go to screener")

You have READ access — you can fetch user data:
- **get_my_portfolio** — portfolio holdings + P&L
- **get_my_watchlist** — tracked stocks
- **get_my_alerts** — price alerts
- **get_dashboard_summary** — financial overview
- **get_my_budgets** — budget status

You have ANALYSIS tools:
- **get_stock_quote** — live stock data
- **search_screener** — search/filter stocks
- **get_ai_picks** — AI strategy profiles
- **get_trading_signals** — technical analysis with entry/target/stop

When the user asks to DO something (buy, add, watch, alert, log expense), USE the appropriate tool — don't just describe how to do it.

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

SIMPLE — greetings, small talk, FAQ, feature explanations, how-to questions
ACTION — user wants to DO something: buy/sell stock, add to portfolio/watchlist, set alert, log expense/income, navigate to a page, show their data
COMPLEX — stock analysis, portfolio advice, market opinions, financial calculations, comparing investments, risk assessment, anything requiring data lookup or reasoning
SUGGESTION — user is requesting a feature, reporting a bug, or suggesting an improvement

Reply with one word: SIMPLE, ACTION, COMPLEX, or SUGGESTION"""


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
                "properties": {"symbol": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL, NVDA)"}},
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
    # ── Write tools ───────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "add_to_portfolio",
            "description": "Add a stock holding to the user's portfolio. Use when the user says 'buy', 'add to portfolio', or 'I bought X shares of Y'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL)"},
                    "quantity": {"type": "number", "description": "Number of shares"},
                    "buy_price": {"type": "number", "description": "Purchase price per share in USD"},
                    "buy_date": {
                        "type": "string",
                        "description": "Purchase date (YYYY-MM-DD). Defaults to today if not specified.",
                    },
                    "notes": {"type": "string", "description": "Optional notes about this position"},
                },
                "required": ["symbol", "quantity", "buy_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_watchlist",
            "description": "Add a stock to the user's watchlist for tracking. Use when the user says 'watch', 'track', or 'add to watchlist'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL)"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_watchlist",
            "description": "Remove a stock from the user's watchlist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol to remove"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_alert",
            "description": "Create a price alert for a stock. Triggers when price goes above or below a target. Use when the user says 'alert me', 'notify me', 'tell me when'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol"},
                    "condition": {
                        "type": "string",
                        "enum": ["above", "below"],
                        "description": "Trigger when price is above or below target",
                    },
                    "target_price": {"type": "number", "description": "Target price in USD"},
                },
                "required": ["symbol", "condition", "target_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": "Record an income or expense transaction. Use when the user says 'I spent', 'I earned', 'log expense', 'add income'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount in USD (positive number)"},
                    "type": {
                        "type": "string",
                        "enum": ["income", "expense"],
                        "description": "Transaction type",
                    },
                    "description": {"type": "string", "description": "What the transaction is for"},
                    "date": {
                        "type": "string",
                        "description": "Transaction date (YYYY-MM-DD). Defaults to today.",
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Category name (e.g. Food, Salary, Transport, Entertainment, Shopping, Health, Bills, Other)",
                    },
                },
                "required": ["amount", "type", "description"],
            },
        },
    },
    # ── Read tools ────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_my_portfolio",
            "description": "Get the user's portfolio summary including holdings, total value, P&L, and sector allocation.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_watchlist",
            "description": "Get the user's watchlist of tracked stocks.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_alerts",
            "description": "Get the user's price alerts.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Get the user's financial dashboard: income, expenses, net balance, budget status, and category breakdown.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_budgets",
            "description": "Get the user's budget status: limits vs actual spending per category this month.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── Navigation tool ───────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "navigate_to",
            "description": "Navigate the user to a specific page in the app. Use when the user asks 'show me', 'go to', 'open', or 'take me to' a page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "enum": [
                            "dashboard",
                            "portfolio",
                            "watchlist",
                            "dca",
                            "alerts",
                            "screener",
                            "autopilot",
                            "smart-advisor",
                            "il-funds",
                            "news",
                            "calendar",
                            "picks-tracker",
                            "education",
                            "profile",
                            "transactions",
                            "budgets",
                        ],
                        "description": "Page name to navigate to",
                    },
                },
                "required": ["page"],
            },
        },
    },
    # ── AI analysis tools ─────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_ai_picks",
            "description": "Get AI-powered investment strategy profiles (Autopilot): Daredevil (aggressive), Strategist (balanced), Fortress (conservative). Shows expected returns, risk levels, and stock allocations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "string",
                        "enum": ["daredevil", "strategist", "fortress"],
                        "description": "Optional: specific strategy profile to view",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trading_signals",
            "description": "Get technical analysis and trading signals for a stock: buy/sell verdict, entry/target/stop prices, risk/reward ratio, pattern detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol to analyze"},
                },
                "required": ["symbol"],
            },
        },
    },
]


# ── Tool execution ────────────────────────────────────────────

_TOOL_DISPATCH = {
    "get_stock_quote": lambda args, uid: _tool_stock_quote(args.get("symbol", "")),
    "search_screener": lambda args, uid: _tool_search_screener(args),
    "submit_suggestion": lambda args, uid: _tool_submit_suggestion(args, uid),
    "add_to_portfolio": lambda args, uid: _tool_add_to_portfolio(args, uid),
    "add_to_watchlist": lambda args, uid: _tool_add_to_watchlist(args, uid),
    "remove_from_watchlist": lambda args, uid: _tool_remove_from_watchlist(args, uid),
    "create_alert": lambda args, uid: _tool_create_alert(args, uid),
    "add_transaction": lambda args, uid: _tool_add_transaction(args, uid),
    "get_my_portfolio": lambda args, uid: _tool_get_my_portfolio(uid),
    "get_my_watchlist": lambda args, uid: _tool_get_my_watchlist(uid),
    "get_my_alerts": lambda args, uid: _tool_get_my_alerts(uid),
    "get_dashboard_summary": lambda args, uid: _tool_get_dashboard_summary(uid),
    "get_my_budgets": lambda args, uid: _tool_get_my_budgets(uid),
    "navigate_to": lambda args, uid: _tool_navigate_to(args),
    "get_ai_picks": lambda args, uid: _tool_get_ai_picks(args),
    "get_trading_signals": lambda args, uid: _tool_get_trading_signals(args),
}


def execute_tool(tool_name: str, args: dict, user_id: int | None = None) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        handler = _TOOL_DISPATCH.get(tool_name)
        if handler:
            return handler(args, user_id)
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
    """Save a suggestion to the database and create a GitHub Issue."""
    from sqlalchemy.orm import Session as _Session

    from src.database import SessionLocal
    from src.models import Suggestion, User
    from src.services import github_issues

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
        db.refresh(suggestion)

        # Create GitHub Issue (best-effort)
        user_email = ""
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user_email = user.email
        try:
            gh_result = github_issues.create_issue(
                title=summary[:120],
                body=summary,
                category=category,
                user_email=user_email,
            )
            if gh_result:
                suggestion.github_issue_url = gh_result["url"]
                suggestion.github_issue_number = gh_result["number"]
                db.commit()
        except Exception:
            pass

        gh_url = suggestion.github_issue_url or ""
        db.close()
        msg = "Suggestion logged successfully"
        if gh_url:
            msg += f" and tracked as GitHub Issue"
        return json.dumps({"success": True, "message": msg, "github_issue_url": gh_url})
    except Exception as e:
        logger.exception("Failed to save suggestion")
        return json.dumps({"error": str(e)})


# ── Write tools ───────────────────────────────────────────────


def _tool_add_to_portfolio(args: dict, user_id: int | None) -> str:
    """Add a stock holding to the user's portfolio."""
    from datetime import date, datetime

    from src.database import SessionLocal
    from src.models import Holding

    if not user_id:
        return json.dumps({"error": "You must be logged in to add to portfolio"})

    symbol = (args.get("symbol") or "").upper().strip()
    quantity = args.get("quantity")
    buy_price = args.get("buy_price")
    if not symbol or not quantity or not buy_price:
        return json.dumps({"error": "symbol, quantity, and buy_price are required"})

    buy_date_str = args.get("buy_date", "")
    try:
        buy_date = datetime.strptime(buy_date_str, "%Y-%m-%d").date() if buy_date_str else date.today()
    except ValueError:
        buy_date = date.today()

    try:
        db = SessionLocal()
        holding = Holding(
            symbol=symbol,
            name=args.get("name", symbol),
            quantity=float(quantity),
            buy_price=float(buy_price),
            buy_date=buy_date,
            notes=args.get("notes", ""),
            user_id=user_id,
        )
        db.add(holding)
        db.commit()
        db.refresh(holding)
        db.close()
        total = float(quantity) * float(buy_price)
        return json.dumps(
            {
                "success": True,
                "message": f"Added {quantity} shares of {symbol} at ${buy_price:.2f} (${total:,.2f} total) to your portfolio.",
                "holding_id": holding.id,
            }
        )
    except Exception as e:
        logger.exception("Failed to add to portfolio")
        return json.dumps({"error": str(e)})


def _tool_add_to_watchlist(args: dict, user_id: int | None) -> str:
    """Add a stock to the user's watchlist."""
    from src.database import SessionLocal
    from src.models import Watchlist

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    symbol = (args.get("symbol") or "").upper().strip()
    if not symbol:
        return json.dumps({"error": "symbol is required"})

    try:
        db = SessionLocal()
        existing = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol).first()
        if existing:
            db.close()
            return json.dumps({"message": f"{symbol} is already on your watchlist."})

        item = Watchlist(symbol=symbol, name=args.get("name", symbol), user_id=user_id)
        db.add(item)
        db.commit()
        db.close()
        return json.dumps({"success": True, "message": f"Added {symbol} to your watchlist."})
    except Exception as e:
        logger.exception("Failed to add to watchlist")
        return json.dumps({"error": str(e)})


def _tool_remove_from_watchlist(args: dict, user_id: int | None) -> str:
    """Remove a stock from the user's watchlist."""
    from src.database import SessionLocal
    from src.models import Watchlist

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    symbol = (args.get("symbol") or "").upper().strip()
    if not symbol:
        return json.dumps({"error": "symbol is required"})

    try:
        db = SessionLocal()
        item = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol).first()
        if not item:
            db.close()
            return json.dumps({"message": f"{symbol} is not on your watchlist."})

        db.delete(item)
        db.commit()
        db.close()
        return json.dumps({"success": True, "message": f"Removed {symbol} from your watchlist."})
    except Exception as e:
        logger.exception("Failed to remove from watchlist")
        return json.dumps({"error": str(e)})


def _tool_create_alert(args: dict, user_id: int | None) -> str:
    """Create a price alert."""
    from src.database import SessionLocal
    from src.models import Alert

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    symbol = (args.get("symbol") or "").upper().strip()
    condition = args.get("condition", "above")
    target_price = args.get("target_price")
    if not symbol or target_price is None:
        return json.dumps({"error": "symbol and target_price are required"})
    if condition not in ("above", "below"):
        return json.dumps({"error": "condition must be 'above' or 'below'"})

    try:
        db = SessionLocal()
        alert = Alert(
            symbol=symbol,
            name=args.get("name", symbol),
            condition=condition,
            target_price=float(target_price),
            user_id=user_id,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        db.close()
        return json.dumps(
            {
                "success": True,
                "message": f"Alert created: notify when {symbol} goes {condition} ${float(target_price):.2f}.",
                "alert_id": alert.id,
            }
        )
    except Exception as e:
        logger.exception("Failed to create alert")
        return json.dumps({"error": str(e)})


def _tool_add_transaction(args: dict, user_id: int | None) -> str:
    """Record income or expense transaction."""
    from datetime import date, datetime

    from src.database import SessionLocal
    from src.models import Category, Transaction

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    amount = args.get("amount")
    tx_type = args.get("type", "expense")
    description = args.get("description", "")
    if not amount or tx_type not in ("income", "expense"):
        return json.dumps({"error": "amount and valid type (income/expense) required"})

    date_str = args.get("date", "")
    try:
        tx_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        tx_date = date.today()

    try:
        db = SessionLocal()

        # Resolve category by name (or use "Other")
        cat_name = args.get("category_name", "Other") or "Other"
        category = db.query(Category).filter(Category.name.ilike(cat_name)).first()
        if not category:
            category = db.query(Category).filter(Category.name == "Other").first()
        if not category:
            # Use first available category
            category = db.query(Category).first()
        if not category:
            db.close()
            return json.dumps({"error": "No categories configured. Ask an admin to set up categories."})

        tx = Transaction(
            amount=float(amount),
            type=tx_type,
            description=description,
            date=tx_date,
            category_id=category.id,
            user_id=user_id,
        )
        db.add(tx)
        db.commit()
        db.close()
        return json.dumps(
            {
                "success": True,
                "message": f"Recorded {tx_type}: ${float(amount):,.2f} — {description} ({category.name}, {tx_date}).",
            }
        )
    except Exception as e:
        logger.exception("Failed to add transaction")
        return json.dumps({"error": str(e)})


# ── Read tools ────────────────────────────────────────────────


def _tool_get_my_portfolio(user_id: int | None) -> str:
    """Get user's portfolio summary."""
    from src.database import SessionLocal
    from src.services.portfolio import calculate_portfolio

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    try:
        db = SessionLocal()
        data = calculate_portfolio(db, user_id)
        db.close()

        holdings = data.get("holdings", [])
        if not holdings:
            return json.dumps({"message": "Your portfolio is empty. Add holdings to get started."})

        # Summarize for AI (keep it compact)
        summary_holdings = [
            {
                "symbol": h.get("symbol"),
                "qty": h.get("quantity"),
                "buy": h.get("buy_price"),
                "current": h.get("current_price"),
                "gain_pct": h.get("gain_loss_pct"),
            }
            for h in holdings[:10]
        ]
        return json.dumps(
            {
                "total_invested": data.get("total_invested"),
                "total_value": data.get("total_value"),
                "total_gain_loss": data.get("total_gain_loss"),
                "total_gain_loss_pct": data.get("total_gain_loss_pct"),
                "num_holdings": len(holdings),
                "holdings": summary_holdings,
                "best": data.get("best_performer"),
                "worst": data.get("worst_performer"),
            }
        )
    except Exception as e:
        logger.exception("Failed to get portfolio")
        return json.dumps({"error": str(e)})


def _tool_get_my_watchlist(user_id: int | None) -> str:
    """Get user's watchlist."""
    from src.database import SessionLocal
    from src.models import Watchlist

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    try:
        db = SessionLocal()
        items = db.query(Watchlist).filter(Watchlist.user_id == user_id).order_by(Watchlist.added_at.desc()).all()
        db.close()

        if not items:
            return json.dumps({"message": "Your watchlist is empty."})

        return json.dumps(
            {
                "count": len(items),
                "items": [{"symbol": w.symbol, "name": w.name} for w in items],
            }
        )
    except Exception as e:
        logger.exception("Failed to get watchlist")
        return json.dumps({"error": str(e)})


def _tool_get_my_alerts(user_id: int | None) -> str:
    """Get user's price alerts."""
    from src.database import SessionLocal
    from src.models import Alert

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    try:
        db = SessionLocal()
        alerts = db.query(Alert).filter(Alert.user_id == user_id).order_by(Alert.created_at.desc()).all()
        db.close()

        if not alerts:
            return json.dumps({"message": "You have no price alerts."})

        return json.dumps(
            {
                "count": len(alerts),
                "alerts": [
                    {
                        "symbol": a.symbol,
                        "condition": a.condition,
                        "target": a.target_price,
                        "active": bool(a.active),
                        "triggered": bool(a.triggered),
                    }
                    for a in alerts
                ],
            }
        )
    except Exception as e:
        logger.exception("Failed to get alerts")
        return json.dumps({"error": str(e)})


def _tool_get_dashboard_summary(user_id: int | None) -> str:
    """Get financial dashboard summary."""
    from datetime import date, timedelta

    from sqlalchemy import func

    from src.database import SessionLocal
    from src.models import Budget, Category, Transaction

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    try:
        db = SessionLocal()
        # Last 180 days
        since = date.today() - timedelta(days=180)
        txns = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.date >= since).all()

        total_income = sum(t.amount for t in txns if t.type == "income")
        total_expenses = sum(t.amount for t in txns if t.type == "expense")

        # Budget status (current month)
        today = date.today()
        month_start = today.replace(day=1)
        budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
        budget_status = []
        for b in budgets:
            spent = (
                db.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.category_id == b.category_id,
                    Transaction.type == "expense",
                    Transaction.date >= month_start,
                )
                .scalar()
                or 0
            )
            cat = db.query(Category).filter(Category.id == b.category_id).first()
            budget_status.append(
                {
                    "category": cat.name if cat else "?",
                    "limit": b.monthly_limit,
                    "spent": float(spent),
                    "pct": round(float(spent) / b.monthly_limit * 100, 1) if b.monthly_limit else 0,
                }
            )

        db.close()
        return json.dumps(
            {
                "period": f"Last 180 days",
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "net_balance": round(total_income - total_expenses, 2),
                "transaction_count": len(txns),
                "budgets": budget_status,
            }
        )
    except Exception as e:
        logger.exception("Failed to get dashboard")
        return json.dumps({"error": str(e)})


def _tool_get_my_budgets(user_id: int | None) -> str:
    """Get user's budgets with spending status."""
    from datetime import date

    from sqlalchemy import func

    from src.database import SessionLocal
    from src.models import Budget, Category, Transaction

    if not user_id:
        return json.dumps({"error": "You must be logged in"})

    try:
        db = SessionLocal()
        budgets = db.query(Budget).filter(Budget.user_id == user_id).all()

        if not budgets:
            db.close()
            return json.dumps({"message": "You have no budgets set up."})

        month_start = date.today().replace(day=1)
        result = []
        for b in budgets:
            spent = (
                db.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.category_id == b.category_id,
                    Transaction.type == "expense",
                    Transaction.date >= month_start,
                )
                .scalar()
                or 0
            )
            cat = db.query(Category).filter(Category.id == b.category_id).first()
            result.append(
                {
                    "category": cat.name if cat else "?",
                    "limit": b.monthly_limit,
                    "spent": float(spent),
                    "remaining": round(b.monthly_limit - float(spent), 2),
                    "pct": round(float(spent) / b.monthly_limit * 100, 1) if b.monthly_limit else 0,
                }
            )

        db.close()
        return json.dumps({"count": len(result), "budgets": result})
    except Exception as e:
        logger.exception("Failed to get budgets")
        return json.dumps({"error": str(e)})


# ── Navigation tool ───────────────────────────────────────────

_PAGE_LABELS = {
    "dashboard": "Dashboard",
    "portfolio": "Portfolio",
    "watchlist": "Watchlist",
    "dca": "DCA Planner",
    "alerts": "Price Alerts",
    "screener": "Stock Screener",
    "autopilot": "AI Picks (Autopilot)",
    "smart-advisor": "Smart Advisor",
    "il-funds": "IL Funds",
    "news": "News",
    "calendar": "Calendar",
    "picks-tracker": "Picks Tracker",
    "education": "Education",
    "profile": "Profile",
    "transactions": "Transactions",
    "budgets": "Budgets",
}


def _tool_navigate_to(args: dict) -> str:
    """Return navigation instruction for the frontend."""
    page = args.get("page", "")
    if page not in _PAGE_LABELS:
        return json.dumps({"error": f"Unknown page: {page}"})
    return json.dumps(
        {
            "navigate": page,
            "message": f"Opening {_PAGE_LABELS[page]} page.",
        }
    )


# ── AI analysis tools ─────────────────────────────────────────


def _tool_get_ai_picks(args: dict) -> str:
    """Get Autopilot strategy profiles."""
    try:
        from src.services.autopilot import get_profiles

        profiles = get_profiles()
        target_id = args.get("profile", "")

        if target_id:
            profile = next((p for p in profiles if p.get("id") == target_id), None)
            if not profile:
                return json.dumps({"error": f"Unknown profile: {target_id}. Options: daredevil, strategist, fortress"})
            return json.dumps(
                {
                    "id": profile["id"],
                    "name": profile.get("name"),
                    "risk_level": profile.get("risk_level"),
                    "expected_return": profile.get("expected_return"),
                    "expected_drawdown": profile.get("expected_drawdown"),
                    "strategy": profile.get("strategy"),
                    "sleeves": profile.get("sleeves", []),
                }
            )

        # Return all profiles (summary)
        summary = [
            {
                "id": p["id"],
                "name": p.get("name"),
                "risk_level": p.get("risk_level"),
                "expected_return": p.get("expected_return"),
                "strategy": p.get("strategy", "")[:80],
            }
            for p in profiles
        ]
        return json.dumps({"profiles": summary})
    except Exception as e:
        logger.exception("Failed to get AI picks")
        return json.dumps({"error": str(e)})


def _tool_get_trading_signals(args: dict) -> str:
    """Get technical analysis / trading signals for a symbol."""
    try:
        from src.services.trading_advisor import get_single_analysis

        symbol = (args.get("symbol") or "").upper().strip()
        if not symbol:
            return json.dumps({"error": "symbol is required"})

        result = get_single_analysis(symbol)
        if not result:
            return json.dumps({"error": f"No trading data for {symbol}"})

        action = result.get("action", {})
        return json.dumps(
            {
                "symbol": symbol,
                "name": result.get("name", ""),
                "verdict": action.get("verdict", "N/A"),
                "score": action.get("score"),
                "confidence": action.get("confidence"),
                "entry": action.get("entry"),
                "target": action.get("target"),
                "stop_loss": action.get("stop_loss"),
                "risk_reward": action.get("risk_reward"),
                "reasoning": action.get("reasoning", ""),
            }
        )
    except Exception as e:
        logger.exception("Failed to get trading signals")
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
        if "ACTION" in text:
            return "ACTION"
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
        yield _sse(
            {
                "type": "error",
                "content": "AI assistant not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables.",
            }
        )
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
    model = LARGE_MODEL if category in ("COMPLEX", "ACTION") else SMALL_MODEL

    yield _sse({"type": "model", "model": model, "category": category})

    # Build system prompt
    system_msg = SITE_KNOWLEDGE + "\n" + CONCISE_INSTRUCTION

    full_messages = [{"role": "system", "content": system_msg}, *messages]

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

            # Emit navigate event for frontend to act on
            if tool_name == "navigate_to":
                try:
                    nav_data = json.loads(result)
                    if "navigate" in nav_data:
                        yield _sse({"type": "navigate", "page": nav_data["navigate"]})
                except (json.JSONDecodeError, KeyError):
                    pass

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
        data: dict = resp.json()
        result: dict = data["choices"][0]["message"]
        return result
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
