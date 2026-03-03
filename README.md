# InvestAI — Investment Advisory Platform

A full-stack investment advisory web app with live market data, global stock screening, portfolio tracking, Israeli mutual fund comparison, and personalized recommendations.

**Live demo:** Start the server and share via `http://<your-ip>:8000` (access key required).

## Features

### Market & Research
- **Live Market Dashboard** — real-time ticker bar + featured stock cards with sparkline charts
- **Stock & ETF Screener** — 280+ global symbols across 12 regions (US, China/HK, Japan, Europe, India, Israel, etc.) with 10 filter dimensions, region filtering, and quick presets
- **Stock Detail Pages** — full company overview, interactive price charts with timeframes, analyst price targets, risk analysis, news
- **Stock Comparison** — side-by-side normalized chart + metrics table for 2-4 stocks
- **Market News** — aggregated news from watchlist and portfolio holdings

### Portfolio & Tracking
- **Portfolio Tracker** — virtual holdings with real-time gain/loss, sector allocation pie chart, performance vs S&P 500 benchmark
- **Watchlist** — bookmark stocks with live price cards
- **Price Alerts** — set above/below triggers, bell notifications, auto-check polling

### Israeli Funds (קרנות נאמנות)
- **Live data from funder.co.il** — 481 real mutual funds scraped in real-time
- **4 categories:** Kaspit (money market), index tracking, kosher, actively managed
- **Fee comparison** — sort by management fee (דמי ניהול), see cost per ₪100K, find the cheapest deals
- **Quick presets:** cheapest Kaspit, best return, index tracking, kosher only

### Advisory
- **Risk Profile Wizard** — 6-step questionnaire → risk score → investor profile
- **Personalized Recommendations** — allocation pie + scored instrument cards based on your profile
- **Education Center** — investment articles by difficulty level
- **Earnings Calendar** — upcoming earnings dates and economic events

### Finance Tracking
- **Transactions** — income/expense CRUD with filtering
- **Budgets** — monthly limits per category with progress bars
- **Dashboard** — financial overview with trend charts and category breakdown

### Infrastructure
- **Access Key Auth** — protect the site with a shared passphrase for network sharing
- **Background Cache Warming** — pre-fetches all market data so the screener is instant
- **Intel Proxy Support** — configured for corporate proxy environments

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite (file-based) |
| Market Data | yfinance (280+ global symbols) |
| Israeli Funds | Live scraper for funder.co.il |
| Frontend | Vanilla HTML/CSS/JS, Chart.js 4.x |
| Auth | HMAC-signed session cookies |

## Quick Start

```bash
cd finance-tracker
pip install -r requirements.txt

# Basic (localhost only)
python -m uvicorn src.main:app --reload

# Network sharing (accessible from other machines)
# Set your access key and proxy if needed
$env:INVESTAI_ACCESS_KEY="yourkey"
$env:HTTP_PROXY="http://proxy-dmz.intel.com:911"
$env:HTTPS_PROXY="http://proxy-dmz.intel.com:912"
python -m uvicorn src.main:app --reload --host 0.0.0.0
```

Open **http://localhost:8000** (or `http://<your-ip>:8000` for network access).

Default access key: `intel2026`

## Project Structure

```
src/
├── main.py                 # FastAPI app, auth routes, startup
├── auth.py                 # Access key middleware + session management
├── database.py             # SQLAlchemy engine + session
├── models.py               # ORM models (Holding, Alert, Watchlist, etc.)
├── routers/                # 15 API route modules
│   ├── market.py           # Live ticker + featured stocks
│   ├── screener.py         # Stock/ETF screener + watchlist
│   ├── stock_detail.py     # Per-stock detail + history + news
│   ├── portfolio.py        # Holdings CRUD + performance
│   ├── israeli_funds.py    # IL fund explorer API
│   ├── alerts.py           # Price alert CRUD + trigger check
│   └── ...                 # comparison, news, calendar, education, etc.
├── schemas/                # Pydantic request/response models
└── services/               # Business logic
    ├── market_data.py      # yfinance integration, caching, batch fetch
    ├── funder_scraper.py   # Live scraper for funder.co.il
    ├── screener.py         # Multi-factor screening + signals
    ├── recommendations.py  # Profile-based scoring engine
    └── ...

static/
├── index.html              # Single-page app shell
├── login.html              # Access key login page
├── style.css               # Dark theme (2200+ lines)
└── js/                     # 18 modular JS files
    ├── app.js, api.js      # Navigation + API client
    ├── market.js            # Live ticker + sparklines
    ├── screener.js          # Screener UI + detail panels
    ├── il-funds.js          # Israeli funds explorer
    └── ...
```

## Documentation

- `AGENTS.md` — Architecture docs for AI-assisted development
- `PROGRESS.md` — Development progress tracking
- `.cursor/rules/` — Cursor IDE rules for consistent AI behavior
