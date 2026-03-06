# InvestAI — AI Coding Agent Context

> **Purpose of this file**: This document gives AI coding agents (GitHub Copilot, Cursor, etc.) the full context needed to navigate, debug, extend, and test this codebase. Keep it updated when adding new features.

## Project Overview

InvestAI is a full-stack personal investment advisory web application. It combines personal finance tracking (transactions, budgets) with advanced investment tools: stock screening, portfolio management, technical analysis, AI-driven advisory, DCA planning, value investing scanners, and more.

**Live site**: https://investai-utho.onrender.com

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.14, FastAPI | REST API, cookie-based JWT auth |
| Database | SQLite via SQLAlchemy 2.0 | Auto-migrated on startup |
| Validation | Pydantic v2 | Request/response schemas |
| Market Data (primary) | Finnhub API | Quotes, candles, news, fundamentals, earnings, insider trades |
| Market Data (fallback) | yfinance | Auto-disabled on repeated failures with cooldown |
| Israeli Funds | funder.co.il scraper | Static JSON fallback if scrape fails |
| Frontend | Vanilla HTML/CSS/JS | No React/Vue/Angular — single-page app |
| Charts | Chart.js 4.x | Dashboard, portfolio, stock history, advisor charts |
| Deployment | Render (free tier) | See `render.yaml`, `LowMemoryMiddleware` for OOM prevention |
| Android | Kotlin + Jetpack Compose | WebView wrapper, see `android/` folder |

## Architecture

### Backend Structure

```
src/
├── main.py                     # FastAPI app, auth routes, middleware, router registration
├── auth.py                     # JWT creation/validation, AuthMiddleware, password hashing
├── database.py                 # SQLAlchemy engine, session factory, Base
├── models.py                   # All ORM models (User, Transaction, Budget, Holding, Alert, DcaPlan, etc.)
├── routers/                    # 22 API route modules (one per domain)
│   ├── admin.py                # /api/admin — user management, system stats
│   ├── alerts.py               # /api/alerts — price alerts with auto-trigger
│   ├── autopilot.py            # /api/autopilot — investment simulation profiles
│   ├── budgets.py              # /api/budgets — budget CRUD + status
│   ├── calendar_router.py      # /api/calendar — earnings + economic events
│   ├── categories.py           # /api/categories — income/expense categories
│   ├── comparison.py           # /api/compare — side-by-side stock comparison
│   ├── dashboard.py            # /api/dashboard — financial summary + charts
│   ├── dca.py                  # /api/dca — DCA plans, dip detection, allocation
│   ├── education.py            # /api/education — educational articles
│   ├── israeli_funds.py        # /api/il-funds — Israeli fund browser
│   ├── market.py               # /api/market — live ticker, sparklines, featured stocks
│   ├── news.py                 # /api/news — personalized + per-ticker news
│   ├── picks_tracker.py        # /api/picks — Discord stock picks P&L tracker
│   ├── portfolio.py            # /api/portfolio — holdings, performance, sector allocation
│   ├── profile.py              # /api/profile — risk questionnaire + allocation
│   ├── recommendations.py      # /api/recommendations — risk-aligned picks
│   ├── screener.py             # /api/screener — multi-filter screener + watchlist
│   ├── smart_advisor.py        # /api/advisor — AI scoring, portfolios, backtest, Company DNA
│   ├── stock_detail.py         # /api/stock — full stock page (fundamentals + chart + news)
│   ├── trading_advisor.py      # /api/trading — strategy packages, technical analysis
│   └── value_scanner.py        # /api/value-scanner — Graham-Buffett value screen
├── schemas/                    # Pydantic request/response models (one per domain)
└── services/                   # Business logic (no HTTP concerns)
    ├── finnhub_client.py       # Rate-limited Finnhub API wrapper
    ├── data_provider.py        # Unified data layer: Yahoo → Finnhub fallback
    ├── market_data.py          # Cache layer, sparklines, background warmer (15-min cycle)
    ├── technical_analysis.py   # 1100+ lines: RSI, MACD, Bollinger, Stochastic, ATR, OBV, ADX, Ichimoku, Fibonacci, etc.
    ├── smart_advisor.py        # Universe scanning, multi-factor scoring, portfolio construction, backtesting
    ├── trading_advisor.py      # Strategy packages (Momentum/Swing/Oversold/Hidden Gems/Institutional)
    ├── value_scanner.py        # Graham-Buffett screen, quality score, margin of safety
    ├── company_dna.py          # Berkshire Score, executive analysis, insider sentiment
    ├── portfolio.py            # Portfolio valuation, sector allocation, benchmark comparison
    ├── dca.py                  # DCA opportunity analysis, dip detection, budget suggestions
    ├── screener.py             # Signal computation (Buy/Hold/Sell), filtering
    ├── risk_profile.py         # Risk score calculation, allocation mapping
    ├── recommendations.py      # Risk-aligned instrument scoring
    ├── autopilot.py            # Investment profiles, historical simulation
    ├── news.py                 # News aggregation from Finnhub
    ├── calendar_service.py     # Earnings + economic events from Finnhub
    ├── education.py            # Static article library
    ├── stock_detail.py         # Combined info + history resolution
    ├── picks_tracker.py        # Discord pick evaluation + P&L
    ├── israeli_funds.py        # Fund filtering/sorting/best-deals
    └── funder_scraper.py       # funder.co.il web scraper + static fallback
```

