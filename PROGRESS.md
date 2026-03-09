# Development Progress

## Completed

- [x] **Original Finance Tracker** (2026-03-03)
  - Dashboard with income/expense stats, monthly trend chart, category breakdown
  - Transaction CRUD with filtering by type, category, date range
  - Budget management with visual progress bars
  - 12 pre-seeded categories (3 income, 9 expense)
  - Dark-themed responsive UI with Chart.js charts

- [x] **Research & Planning** (2026-03-03)
  - Researched fintech robo-advisor flows (Wealthfront, Betterment patterns)
  - Researched UI/UX best practices for investment apps
  - Researched Cursor + Claude project management best practices
  - Defined 3-phase build plan with modular architecture

- [x] **Project Restructuring** (2026-03-03)
  - Migrated to src/ modular layout with routers, schemas, services
  - Split JS into per-page modules
  - Created AGENTS.md, PROGRESS.md, Cursor rules

- [x] **Phase 1: Risk Profile Wizard** (2026-03-03)
  - Backend: RiskProfile model, weighted scoring algorithm, allocation mapping
  - Frontend: 6-step wizard with progress bar, option cards, slider, risk gauge result

- [x] **Phase 2: Stock & Fund Screener** (2026-03-03)
  - Market data service with yfinance + 15-min in-memory cache
  - Background cache warming for instant screener results
  - Buy/Hold/Avoid signals with multi-factor analysis
  - Risk analysis (volatility, valuation, financial health, growth, price position)
  - Analyst price targets with visual range bar

- [x] **Phase 3: Recommendations** (2026-03-03)
  - Recommendation engine: profile → allocation → instrument scoring
  - Scoring based on beta, P/E, dividend yield, momentum, analyst ratings
  - Frontend: allocation pie chart, tabbed card grid with match scores

- [x] **Phase 4: Full Platform Build** (2026-03-03)
  - Watchlist page with live prices
  - Stock detail pages with interactive Chart.js charts and timeframes
  - Portfolio tracker with virtual holdings, gain/loss, sector allocation
  - Performance analytics vs S&P 500 benchmark
  - News feed aggregating articles from watchlist/holdings
  - Price alerts with bell notifications and auto-polling
  - Education center with categorized articles
  - Earnings & economic events calendar

- [x] **Phase 5: Global Expansion** (2026-03-03)
  - Added 100+ international stocks: China/HK, Japan, Korea, Taiwan, Europe, India, Australia, Canada, Brazil, Singapore
  - Added 13 international/emerging market ETFs
  - Region filter in screener + region badges on cards
  - Quick presets for China/HK and Europe
  - Featured dashboard updated with global names (Xiaomi, Tencent, TSMC, ASML, etc.)

- [x] **Phase 6: Israeli Funds Explorer** (2026-03-03)
  - Live scraper for funder.co.il (kaspit, index tracking, kosher, managed funds)
  - 481 real mutual funds with live data
  - Fee comparison: management fee, entry fee, cost per ₪100K
  - Best deal highlighting, market overview stats
  - Filters: type, manager, max fee, min return, min size, kosher only

- [x] **Performance Optimization** (2026-03-03)
  - Rewrote fetch_live_quotes to use yf.download() batch (single HTTP request vs N sequential)
  - Parallelized featured endpoint (quotes + sparklines concurrent)
  - Parallelized frontend API calls with Promise.all
  - Separate 90s cache TTL for live quotes vs 15min for full info

- [x] **Infrastructure** (2026-03-03)
  - Access key authentication with HMAC-signed session cookies
  - Login page with dark theme matching the app
  - Logout button in sidebar
  - Firewall rule for network sharing (port 8000)
  - Server bound to 0.0.0.0 for LAN access
  - GitHub repo created: MoS-ModelonSilicon/InvestAI

## Stats

