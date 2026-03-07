# Skill: Release & Deploy Procedure

## Pre-Deploy Checklist

- [ ] All smoke tests pass locally
- [ ] No hardcoded secrets in code (`grep -r "password\|secret\|api_key" src/ --include="*.py"`)
- [ ] Requirements up to date (`requirements.txt`)
- [ ] AGENTS.md updated if endpoints changed
- [ ] `render.yaml` reflects any new env vars

## Deploy to Render

1. Push to `master` branch on GitHub
2. Render auto-deploys from `master`
3. Watch build logs in Render dashboard
4. First request after deploy triggers:
   - Database auto-migration (new tables/columns)
   - Default admin seed (from `ADMIN_EMAIL`/`ADMIN_PASSWORD`)
   - Cache restore from PostgreSQL (`persistence.py`)
   - Background warmer startup (15-min cycle)

## Post-Deploy Verification

1. Hit the live site: https://investai-utho.onrender.com
2. Check login works
3. Check market data loads (screener, featured stocks)
4. Verify admin panel (`/api/admin/stats`)
5. Check GitHub Actions nightly tests (runs at 2 AM UTC)

## Rollback

- Render supports instant rollback to previous deploy
- If DB schema changed: check if rollback is safe (new nullable columns are fine, dropped columns are not)

## Render Gotchas

- **Free tier**: 512 MB RAM — `LowMemoryMiddleware` prevents OOM
- **Ephemeral filesystem**: SQLite DB is lost on redeploy — PostgreSQL (Supabase) is the permanent store
- **Cold starts**: First request after sleep takes 30-60s — nightly tests wake the site
- **No persistent disk**: Static file uploads won't survive redeploys

## Android Release

See `android/PUBLISH.md` for Play Store release process. Separate from backend deployment.

## Environment Variables (Render)

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `FINNHUB_API_KEY` | Yes | Market data API |
| `INVESTAI_SECRET` | Yes | JWT signing (stable across restarts) |
| `ADMIN_EMAIL` | Yes | Default admin account |
| `ADMIN_PASSWORD` | Yes | Default admin password |
| `LOW_MEMORY` | Recommended | `1` for aggressive memory management |
| `PRODUCTION` | Recommended | `1` to disable /docs endpoint |
