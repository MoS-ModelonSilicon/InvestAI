# Skill: CI Monitoring During Ship Pipeline

## Rule: Always Check GitHub CI Logs — Never Wait Blindly

When the ship pipeline (`ship.ps1`) is running, **actively monitor CI status on GitHub** instead of just sleeping and polling the background terminal. This catches failures faster and avoids wasted time.

## How to Check CI Logs

### 1. Use `gh` CLI to check run status

```powershell
# Set proxy (Intel network)
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912"
$env:HTTP_PROXY = "http://proxy-dmz.intel.com:911"

# List recent CI runs
gh run list --repo MoS-ModelonSilicon/InvestAI --limit 5 --json databaseId,status,conclusion,name,headBranch

# Watch a specific run (blocks until complete)
gh run watch <run-id> --repo MoS-ModelonSilicon/InvestAI

# View failed job logs
gh run view <run-id> --repo MoS-ModelonSilicon/InvestAI --log-failed
```

### 2. Check the ship pipeline terminal output

```powershell
# Use get_terminal_output to check the background ship process
# Look for: "CI Gate failed", "auto-fix attempt", "CI Gate passed"
```

### 3. If CI fails — diagnose immediately

Don't just wait for auto-fix. Read the failure logs to understand the root cause:

```powershell
# Get the failed run ID from ship output or gh run list
gh run view <run-id> --repo MoS-ModelonSilicon/InvestAI --log-failed 2>&1 | Select-Object -Last 50
```

Common CI failures and fixes:

| Failure | Fix |
|---------|-----|
| `ruff format --check` fails | Run `python -m ruff format src/ tests/` locally before shipping |
| `ruff check` lint errors | Run `python -m ruff check src/ tests/ --fix` |
| Smoke test failure | Run `python -m pytest tests/test_api_smoke.py -x -v` locally first |
| Import error | Missing dependency in `requirements.txt` |

## Workflow: Ship Pipeline Monitoring

1. **Before shipping**: Run `ruff format` and `ruff check` locally to pre-empt lint failures
2. **Start ship**: Launch `ship.ps1` in background terminal
3. **Monitor actively**: Check terminal output every 30s for phase changes
4. **On CI failure**: Immediately fetch logs with `gh run view --log-failed`
5. **Don't duplicate auto-fix**: If ship's auto-fix is already running, check its progress instead of manually fixing the same issue
6. **After merge**: Monitor E2E phase — transient network failures on live site are expected and logged to the issue
7. **E2E 401 errors**: `TestAPIHealth._fetch()` auto-recovers from 401 by re-logging in via `_reauth()`. If 401 persists after retry, check that `INVESTAI_SECRET` env var is set (not ephemeral) on Render

## Pre-Ship Lint Check (Recommended)

Always run this before `ship.ps1` to avoid the most common CI failure:

```powershell
cd finance-tracker
python -m ruff format src/ tests/
python -m ruff check src/ tests/ --fix
python -m pytest tests/test_api_smoke.py -x -q
```

If all three pass, the ship pipeline should clear CI on the first attempt.