- **79 files**, **15,000+ lines** of code
- **280+ global stock symbols** across 12 regions
- **481 Israeli mutual funds** from live data
- **15 API routers**, **12 service modules**, **18 JS modules**
- **35+ technical indicators**, **21 candlestick patterns**, **10 chart patterns**
- **Built entirely in one session** with Cursor + Claude

- [x] **Security: Admin Credential Hardening** (2026-03-06)
  - Replaced weak default admin credentials (`admin@test.com` / `admin123`) with secure ones
  - Admin email set to `yaronklein1@gmail.com` with strong password (mixed case, numbers, symbols)
  - Added minimum 8-character password validation in `src/main.py` startup auto-create flow
  - Updated `run.ps1` local dev script with new secure credentials
  - Added `ADMIN_EMAIL` / `ADMIN_PASSWORD` placeholders to `render.yaml` (`sync: false`)
  - Updated Render production env vars via Render REST API
  - Triggered Render redeploy to apply changes
  - Documented new admin email in `DEPLOY-KEYS.md` (password intentionally omitted from docs)

- [x] **AI Assistant Chatbot** (2026-03-09)
  - Two-tier model routing: gpt-5-nano for simple queries (FAQ, greetings), o3 for complex financial reasoning + actions
  - Both models are Azure OpenAI reasoning models — no temperature, uses `max_completion_tokens`
  - SSE streaming with token-by-token output and model badge indicators (⚡ nano / 🧠 o3)
  - Tool calling: o3 can invoke `get_stock_quote`, `search_screener`, `submit_suggestion` mid-conversation
  - Classification prompt routes each message to SIMPLE / COMPLEX / ACTION / SUGGESTION
  - Floating chat widget (bottom-right FAB → 380px panel) with 20-message context window
  - Suggestion box: users submit feature requests, optional AI summary categorization
  - Admin endpoints: list, update status, view stats for suggestions
  - Backend: `src/services/assistant.py` (~470 lines), `src/routers/assistant.py` (7 endpoints)
  - Frontend: `static/js/assistant.js` (SSE client, markdown-lite rendering), `static/style.css` (+279 lines)
  - Env vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` (set in Render dashboard)
  - API pattern: `{endpoint}/openai/deployments/{model}/chat/completions?api-version=2024-12-01-preview`

- [x] **GitHub Issues Integration + Admin Dashboard** (2026-03-09)
  - `src/services/github_issues.py` — GitHub REST API service (create/close/reopen issues, add comments)
  - Auto-discovers GitHub token (`GITHUB_TOKEN` env var or `gh auth token` CLI fallback)
  - Auto-discovers repo from git remote origin URL
  - Intel proxy auto-detection for corporate networks
  - Labels auto-applied: `user-feedback`, `feature-request`, `user-bug` (based on category)
  - Two integration paths: manual suggestion form + AI tool both create GitHub Issues
  - Admin status changes sync to GitHub (done/declined → close issue, reopen on status revert)
  - Admin notes posted as GitHub comments on the linked issue
  - `github_issue_url` + `github_issue_number` columns added to Suggestion model
  - Auto-migration in `src/main.py` for existing databases
  - Admin UI: "Feature Requests & Bugs" section with filter dropdown, detail modal, GitHub links
  - Stats badges: total suggestions, new requests shown on admin dashboard

- [x] **AI Assistant: 13 New Tool Capabilities** (2026-03-09)
  - **Write tools (5):** `add_to_portfolio` (buy shares), `add_to_watchlist`, `remove_from_watchlist`, `create_alert` (above/below price triggers), `add_transaction` (income/expense with category lookup)
  - **Read tools (5):** `get_my_portfolio` (holdings + P&L summary), `get_my_watchlist`, `get_my_alerts`, `get_dashboard_summary` (income/expenses/budgets), `get_my_budgets` (spending vs limits)
  - **Analysis tools (2):** `get_ai_picks` (Autopilot strategy profiles), `get_trading_signals` (technical analysis with entry/target/stop/R:R)
  - **Navigation (1):** `navigate_to` — emits SSE `navigate` event, frontend clicks the nav link to switch pages
  - Classification expanded: SIMPLE / COMPLEX / ACTION / SUGGESTION — ACTION routes to o3 for reliable tool calling
  - Total tool count: 16 (3 original + 13 new)
  - All tools use `SessionLocal()` pattern for DB access (same as existing `_tool_submit_suggestion`)
  - Frontend `showToolIndicator()` labels expanded for all 16 tools

- [x] **Bulk Manage: Multi-Select Delete for Portfolio & Watchlist** (2026-03-09)
  - "Manage" toggle button in Portfolio and Watchlist headers — enters edit mode
  - Checkboxes appear on every holding row / watchlist card for multi-select
  - Sticky action toolbar with Select All / Deselect All, live counter ("4 of 12 selected"), Remove Selected
  - Confirmation modal lists every symbol being removed before deletion
  - Toast notification on completion ("3 holdings removed")
  - Backend: `POST /api/portfolio/holdings/bulk-delete` and `POST /api/screener/watchlist/bulk-delete` — single DB call for bulk operations
  - New shared module `static/js/bulk-manage.js` for modal and toolbar helpers
  - CSS: custom checkboxes, selected-row/card highlights, slide-in toolbar animation

- [x] **Visual Decision Framework + 35 New Patterns/Indicators** (2026-03-09)
  - **`pattern_detection.py`** (1,300+ lines): 10 chart patterns (Double Top/Bottom, Head & Shoulders, Inverse H&S, Bull/Bear Flags, Ascending/Descending/Symmetric Triangles, Rising/Falling Wedges, Triple Top/Bottom) + 21 candlestick patterns (Doji, Dragonfly/Gravestone Doji, Hammer, Inverted Hammer, Shooting Star, Hanging Man, Marubozu, Bullish/Bearish Engulfing, Piercing Line, Dark Cloud Cover, Bullish/Bearish Harami, Tweezer Top/Bottom, Morning/Evening Star, Three White Soldiers, Three Black Crows) + gap classification (Breakaway, Runaway, Exhaustion, Common)
  - **`advanced_indicators.py`** (770+ lines): VWAP, Keltner Channels, TTM Squeeze, Parabolic SAR, Williams %R, Chaikin Money Flow, Donchian Channels, Aroon, CCI, Heikin-Ashi, Force Index, Linear Regression Channel, Momentum, Rate of Change — each with aggregate scoring
  - **Backend integration**: `get_single_analysis()` rewritten to call both engines, merge signals into `decision_breakdown`, adjust composite score with pattern + advanced boosts
  - **"Why This Score?" waterfall chart**: Each indicator's weighted contribution shown as green (bullish) or red (bearish) bars
  - **Candlestick chart mode**: Toggle between OHLC candles and line view
  - **Overlay toggles**: SMA, Bollinger, VWAP, Keltner, Parabolic SAR, Ichimoku — click to add/remove from price chart
  - **Pattern annotations**: Chart patterns drawn as connected point markers; candlestick patterns as triangular markers at detection indices
  - **Pattern badges section**: All detected patterns displayed as colored tags with confidence %
  - **TTM Squeeze badge**: Animated pulse when Bollinger-inside-Keltner squeeze fires
  - **New sub-charts**: Stochastic %K/%D and ADX (+DI/-DI) alongside RSI + MACD
  - **Loading spinner** with debounce to prevent double-opens

- [x] **DevOps: Render API Management** (2026-03-06)
  - Established Render API access for automated deployments and env-var management
  - API key and Service ID documented in `DEPLOY-KEYS.md`
  - Can now read/update env vars and trigger deploys directly from Cursor terminal
  - Deploy workflow documented: push to GitHub → trigger Render deploy via API

## Known Issues

- yfinance rate limiting can temporarily affect data fetching (external API issue)
- SQLite is single-file — all users sharing the server share the same data
- Intel proxy bypass needed for LAN access from other machines (`NO_PROXY=10.*`)
