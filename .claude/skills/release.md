# Skill: Release & Deploy Procedure

## Pre-Deploy Checklist

- [ ] All smoke tests pass locally
- [ ] No hardcoded secrets in code (`grep -r "password\|secret\|api_key" src/ --include="*.py"`)
- [ ] Requirements up to date (`requirements.txt`)
- [ ] AGENTS.md updated if endpoints changed
- [ ] `render.yaml` reflects any new env vars

## Deploy to Render

1. Ensure Intel proxy is configured: `git config --global http.proxy http://proxy-dmz.intel.com:911`
2. Push to `master` branch on GitHub: `git push origin master`
3. **CI Gate runs automatically** — smoke tests + lint must pass
4. **Verify CI passes** — check the GitHub Actions status:
   - Fetch https://github.com/MoS-ModelonSilicon/InvestAI/actions/workflows/pr-tests.yml
   - Find the run matching your commit SHA
   - Confirm status shows "completed successfully"
   - If CI **fails**: read the run logs, fix the issue, commit, push, and re-check
   - Do NOT consider the task done until CI shows green
5. If CI passes: Render deploys (auto-deploy or via `RENDER_DEPLOY_HOOK`)
6. **Verify live site** — after ~2 min, confirm the change works at https://investai-utho.onrender.com
7. Watch build logs in Render dashboard
6. First request after deploy triggers:
   - Database auto-migration (new tables/columns)
   - Default admin seed (from `ADMIN_EMAIL`/`ADMIN_PASSWORD`)
   - Cache restore from PostgreSQL (`persistence.py`)
   - Background warmer startup (refreshes every 15 min)
   - **Smart advisor warm-up**: scan once → replicate to 4 period keys → pre-compute 12 risk×period analyses (~2-3 min)

## CI Pipeline (`.github/workflows/pr-tests.yml`)

| Job | Blocking? | Purpose |
|-----|-----------|--------|
| `smoke-tests` | **YES** | API smoke tests — if these fail, deploy is skipped |
| `lint` | **YES** | Ruff lint + import verification |
| `type-check` | No | Mypy advisory only |
| `deploy` | — | Triggers Render deploy hook (only after smoke-tests + lint pass) |

**To fully gate deploys on CI:**
1. In Render dashboard → Settings → disable "Auto-Deploy"
2. Copy Deploy Hook URL from Render → Settings
3. Add as GitHub secret: `RENDER_DEPLOY_HOOK`

**Key lesson**: Never use `continue-on-error: true` on smoke-tests — it makes the CI gate advisory (failures hidden as green). The `type-check` and `ruff format` jobs use it intentionally because they're advisory.

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
