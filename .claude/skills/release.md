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

1. **Check Render deploy status** — query the Render API to confirm deploy is `live`:
   ```bash
   python _check_render.py
   ```
   Expected: `status=live` for the latest deploy matching your commit message.
   If `build_failed` or stuck `update_in_progress` > 5 min, check build logs via Render API.

2. **Verify new code is actually served** — curl the static assets to confirm:
   ```bash
   curl -s https://investai-utho.onrender.com/static/js/picks-tracker.js | head -5
   curl -s https://finance-tracker-staging.onrender.com/static/js/picks-tracker.js | head -5
   ```
   The response should contain the code you just shipped (not a cached old version).

3. **Hit the live site**: https://investai-utho.onrender.com
4. **Check login works**
5. **Check market data loads** (screener, featured stocks)
6. **Verify admin panel** (`/api/admin/stats`)
7. **Run E2E against live site**:
   ```powershell
   python -m pytest tests/test_live_site.py --live-url https://investai-utho.onrender.com -k "test_login_page_loads or test_dashboard_loads" -v
   ```
8. **Check GitHub Actions nightly tests** (runs at 2 AM UTC)

> **Critical:** A commit on `master` is NOT shipped until it's verified live. Always confirm the Render deploy status AND that the new code is being served before considering the feature delivered.

### Render Deploy Status Reference

| Status | Meaning |
|---|---|
| `live` | Successfully deployed and serving traffic |
| `update_in_progress` | Build/deploy is running (wait 2-3 min) |
| `build_failed` | Build error — check logs via API or Render dashboard |
| `deactivated` | Replaced by a newer deploy |

### Trigger Production Deploy Manually

Production has `autoDeploy: false`. If staging is green but prod hasn't deployed:
```bash
curl -X POST "https://api.render.com/deploy/srv-d6jcdsvgi27c73d2uta0?key=wnZP2EvMsZs"
```

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