### Frontend Structure

```
static/
├── index.html                  # All page sections as hidden divs (SPA)
├── login.html                  # Login/register page
├── style.css                   # Dark/light theme, responsive layout
├── app.js                      # Legacy (navigation moved to js/app.js)
└── js/                         # 28 JS modules
    ├── api.js                  # Fetch wrapper with auto 401→login redirect
    ├── app.js                  # SPA navigation, theme toggle, sidebar, mobile nav
    ├── dashboard.js            # Income/expense cards, trend chart, category donut, budget bars
    ├── transactions.js         # Transaction list, filters, add/edit/delete modals
    ├── budgets.js              # Budget management with progress bars
    ├── portfolio.js            # Holdings table, gain/loss, allocation pie, performance chart
    ├── market.js               # Scrolling ticker tape, sparkline cards, 60s auto-refresh
    ├── stock-detail.js         # Stock page: Chart.js price chart, fundamentals, SMA, news
    ├── screener.js             # Filter panel, result cards, presets, watchlist integration
    ├── watchlist.js            # Live watchlist with prices
    ├── comparison.js           # Side-by-side metrics + normalized overlay chart
    ├── smart-advisor.js        # Rankings, portfolio tabs, backtest chart, Company DNA modal
    ├── advisor.js              # Trading advisor: mood donut, strategy tabs, indicator charts
    ├── value-scanner.js        # Progress, stats, sector tabs, quality bars, action plan
    ├── autopilot.js            # Profile cards, simulation chart, allocation, methodology
    ├── dca.js                  # DCA plans, dip opportunities, monthly allocation
    ├── alerts.js               # Alert management, bell badge polling
    ├── news.js                 # News feed with time-ago, search filter
    ├── calendar.js             # Earnings + economic events tabs
    ├── education.js            # Article cards with category filters
    ├── il-funds.js             # Israeli fund browser with filters
    ├── picks-tracker.js        # Discord picks P&L table, stats, seed-to-watchlist
    ├── recommendations.js      # Recommended instrument cards
    ├── profile.js              # Risk questionnaire wizard, allocation donut
    ├── admin.js                # Admin dashboard: stats, user table, actions
    ├── context-menu.js         # Right-click context menus
    ├── tooltips.js             # Tooltip system
    └── pagination.js           # Reusable pagination component
```

## Complete API Reference

### Authentication (`/auth/*` in main.py)

