# Full PostgreSQL Migration Plan

## Problem

On **Render free tier**, the filesystem is **ephemeral** — every redeploy, sleep, or restart wipes:

1. **SQLite database** (`finance.db`) — users, transactions, portfolios, alerts, DCA plans, watchlists, etc.
2. **In-memory caches** — scan results, market data, news, candle data, picks tracker results

This means every patch/deploy **destroys all user data and takes 15-30 min** to rebuild scan caches.

---

## Solution: External PostgreSQL (Supabase Free Tier)

Move everything to an **externally hosted PostgreSQL** database that lives outside Render's container.

### Service Signup Required

**Supabase** — [https://supabase.com](https://supabase.com)

1. Create a free account (GitHub or email)
2. Create a new project (pick any region, set a DB password)
3. Go to **Settings → Database → Connection string → URI**
4. Copy the connection string (looks like `postgresql://postgres.xxxx:password@aws-0-region.pooler.supabase.com:6543/postgres`)
5. In **Render dashboard** → your service → **Environment** → Add:
   - Key: `DATABASE_URL`
   - Value: `<your Supabase connection string>`

**Supabase free tier includes:**
- 500 MB database storage
- Unlimited API requests
- 2 projects
- No expiration (unlike Render's 90-day PostgreSQL)

---

## What Gets Persisted

| Data | Before | After |
|---|---|---|
| Users, Transactions, Categories, Budgets | SQLite (lost on redeploy) | External PostgreSQL (permanent) |
| Risk Profiles, Watchlists, Holdings | SQLite (lost on redeploy) | External PostgreSQL (permanent) |
| Alerts, DCA Plans, Password Resets | SQLite (lost on redeploy) | External PostgreSQL (permanent) |
| Value scanner results | In-memory dict (lost on restart) | PostgreSQL `scan_results` table |
| Trading advisor results | In-memory dict (lost on restart) | PostgreSQL `scan_results` table |
| Market data cache (quotes, sparklines) | In-memory dict (lost on restart) | PostgreSQL `scan_results` (priority symbols) |
| News cache | In-memory via `market_data._cache` | PostgreSQL `scan_results` |
| Smart advisor scan | In-memory via `market_data._cache` | PostgreSQL `scan_results` |
| Picks tracker results | In-memory dict (lost on restart) | PostgreSQL `scan_results` table |
| Rate limiter / Yahoo flags | In-memory (auto-rebuilds) | Not persisted (not needed) |

---

## Files Changed

| File | Change |
|---|---|
| `requirements.txt` | Added `psycopg2-binary` |
| `src/database.py` | Read `DATABASE_URL` env var, fallback to SQLite for local dev |
| `src/models.py` | Added `ScanResult` model (key/data/updated_at) |
| `src/services/persistence.py` | **NEW** — save/load/restore scan results from DB |
| `src/services/market_data.py` | Restore cache from DB on warm, save priority keys |
| `src/services/value_scanner.py` | Save scan results after completion, restore on startup |
| `src/services/trading_advisor.py` | Save scan results after completion, restore on startup |
| `src/services/picks_tracker.py` | Save evaluated picks after computation, restore on startup |
| `src/services/background_scheduler.py` | Periodic cache snapshot to DB |
| `src/main.py` | Call `restore_all_caches()` on startup before scheduler |
| `render.yaml` | Added `DATABASE_URL` env var placeholder |

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   API Call   │────▶│  In-Memory   │◀────│   Background    │
│  (fast read) │     │    Cache     │     │   Scheduler     │
└─────────────┘     └──────┬───────┘     └────────┬────────┘
                           │ save                  │ scan
                           ▼                       ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │  PostgreSQL  │     │  Finnhub/Yahoo  │
                    │  (Supabase)  │     │     APIs        │
                    └──────────────┘     └─────────────────┘
                           ▲
                           │ restore on startup
                    ┌──────┴───────┐
                    │  App Startup │
                    └──────────────┘
```

**Dual-write pattern**: In-memory cache is the hot path (fast reads). DB is the backup. On restart, DB → in-memory before scheduler runs.

---

## Local Development

No changes needed — when `DATABASE_URL` is not set, the app falls back to SQLite (`finance.db`) exactly as before.
