# src/services/ — Service Layer Gotchas

## Golden Rule

Services contain business logic ONLY. No `Request` objects, no `Response` objects, no HTTP status codes. They accept `db: Session` + plain types, return data or raise exceptions.

## Market Data (`market_data.py`, `data_provider.py`, `finnhub_client.py`)

### Rate Limits — THIS WILL BREAK YOUR APP
- **Finnhub free tier: 60 API calls per minute**
- `finnhub_client.py` has a rate limiter — ALWAYS use it, never call Finnhub directly
- NEVER put Finnhub calls inside loops over the symbol universe (280+ symbols)
- The background warmer batches requests carefully to stay under limits

### Yahoo Finance Auto-Disable
- `data_provider.py` tracks failures per symbol
- After 3+ consecutive failures: Yahoo is auto-disabled for 30-minute cooldown
- `DISABLE_YAHOO` env var forces Finnhub-only mode
- Don't manually disable Yahoo without setting the env var — the cooldown handles it

### Cache Architecture
- `market_data.py` owns all cache dicts (in-memory)
- Cache keys: `quote:{symbol}`, `info:{symbol}`, `sparkline:{symbol}`
- Background warmer thread refreshes every 15 minutes
- `persistence.py` snapshots critical cache entries to PostgreSQL for survival across deploys

### Warmer Startup Sequence
1. `restore_all_caches()` loads from PostgreSQL → populates in-memory cache
2. Background warmer starts → refreshes stale entries
3. Scanners start → use cached data, don't re-fetch

**If you break this order, the first 15-30 minutes after deploy will have no market data.**

## Technical Analysis (`technical_analysis.py`)

- 1100+ lines — intentionally large, pure math, self-contained
- Implements: RSI, MACD, Bollinger Bands, Stochastic, ATR, OBV, ADX, Ichimoku, Fibonacci
- All functions take price arrays, return indicator values — no side effects
- Don't split this unless adding a fundamentally new category of analysis

## Scan Services (`smart_advisor.py`, `trading_advisor.py`, `value_scanner.py`)

- These run in background threads scanning the entire stock universe
- Results stored in `persistence.py` → `ScanResult` table
- Progress is tracked and reported to frontend (progress bars)
- **Memory sensitive**: each scan loads data for 280+ symbols — watch RSS on Render

### Scan Result Persistence Pattern
```python
# After scan completes:
save_scan_result("trading_advisor", results_dict)  # → PostgreSQL

# On startup:
cached = load_scan_result("trading_advisor")  # ← PostgreSQL
if cached:
    _results = cached  # Populate in-memory store
```

### Smart Advisor — CRITICAL GOTCHAS

**`scan_and_score(period)` does NOT use `period` for computation.**
The `period` parameter only affects the cache key (`advisor:scan:{period}`). The actual candle fetch always uses `CANDLE_LOOKBACK_DAYS` (constant). So scanning "1y" vs "6m" produces identical results. The scheduler scans ONCE and replicates results to all period cache keys.

**Cache key type normalization is mandatory.**
FastAPI parses `amount` as `float`, scheduler passes `int`. The cache key is `f"advisor:full:{amount}:{risk}:{period}"` — float 10000.0 ≠ int 10000 in the string. `run_full_analysis()` normalizes with `amount = int(amount)` at the top. If you add new cached functions with numeric params, always normalize types before building keys.

**Pre-warming covers 12 combos (3 risks × 4 periods) with default amount 10000.**
Custom amounts (e.g., 50000) compute fresh on first request, but the heavy `scan_and_score` is already cached so it's still fast (~2-5s vs 30+s cold).

**Full warm-up sequence** (`background_scheduler.py`):
1. `scan_and_score("1y")` — one heavy scan (40-80 candle fetches)
2. Copy scan results to `advisor:scan:6m`, `advisor:scan:3m`, `advisor:scan:1m` cache keys
3. `run_full_analysis()` for each of 12 combos — these reuse the cached scan, so they're fast
4. Total warm-up: ~2-3 min after Render starts

## Israeli Funds (`funder_scraper.py`, `israeli_funds.py`)

- Scrapes funder.co.il in real-time
- Has static JSON fallback if scrape fails (`static/data/funds_fallback.json`)
- Hebrew text handling: ensure UTF-8 throughout
- Fund data includes: name, manager, fee, return, type, kosher status

## Picks Tracker (`picks_tracker.py`)

- Reads Discord messages from `discord_archive/` JSON files
- Parses stock picks using regex patterns
- Evaluates P&L against current prices via market data service
- Results cached and persisted like scan results
