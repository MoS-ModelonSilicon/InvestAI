# ADR-003: Market Data Fallback Strategy

**Date**: 2026-03-03  
**Status**: Accepted  
**Deciders**: Yaron Klein

## Context

Need reliable market data for 280+ symbols across 12 regions. No single free API covers everything reliably.

## Decision

Use a **dual-provider strategy** with automatic failover:
1. **Yahoo Finance** (via `yfinance`) as primary — free, no API key, broad coverage
2. **Finnhub** as fallback — requires API key, 60 calls/min rate limit

## Implementation

`data_provider.py` manages the fallback:
- Tries Yahoo first
- On failure: increments counter per symbol
- After 3+ consecutive failures: auto-disables Yahoo for 30-minute cooldown
- Falls back to `finnhub_client.py` which enforces rate limiting

`market_data.py` provides the caching layer:
- Live quotes: 90-second TTL
- Full stock info: 15-minute TTL
- Sparklines: 15-minute TTL
- Background warmer refreshes all priority symbols every 15 minutes

## Gotchas

- **Finnhub 60/min**: Never call in loops over the full symbol universe (280+)
- **Yahoo batch API**: Use `yf.download()` for multiple symbols (single HTTP request)
- **Market hours**: Outside trading hours, quotes are stale — cache is still valid
- **Proxy**: Intel corporate network requires `HTTP_PROXY`/`HTTPS_PROXY` for all external calls
- **`DISABLE_YAHOO`**: Env var to force Finnhub-only mode (useful for debugging)
