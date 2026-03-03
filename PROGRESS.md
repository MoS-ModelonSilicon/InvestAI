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
  - Split JS into per-page modules (7 files)
  - Created AGENTS.md, PROGRESS.md, Cursor rules

- [x] **Phase 1: Risk Profile Wizard** (2026-03-03)
  - Backend: RiskProfile model, weighted scoring algorithm, allocation mapping
  - Frontend: 6-step wizard with progress bar, option cards, slider, risk gauge result

- [x] **Phase 2: Stock & Fund Screener** (2026-03-03)
  - Market data service with yfinance + 15-min in-memory cache
  - 50 stocks + 30 ETFs universe
  - Screener with 9 filter dimensions + 4 quick presets
  - Frontend: sidebar filters, sortable results table

- [x] **Phase 3: Recommendations** (2026-03-03)
  - Recommendation engine: profile → allocation → instrument scoring
  - Scoring based on beta, P/E, dividend yield, momentum, analyst ratings
  - Frontend: allocation pie chart, tabbed card grid with match scores

## Next Steps

- [ ] **Phase 4: Polish**
  - Watchlist with live-ish prices on dashboard
  - Enhanced dashboard with investment overview
  - Portfolio simulation with historical backtesting
  - More instruments in universe (international, bonds)

## Known Issues

- yfinance calls can be slow (2-5 seconds). Need loading indicators on frontend.
- SQLite file (finance.db) lives in project root. Don't commit it.

## Session Notes

### Session 1 (2026-03-03)
- Built original finance tracker from scratch
- Researched fintech patterns, Cursor best practices
- Starting restructuring + Phase 1 build