| Method | Path | Action |
|--------|------|--------|
| POST | `/auth/register` | Create account (rate-limited 3/min) |
| POST | `/auth/login` | Login, sets httponly JWT cookie (rate-limited 5/min) |
| POST | `/auth/logout` | Clear auth cookie |
| GET | `/` | Serve main SPA |
| GET | `/login` | Serve login page |

### Admin Panel (`/api/admin`)

| Method | Path | Action |
|--------|------|--------|
| GET | `/stats` | System-wide stats (users, transactions, holdings, alerts, DCA plans) |
| GET | `/users` | Paginated user list with search + activity counts |
| GET | `/users/{user_id}` | Full user detail |
| POST | `/toggle-admin` | Promote/demote admin (self-protection) |
| POST | `/toggle-active` | Enable/disable user account |
| POST | `/reset-password` | Force-reset user password |
| DELETE | `/users/{user_id}` | Delete user + all associated data |

### Personal Finance

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/dashboard` | Aggregated income/expense/balance, category breakdown, monthly trend |
| GET/POST | `/api/categories` | List or create categories |
| DELETE | `/api/categories/{id}` | Delete category (blocked if transactions exist) |
| GET/POST | `/api/transactions` | List (filtered, paginated) or create transactions |
| PUT/DELETE | `/api/transactions/{id}` | Update or delete transaction |
| GET | `/api/budgets` | List budgets |
| GET | `/api/budgets/status` | Budgets with spent amounts + color-coded progress |
| POST | `/api/budgets` | Upsert budget |
| DELETE | `/api/budgets/{id}` | Delete budget |

### Risk Profile & Recommendations

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/profile` | Get current risk profile |
| POST | `/api/profile` | Submit questionnaire → risk score + label |
| GET | `/api/profile/allocation` | Recommended allocation (stocks/bonds/cash %) |
| GET | `/api/recommendations` | Personalized picks based on risk profile |

### Portfolio Management

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/portfolio/summary` | Total value, gain/loss, sector allocation, best/worst |
| GET | `/api/portfolio/performance` | Historical performance vs SPY benchmark |
| GET | `/api/portfolio/holdings` | Raw holdings list |
| POST | `/api/portfolio/holdings` | Add holding (symbol, shares, buy price, date) |
| DELETE | `/api/portfolio/holdings/{id}` | Remove holding |

### Market Data

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/market/ticker` | Live quotes: SPY, QQQ, AAPL, MSFT, GOOGL, NVDA, TSLA, AMZN |
| GET | `/api/market/featured` | Featured stocks with sparkline mini-charts |
| GET | `/api/market/home` | Combined ticker + featured (single round trip) |
| GET | `/api/market/cache-status` | Cache diagnostic info |

### Stock Research

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/stock/{symbol}` | Fundamentals, signal (Buy/Hold/Sell), risk analysis, analyst targets |
| GET | `/api/stock/{symbol}/full` | Combined: info + price history (with SMA50) + news |
| GET | `/api/stock/{symbol}/history` | Price history with configurable period/interval |
| GET | `/api/stock/{symbol}/news` | Stock-specific news |

### Stock Screener & Watchlist

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/screener` | Multi-filter screener (type, sector, cap, P/E, dividend, beta, signal) |
| GET | `/api/screener/sectors` | Available sectors and regions |
| GET | `/api/screener/watchlist` | User's watchlist items |
| GET | `/api/screener/watchlist/live` | Watchlist with live prices + fundamentals |
| POST | `/api/screener/watchlist` | Add to watchlist |
| DELETE | `/api/screener/watchlist/{id}` | Remove from watchlist |

### Stock Comparison

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/compare?symbols=AAPL,MSFT,GOOGL` | Side-by-side fundamentals + normalized price history (up to 4) |

### Smart Advisor (AI-driven)

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/advisor/analyze` | Scan universe → score → build 3 portfolios → backtest with Sharpe/drawdown |
| GET | `/api/advisor/stock/{symbol}` | Deep technical + fundamental analysis for single stock |
| GET | `/api/advisor/company-dna/{symbol}` | Berkshire Score, executive analysis, insider transactions, institutional sentiment |

