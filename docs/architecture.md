# InvestAI — System Architecture

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Vanilla JS   │  │ Android App  │  │ API Consumers    │   │
│  │ SPA (28 mods)│  │ (WebView)    │  │ (tests, curl)    │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
└─────────┼──────────────────┼───────────────────┼─────────────┘
          │ HTTP/REST        │ HTTP/REST         │
┌─────────┼──────────────────┼───────────────────┼─────────────┐
│         ▼                  ▼                   ▼             │
│  ┌─────────────────────────────────────────────────────┐     │
│  │               FastAPI Application                    │     │
│  │  ┌───────────┐  ┌──────────┐  ┌────────────────┐   │     │
│  │  │ Auth MW   │→ │ Security │→ │ LowMemory MW   │   │     │
│  │  │ (JWT)     │  │ Headers  │  │ (OOM prevent)  │   │     │
│  │  └───────────┘  └──────────┘  └────────────────┘   │     │
│  │                                                      │     │
│  │  ┌─────────────────────────────────────────────┐    │     │
│  │  │          22 API Routers                      │    │     │
│  │  │  admin │ alerts │ portfolio │ screener │ ... │    │     │
│  │  └──────────────────┬──────────────────────────┘    │     │
│  │                     ▼                                │     │
│  │  ┌─────────────────────────────────────────────┐    │     │
│  │  │          20+ Service Modules                 │    │     │
│  │  │  market_data │ technical │ advisor │ scanner │    │     │
│  │  └──────────┬──────────────┬───────────────────┘    │     │
│  │             │              │                         │     │
│  └─────────────┼──────────────┼─────────────────────────┘     │
│                │              │                               │
│  ┌─────────────▼──┐  ┌───────▼──────────────┐               │
│  │   SQLAlchemy   │  │   External APIs       │               │
│  │   ORM Layer    │  │  ┌─────────────────┐  │               │
│  │                │  │  │ Finnhub (primary)│  │               │
│  │  10 Models     │  │  │ 60 calls/min    │  │               │
│  │  User, Holding │  │  ├─────────────────┤  │               │
│  │  Alert, DCA... │  │  │ Yahoo (fallback) │  │               │
│  │                │  │  │ auto-disable     │  │               │
│  └───────┬────────┘  │  ├─────────────────┤  │               │
│          │           │  │ funder.co.il    │  │               │
│          ▼           │  │ IL fund scraper │  │               │
│  ┌──────────────┐    │  └─────────────────┘  │               │
│  │  Database    │    └───────────────────────┘               │
│  │  PostgreSQL  │                                            │
│  │  (Supabase)  │    ┌───────────────────────┐               │
│  │  or SQLite   │    │   Background Tasks     │               │
│  │  (local dev) │    │  • Cache warmer (15m)  │               │
│  └──────────────┘    │  • Trading scanner     │               │
│                      │  • Value scanner       │               │
│                      │  • Cache persistence   │               │
│                      └───────────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

## Request Flow

1. Request hits **AuthMiddleware** → checks JWT cookie → sets `request.state.user_id`
2. **Security headers middleware** adds OWASP headers
3. **LowMemoryMiddleware** checks RSS memory, triggers GC if needed
4. **Router** receives request, validates with Pydantic, calls service
5. **Service** executes business logic, queries DB or external APIs
6. **Response** flows back through middleware chain

## Data Flow: Market Data

```
User requests stock data
        │
        ▼
   In-memory cache hit? ──yes──→ Return cached data
        │ no
        ▼
   data_provider.py
        │
        ├── Try Yahoo Finance first
        │      │
        │      ├── Success → cache + return
        │      └── Failure → increment failure counter
        │              │
        │              └── 3+ failures → auto-disable Yahoo (30min cooldown)
        │
        └── Fallback to Finnhub
               │
               ├── Rate limiter (60/min)
               ├── Success → cache + return
               └── Failure → return error/empty
```

## Caching Strategy

| Cache | TTL | Storage | Warmed By |
|-------|-----|---------|-----------|
| Live quotes (SPY, QQQ, etc.) | 90 seconds | In-memory dict | Background warmer |
| Full stock info | 15 minutes | In-memory dict | On-demand + warmer |
| Sparkline coordinates | 15 minutes | In-memory dict | Background warmer |
| Scan results (value, trading) | Until next scan | In-memory + PostgreSQL | Background scanner |
| Israeli fund data | 1 hour | In-memory dict | On-demand |

## Authentication Flow

```
Register → bcrypt hash → DB → Set JWT cookie (httponly, secure, samesite=lax)
Login → verify bcrypt → Set JWT cookie
Every request → AuthMiddleware → decode JWT → set request.state.user_id
Logout → delete cookie
```

## Deployment Architecture

```
GitHub (master branch)
       │ push
       ▼
Render (auto-deploy)
       │
       ├── Build: pip install -r requirements.txt
       ├── Start: uvicorn src.main:app
       ├── Startup sequence:
       │     1. Create tables (auto-migrate)
       │     2. Seed admin user
       │     3. Restore caches from PostgreSQL
       │     4. Start background warmer thread
       │     5. Start scanner threads
       └── External services:
             ├── Supabase PostgreSQL (data persistence)
             ├── Finnhub API (market data)
             └── GitHub Actions (nightly E2E tests)
```
