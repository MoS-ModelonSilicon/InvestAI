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
  - Stock comparison tool (2-4 stocks side-by-side)
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

- **79 files**, **12,500+ lines** of code
- **280+ global stock symbols** across 12 regions
- **481 Israeli mutual funds** from live data
- **15 API routers**, **10 service modules**, **18 JS modules**
- **Built entirely in one session** with Cursor + Claude

## Known Issues

- yfinance rate limiting can temporarily affect data fetching (external API issue)
- SQLite is single-file — all users sharing the server share the same data
- Intel proxy bypass needed for LAN access from other machines (`NO_PROXY=10.*`)
