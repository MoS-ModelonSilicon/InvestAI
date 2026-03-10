# Solve GitHub Issue

Fully resolve a GitHub issue: read it, implement the code, test, and ship to production.

## Input
- `issueNumber` — The GitHub issue number to solve (e.g. `114`)

## Steps

### 1. Read the issue
Run in terminal:
```
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912"
gh issue view $ISSUE_NUMBER --repo MoS-ModelonSilicon/InvestAI
```
Extract the title, description, labels, and acceptance criteria.

### 2. Research the codebase
- Read `finance-tracker/CLAUDE.md` for architecture, rules, and conventions
- Read the area-specific CLAUDE.md files (`src/CLAUDE.md`, `static/CLAUDE.md`, `tests/CLAUDE.md`)
- Search the codebase for relevant existing code (routers, services, schemas, JS modules)
- Understand the current implementation before changing anything

### 3. Implement the feature or fix
Follow all rules from CLAUDE.md:
- **Backend**: router in `src/routers/`, service in `src/services/`, schema in `src/schemas/`
- **Frontend**: vanilla JS in `static/js/`, HTML section in `static/index.html`, CSS in `static/style.css`
- **Tests**: add smoke tests in `tests/test_api_smoke.py`
- Vanilla JS only (no React/Vue/Angular)
- No raw SQL — SQLAlchemy ORM only
- Keep files under 400 lines
- Business logic in services/, HTTP layer in routers/
- Filter all user data by `user_id`

### 4. Verify locally
Run these checks in the terminal:
```
cd finance-tracker
python -m ruff format src/ tests/
python -m ruff check src/ tests/
python -m mypy src/ --config-file=pyproject.toml
$env:TESTING = "1" ; python -m pytest tests/test_api_smoke.py -q --tb=short
```
Fix any errors before proceeding.

### 5. Ship it
Run the ship pipeline which handles branch → PR → CI → auto-fix → merge → deploy → E2E:
```
cd finance-tracker
git add -A
powershell -ExecutionPolicy Bypass -File .\ship.ps1 "<type>: <title> (closes #<issueNumber>)"
```
Where `<type>` is `feat`, `fix`, `perf`, etc. based on the issue.

### 6. Verify on live site
After ship completes, confirm the deployment:
```
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912"
Invoke-RestMethod -Uri "https://investai-utho.onrender.com/health" -TimeoutSec 30
```
Check that the version SHA matches the merged commit.
