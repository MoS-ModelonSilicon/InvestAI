# Runbook: Render Deployment & Troubleshooting

## Environments

| Environment | URL | Auto-Deploy? | Database |
|-------------|-----|-------------|----------|
| **Production** | https://investai-utho.onrender.com | No (manual promote) | Supabase `investai` |
| **Staging** | https://finance-tracker-staging.onrender.com | Yes (on push to master) | Supabase `investai-staging` |

## Normal Deploy

1. Push to `master` on GitHub
2. **Staging** auto-deploys (build → install deps → start server)
3. First request triggers startup sequence (migrations, cache restore, warmer)
4. Nightly E2E runs against staging at 2 AM UTC
5. If tests pass → production auto-promoted via deploy hook

## Promoting to Production

| Method | How |
|--------|-----|
| **Automatic** | Nightly E2E passes on staging → deploy hook fires → production deploys |
| **Manual (GitHub)** | Actions → "Promote to Production" → Run workflow |
| **Manual (curl)** | `curl -X POST "$RENDER_PROD_DEPLOY_HOOK"` (see DEPLOY-KEYS.md) |

## Cold Start (Site Sleeping)

Render free tier sleeps after 15min inactivity. First request takes 30-60s.

**Fix**: Nightly GitHub Actions (`nightly-tests.yml`) wake the site at 2 AM UTC.

## OOM Kill (Out of Memory)

**Symptom**: Server crashes, restarts, "Instance exceeded memory limit"

**Check**:
- `/api/market/cache-status` — how big is the in-memory cache?
- Are multiple scans running simultaneously?

**Fix**:
- Set `LOW_MEMORY=1` env var → enables aggressive GC in `LowMemoryMiddleware`
- Reduce scan batch sizes in value_scanner/trading_advisor
- Check for memory leaks: large dicts not being cleared

## Database Connection Issues

**Symptom**: `OperationalError: could not connect to server`

**Check**:
- `DATABASE_URL` env var in Render dashboard
- Supabase project isn't paused (free tier pauses after 1 week inactivity)
- Connection string uses pooler port (6543) not direct (5432)

**Fix**: Log into Supabase, un-pause project, verify connection string.

## Market Data Not Loading

**Symptom**: Screener/featured stocks show empty or stale data

**Check**:
1. `/api/market/cache-status` — is warmer running?
2. Check Finnhub API key: `FINNHUB_API_KEY` env var
3. Is Yahoo auto-disabled? Check logs for "Yahoo Finance disabled"

**Fix**:
- Verify API key is valid at https://finnhub.io/dashboard
- Restart the service to re-enable Yahoo
- Check proxy settings if on corporate network

## Nightly Test Failures

**Symptom**: GitHub Issue auto-created titled "Nightly test failure"

**Check**:
1. Is the Render site actually running? (cold start issue)
2. Did the site redeploy and lose data? (PostgreSQL migration issue)
3. Is an external API down? (Finnhub/Yahoo outage)

**Fix**: Read the auto-created issue for specific failure details + log excerpt.

## Proxy Issues (Intel Network)

**Symptom**: External API calls timeout on corporate network

**Required env vars** (for the running app):
```bash
HTTP_PROXY=http://proxy-dmz.intel.com:911
HTTPS_PROXY=http://proxy-dmz.intel.com:912
NO_PROXY=localhost,127.0.0.1
USE_INTEL_PROXY=1
```

**Git push failing** (`Failed to connect to github.com port 443`):
```bash
git config --global http.proxy http://proxy-dmz.intel.com:911
```
This must be set on any Intel machine before `git push origin master` will work. It persists across sessions but may be cleared by IT policy or reinstalls.