### Trading Advisor

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/trading` | Dashboard: 5 strategy packages, market mood, scan progress |
| GET | `/api/trading/{symbol}` | Full technical analysis (RSI, MACD, Bollinger, Stochastic, ADX, Ichimoku, Fibonacci, OBV) |

Strategies: Momentum | Swing | Oversold Bargains | Hidden Gems | Institutional Favorites

### Value Scanner (Graham-Buffett)

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/value-scanner` | Graham-Buffett screen (P/E ≤ 15, D/E ≤ 1.0, CR ≥ 1.5, FCF > 0) |
| GET | `/api/value-scanner/action-plan` | Portfolio action plan from value candidates |
| GET | `/api/value-scanner/sectors` | Available sectors |

### Autopilot Simulation

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/autopilot/profiles` | Investment profiles (Daredevil, Strategist, Fortress) |
| GET | `/api/autopilot/simulate` | Historical simulation with real data for given amount/profile/period |

### DCA Planning

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/dca/dashboard` | Plans, dip opportunities, monthly allocation, total DCA value |
| GET | `/api/dca/budget-suggestion` | Budget suggestion based on risk profile |
| GET/POST | `/api/dca/plans` | List or create DCA plans |
| PUT/DELETE | `/api/dca/plans/{id}` | Update or delete DCA plan |

### Price Alerts

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/alerts` | List alerts (auto-triggers if price condition met) |
| GET | `/api/alerts/triggered` | List triggered alerts |
| POST | `/api/alerts` | Create price alert (above/below target) |
| DELETE | `/api/alerts/{id}` | Delete alert |
| POST | `/api/alerts/{id}/dismiss` | Dismiss triggered alert |

### News & Calendar

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/news` | Personalized news (from watchlist + holdings) |
| GET | `/api/news/{symbol}` | News for specific ticker |
| GET | `/api/calendar/earnings` | Earnings calendar for user's stocks |
| GET | `/api/calendar/economic` | Economic events calendar |

### Education

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/education` | Educational articles by category |

### Israeli Funds

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/il-funds` | Filterable fund list (type, manager, kosher, fees, returns, size) |
| GET | `/api/il-funds/best` | Best deals by category |
| GET | `/api/il-funds/meta` | Fund types + managers metadata |

### Discord Picks Tracker

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/picks` | Evaluate all Discord picks with current P&L |
| POST | `/api/picks/seed-watchlist` | Bulk-add pick symbols to watchlist |

## Data Flow

```
User → Frontend (Vanilla JS) → REST API (FastAPI routers)
                                        ↓
                                 Services (business logic)
                                   ↓              ↓
                          SQLAlchemy Models    Market Data
                                   ↓              ↓
                                SQLite DB     data_provider.py
                                                   ↓
                                          Yahoo Finance (primary)
                                                   ↓ (on failure)
                                          Finnhub API (fallback)
                                                   ↓
                                          15-min in-memory cache
