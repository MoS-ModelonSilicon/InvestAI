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

- 1400+ lines — intentionally large, pure math, self-contained
- Implements: RSI, MACD, Bollinger Bands, Stochastic, ATR, OBV, ADX, Ichimoku, Fibonacci, Z-score, Relative Strength, Volume Anomaly, Divergence Detection, Cup & Handle
- All functions take price arrays, return indicator values — no side effects
- `composite_score()` weights: MACD 0.22, RSI 0.18, SMA 0.18, Bollinger 0.14, Stochastic 0.10, OBV 0.08, Advanced 0.10
- Don't split this unless adding a fundamentally new category of analysis

## Pattern Detection (`pattern_detection.py`)

- 1300+ lines — chart patterns + candlestick patterns, pure math
- **Chart patterns**: Double Top/Bottom, Head & Shoulders (+ inverse), Bull/Bear Flags, Ascending/Descending/Symmetric Triangles, Rising/Falling Wedges, Triple Top/Bottom
- **Candlestick patterns**: 21 patterns (Doji, Hammer, Engulfing, Morning/Evening Star, Three White Soldiers, etc.)
- **Gaps**: Breakaway, Runaway, Exhaustion, Common — classified by context
- Every pattern returns `viz_points: [{idx, value, label}]` — used by frontend to annotate charts
- Candlestick patterns return `viz: {type, shape/start/end, color}` for rendering
- Master function: `detect_all_patterns(opens, highs, lows, closes, volumes)` → `{chart_patterns, candlestick_patterns, gaps, pattern_score, pattern_summary}`
- `pattern_score` is a float (typically -1.0 to +1.0) aggregating all detected pattern signals

## Advanced Indicators (`advanced_indicators.py`)

- 770+ lines — 14 indicators beyond the classic set
- VWAP, Keltner Channels, TTM Squeeze, Parabolic SAR, Williams %R, Chaikin Money Flow, Donchian Channels, Aroon, CCI, Heikin-Ashi, Force Index, Linear Regression Channel, Momentum, Rate of Change
- Uses lazy imports (`from src.services.technical_analysis import ema, atr`) to avoid circular dependencies
- Master function: `compute_all_advanced(opens, highs, lows, closes, volumes)` → all indicator arrays + `advanced_score` + `advanced_signals[]`
- Aggregate scoring: TTM Squeeze (weight 0.3), SAR (0.2), Williams %R, CMF, Aroon, CCI, Regression (0.1-0.15 each)

## Scan Services (`smart_advisor.py`, `trading_advisor.py`, `value_scanner.py`)

- These run in background threads scanning the entire stock universe
- Results stored in `persistence.py` → `ScanResult` table
- Progress is tracked and reported to frontend (progress bars)
- **Memory sensitive**: each scan loads data for 280+ symbols — watch RSS on Render

### Trading Advisor — Two Code Paths
- **`_analyze_stock()`** (line ~65) — lightweight background scan, uses classic indicators ONLY. This runs for all 280+ symbols.
- **`get_single_analysis()`** (line ~645) — deep analysis for a single stock, called when user clicks a pick card. This calls ALL three engines (technical_analysis + pattern_detection + advanced_indicators) and builds the `decision_breakdown` + `patterns` payload.
- The background scan does NOT use the new pattern/indicator engines (too expensive for 280+ symbols). Only the on-demand detail view does.
- Score merging: `adjusted_raw = composite_raw + (pattern_score × 0.08) + (advanced_score × 0.07)` — these boost factors are tuned to slightly influence but not dominate the score.

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
