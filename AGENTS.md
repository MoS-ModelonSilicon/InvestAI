# InvestAI - Investment Advisory Application

## Project Overview

InvestAI (formerly Finance Tracker) is a personal investment advisory web application. It helps users discover stocks, ETFs, and mutual funds to invest in based on their risk profile, provides screening tools with rich filters, and generates personalized portfolio recommendations.

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Python 3.14, FastAPI | REST API server |
| Database | SQLite via SQLAlchemy 2.0 | Persistent storage |
| Validation | Pydantic v2 | Request/response schemas |
| Market Data | yfinance | Stock/ETF/fund prices & fundamentals |
| Frontend | Vanilla HTML/CSS/JS | Single-page application |
| Charts | Chart.js 4.x | Dashboard & portfolio visualizations |

## Architecture

### Backend Structure

```
src/
├── main.py                  # FastAPI app, mounts all routers, startup events
├── database.py              # SQLAlchemy engine, session factory, Base
├── models.py                # All SQLAlchemy ORM models
├── routers/                 # API route handlers (one file per domain)
│   ├── categories.py
│   ├── transactions.py
│   ├── budgets.py
│   ├── dashboard.py
│   ├── profile.py           # Risk profile wizard endpoints
│   ├── screener.py          # Stock/fund screening endpoints
│   └── recommendations.py   # Personalized recommendations
├── schemas/                 # Pydantic models (one file per domain)
│   ├── categories.py
│   ├── transactions.py
│   ├── budgets.py
│   ├── dashboard.py
│   ├── profile.py
│   ├── screener.py
│   └── recommendations.py
└── services/                # Business logic (no HTTP concerns)
    ├── market_data.py       # yfinance wrapper with 15-min cache
    ├── screener.py          # Filtering/scoring logic
    ├── risk_profile.py      # Risk score calculation
    └── recommendations.py   # Portfolio allocation + instrument matching
```

### Frontend Structure

```
static/
├── index.html               # Single HTML file, all page sections
├── style.css                # Dark theme, responsive layout
└── js/
    ├── api.js               # Shared fetch helpers (get/post/put/del)
    ├── app.js               # Navigation, init, shared state
    ├── dashboard.js          # Dashboard charts & stats
    ├── transactions.js       # Transaction CRUD & filtering
    ├── budgets.js            # Budget management
    ├── profile.js            # Risk profile wizard UI
    ├── screener.js           # Stock screener filters & results
    └── recommendations.js    # Recommendation cards & allocation chart
```

### Data Flow

```
User → Frontend (JS) → REST API (FastAPI routers)
                            ↓
                     Services (business logic)
                       ↓              ↓
              SQLAlchemy Models    yfinance (market data)
                       ↓              ↓
                    SQLite DB     15-min cache dict
```

## Key Features

### 1. Risk Profile Wizard
- 6-step questionnaire: goal, timeline, monthly budget, experience, risk tolerance, income stability
- Produces a risk score (1-10) mapped to a profile label
- Profile stored in DB, used by screener and recommendations
- Profiles: Very Conservative (1-2), Conservative (3-4), Moderate (5-6), Growth (7-8), Aggressive (9-10)

### 2. Stock & Fund Screener
- Filters: asset type, sector, market cap, P/E ratio, dividend yield, beta, expense ratio
- Preset screeners: "Value Stocks", "High Dividend", "Growth Tech", "Low-Cost ETFs"
- Results table: sortable, with add-to-watchlist action
- Data pulled from yfinance, cached for 15 minutes

### 3. Personalized Recommendations
- Based on risk profile, recommends target allocation (stocks/bonds/cash %)
- Scores instruments by how well they match the profile
- Shows match percentage, key metrics, risk badge, reasoning
- Card-based UI with tabs (All/Stocks/ETFs/Bonds)

### 4. Financial Dashboard (original feature)
- Income/expense tracking with category breakdown
- Monthly trend bar chart, category doughnut chart
- Budget progress bars with color-coded warnings

## Database Models

- **Category**: id, name, color, type (income/expense) — pre-seeded defaults
- **Transaction**: id, amount, type, description, date, category_id
- **Budget**: id, category_id, monthly_limit
- **RiskProfile**: id, goal, timeline, monthly_investment, experience, risk_reaction, income_stability, risk_score, profile_label, created_at
- **Watchlist**: id, symbol, added_at

## API Patterns

- All routes live under `/api/` prefix
- Routers use `APIRouter(prefix="/api/...", tags=[...])` and are included in main.py
- Use `Depends(get_db)` for database sessions
- Return Pydantic response models with `from_attributes = True`
- HTTP 404 for not found, 400 for validation errors
- Market data endpoints may be slow (yfinance fetch); frontend shows loading states

## Adding a New Feature

1. Add SQLAlchemy model to `src/models.py`
2. Create Pydantic schemas in `src/schemas/<domain>.py`
3. Create service logic in `src/services/<domain>.py`
4. Create router in `src/routers/<domain>.py`
5. Include router in `src/main.py`
6. Add HTML section in `static/index.html`
7. Add JS module in `static/js/<domain>.js`
8. Add `<script>` tag in index.html
9. Add CSS for new components in `static/style.css`

## Important Constraints

- **File size**: Keep all files under 400 lines. Split if growing.
- **No frameworks on frontend**: Vanilla JS only (no React/Vue/Angular).
- **yfinance rate limits**: Cache aggressively (15-min TTL). Never call in loops without caching.
- **SQLite limitations**: Single-writer. Fine for single-user app.
- **Proxy required**: Intel corporate proxy needed for pip installs and external API calls. See `.cursor/rules/intel-proxy.mdc`.