```

## Key Technical Details

### Authentication
- JWT tokens stored in httponly cookies (not localStorage)
- `AuthMiddleware` exempts `/login`, `/auth/*`, `/static/*`
- Rate limiting: 3/min register, 5/min login (disabled during `TESTING=1`)

### Market Data Strategy
- `data_provider.py` tries Yahoo first, auto-disables on failures with cooldown
- `finnhub_client.py` is rate-limited (Finnhub free tier: 60 calls/min)
- `market_data.py` runs a background thread that pre-warms cache every 15 minutes
- Sparklines are generated server-side as coordinate arrays

### Background Tasks
- **Cache warmer**: Refreshes market data every 15 minutes
- **Trading advisor scanner**: Scans stock universe in background
- **Value scanner**: Background Graham-Buffett screening with progress reporting

### Security
- OWASP security headers (CSP, HSTS, X-Frame-Options, etc.)
- Admin endpoints check `is_admin` flag
- Self-protection: admins can't demote/disable themselves
- Password minimum 8 characters, bcrypt hashing

### Deployment (Render)
- `LowMemoryMiddleware` monitors RSS and triggers GC when close to limit
- `render.yaml` defines the web service configuration
- Auto-migrate on startup (adds columns, indexes safely)
- Default admin seeded from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars

## Database Models

- **User**: id, email, hashed_password, name, is_admin, is_active
- **Category**: id, name, color, type (income/expense), user_id
- **Transaction**: id, amount, type, description, date, category_id, user_id
- **Budget**: id, category_id, monthly_limit, user_id
- **RiskProfile**: id, goal, timeline, monthly_investment, experience, risk_reaction, income_stability, risk_score, profile_label, user_id
- **Watchlist**: id, symbol, added_at, user_id
- **Holding**: id, symbol, shares, buy_price, buy_date, user_id
- **Alert**: id, symbol, target_price, condition (above/below), triggered, triggered_at, dismissed, user_id
- **DcaPlan**: id, symbol, monthly_budget, dip_threshold, dip_multiplier, long_term, is_active, user_id
- **PasswordReset**: id, user_id, token, created_at

## API Patterns

- All routes live under `/api/` prefix
- Routers use `APIRouter(prefix="/api/...", tags=[...])` and are registered in `main.py`
- Use `Depends(get_db)` for database sessions
- `request.state.user` holds the authenticated user (set by `AuthMiddleware`)
- Return Pydantic response models with `from_attributes = True`
- HTTP 404 for not found, 400 for validation, 403 for unauthorized
- Market data endpoints may be slow (external API fetch); frontend shows loading spinners

## Adding a New Feature

1. Add SQLAlchemy model to `src/models.py`
2. Create Pydantic schemas in `src/schemas/<domain>.py`
3. Create service logic in `src/services/<domain>.py` (business logic only, no HTTP)
4. Create router in `src/routers/<domain>.py` using `APIRouter(prefix="/api/<domain>", tags=["<Domain>"])`
5. Import and include router in `src/main.py`
6. Add HTML section in `static/index.html` (as another hidden `<section>` div)
7. Add JS module in `static/js/<domain>.js`
8. Add `<script>` tag in `index.html`
9. Register nav item in `js/app.js`
10. Add CSS for new components in `static/style.css`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `FINNHUB_API_KEY` | Finnhub API access (required for market data) |
| `INVESTAI_SECRET` | JWT signing secret |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Default admin account seeded on startup |
| `HTTP_PROXY` / `HTTPS_PROXY` | Corporate proxy (Intel) |
| `USE_INTEL_PROXY` | Flag for proxy-aware HTTP clients |
| `NO_PROXY` | Bypass proxy for local addresses |
| `TESTING` | Set to `1` to disable rate limiting |
| `LOW_MEMORY` | Set to `1` for aggressive memory management |
| `RENDER` / `PRODUCTION` | Disables /docs, /redoc, /openapi.json |
| `DISABLE_YAHOO` | Force Finnhub-only mode |

## Important Constraints

- **No frontend frameworks**: Vanilla JS only. No React, Vue, or Angular.
- **File size**: Keep files under 400 lines. Split if growing larger.
- **Finnhub rate limits**: Free tier = 60 calls/min. Always use cache. Never call in loops.
- **Yahoo Finance**: Unreliable, auto-disabled on failures. Finnhub is the reliable fallback.
- **SQLite**: Single-writer. Fine for this app's scale.
- **Proxy**: Intel corporate proxy required for external API calls. Set `HTTP_PROXY`/`HTTPS_PROXY`.
- **Render free tier**: 512 MB RAM. `LowMemoryMiddleware` exists to prevent OOM kills.

## Testing

- **Smoke tests**: `tests/test_api_smoke.py` — fast, uses TestClient, no external APIs
- **E2E tests**: `tests/test_e2e.py` — requires running server on port 8091
- **Live site tests**: `tests/test_live_site.py` — tests against deployed Render instance
- Run with: `python -m pytest tests/test_api_smoke.py -v --tb=short`
- Set `TESTING=1` to disable rate limiting during tests
