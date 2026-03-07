# Runbook: Adding Market Data for New Regions

## Steps

1. Find symbol list for the region (exchange suffix matters: `.T` for Tokyo, `.HK` for Hong Kong, etc.)
2. Add symbols to `UNIVERSE` or region dict in `src/services/screener.py`
3. Add region to screener filter options
4. Update `src/services/market_data.py` warmer to include new symbols in pre-fetch
5. Verify Finnhub supports the exchange (some international symbols need premium tier)
6. Test: `curl http://localhost:8000/api/screener?region=<new_region>`

## Gotchas

- Finnhub free tier doesn't support all exchanges — test before adding
- Yahoo Finance handles most international symbols but suffix format varies
- Adding 50+ symbols increases warmer cycle time — monitor memory usage
- Background warmer fetches ALL symbols — consider prioritizing frequently-accessed ones
