# InvestAI - Personal Investment Advisory App

A web application that helps you discover stocks, ETFs, and mutual funds based on your risk profile, screen instruments with rich filters, and get personalized portfolio recommendations.

## Features

- **Risk Profile Wizard** -- 6-step questionnaire that calculates your risk score and investor profile (Very Conservative → Aggressive)
- **Stock & Fund Screener** -- filter by asset type, sector, market cap, P/E ratio, dividend yield, beta. Quick presets for common strategies.
- **Personalized Recommendations** -- allocation pie chart + scored instrument cards based on your profile. Match percentage, risk badges, and reasoning for each pick.
- **Financial Dashboard** -- income/expense tracking, monthly trend charts, category breakdown, budget progress bars
- **Transaction Management** -- full CRUD with filtering by type, category, and date range
- **Budget Tracking** -- monthly limits per category with color-coded warnings

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite |
| Market Data | yfinance |
| Frontend | Vanilla HTML/CSS/JS, Chart.js |

## Getting Started

```bash
cd finance-tracker
pip install -r requirements.txt
python -m uvicorn src.main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

## Project Structure

```
src/
├── main.py             # FastAPI app entry point
├── database.py         # SQLAlchemy engine + session
├── models.py           # All ORM models
├── routers/            # API route handlers
├── schemas/            # Pydantic request/response models
└── services/           # Business logic (risk scoring, market data, screener, recommendations)

static/
├── index.html          # Single-page app
├── style.css           # Dark theme styles
└── js/                 # Modular JS (api, dashboard, transactions, budgets, profile, screener, recommendations)
```

## Documentation

- `AGENTS.md` -- Full architecture docs for AI-assisted development
- `PROGRESS.md` -- Development progress tracking
- `.cursor/rules/` -- Cursor IDE rules for consistent AI behavior
