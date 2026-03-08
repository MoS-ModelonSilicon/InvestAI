# InvestAI — Ship Pipeline

> One command to go from code changes → green CI → merged PR → deployed → verified live.

## Quick Start

```powershell
# 1. Make your changes in VS Code (or ask Copilot to implement them)
# 2. Run the pipeline:
.\ship.ps1 "feat: dark mode toggle"

# That's it. Go get coffee. ☕
# When you come back: issue created, PR merged, deployed, E2E tested.
```

Or press **Ctrl+Shift+B** in VS Code → type your commit title → done.

## The 9-Phase Pipeline

```
YOU: "feat: add DCA calculator"
 │
 ▼
┌──────────────────────────────────────────────────────────────────┐
│  PHASE 0 — Preflight                                             │
│  Verify: on master, changes exist, gh + claude CLI ready, proxy  │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 1 — Parse                                                 │
│  Extract type/title → generate branch name + labels              │
│  "feat: DCA calculator" → feat/dca-calculator-20260308           │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 2 — GitHub Issue                                          │
│  Create issue with description + checklist tracking pipeline     │
│  → Issue #42: "feat: DCA calculator"                             │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 3 — Branch + Commit + Push                                │
│  Create feature branch, commit with "closes #42", push to origin │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 4 — Pull Request                                          │
│  Create PR linked to issue, with pipeline status in body         │
│  → PR #43: "feat: DCA calculator"                                │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 5 — CI Gate + Auto-Fix Loop (max 3 attempts)             │
│                                                                  │
│  ┌─ Wait for CI Gate (smoke tests + lint + type-check)          │
│  │   ├─ ✅ CI passes → continue to Phase 6                      │
│  │   └─ ❌ CI fails:                                            │
│  │       ├─ Fetch failed job logs from GitHub API                │
│  │       ├─ Comment on issue: "fixing attempt 1/3..."           │
│  │       ├─ Run Claude Code locally (uses Pro subscription)      │
│  │       │   → reads CLAUDE.md, diagnoses, fixes, verifies      │
│  │       ├─ Commit fix → push → loop back to CI wait            │
│  │       └─ After 3 failures → abort + comment on issue         │
│  └────────────────────────────────────────────────────────────── │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 6 — Auto-Merge                                            │
│  Squash-merge PR into master, delete feature branch              │
│  (skip with -NoMerge flag for manual review)                     │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 7 — Staging Deploy Wait                                   │
│  Wait ~2.5 min for staging to deploy from master                 │
│  Pings staging site to detect when deploy is ready               │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 8 — E2E Verification on Staging                            │
│  Run E2E smoke tests against staging                             │
│  tests/test_live_site.py --live-url staging-url                  │
│  Results posted to the GitHub Issue                              │
├──────────────────────────────────────────────────────────────────┤
│  PHASE 9 — Close Issue                                           │
│  If E2E passes → close issue as completed                        │
│  If E2E fails → leave open, production NOT promoted              │
│  Note: Production promote happens via nightly auto-promote       │
└──────────────────────────────────────────────────────────────────┘
 │
 ▼
🎉 DONE — Feature delivered, tested, deployed, verified.
```

## Usage

### Basic

```powershell
# Feature
.\ship.ps1 "feat: dark mode toggle"

# Bug fix
.\ship.ps1 "fix: cache key mismatch on advisor page"

# With description (appears in the GitHub Issue)
.\ship.ps1 "feat: DCA calculator" -Description "Add a Dollar Cost Averaging calculator that shows optimal recurring investment schedules."

# Performance improvement
.\ship.ps1 "perf: lazy-load chart data on scroll"
```

### Options

```powershell
.\ship.ps1 "feat: example" `
    -NoMerge              # Don't auto-merge, leave PR for review
    -MaxFixAttempts 5     # Allow 5 Claude fix attempts (default: 3)
    -CITimeoutMin 20      # Wait 20 min for CI (default: 12)
    -DeployWaitSec 300    # Wait 5 min for Render (default: 150)
    -LiveUrl "http://localhost:8091"  # Test against local instead
```

### VS Code Integration

| Action | How |
|---|---|
| Ship (full pipeline) | `Ctrl+Shift+B` → type commit title |
| Ship (no auto-merge) | `Ctrl+Shift+P` → "Run Task" → "Ship (no auto-merge)" |
| Run local server | `Ctrl+Shift+P` → "Run Task" → "Run local server" |

## The Full Development Workflow

### 1. You Request a Feature (in VS Code Chat)

> "Add a Dollar Cost Averaging calculator page. It should let users input a stock ticker, amount, and frequency, then show a chart of historical DCA returns."

Copilot/Claude in the chat:
- Researches the codebase
- Plans the architecture
- Implements the feature (router, service, schema, JS page)
- Runs local checks (ruff, mypy)

### 2. You Ship It (One Command)

```powershell
.\ship.ps1 "feat: DCA calculator" -Description "Dollar Cost Averaging calculator with historical return chart"
```

### 3. The Pipeline Takes Over

Everything happens automatically:

```
[Phase 0] ✅ Preflight checks passed
[Phase 1] ✅ Type: feat | Branch: feat/dca-calculator-20260308
[Phase 2] ✅ Created Issue #42
[Phase 3] ✅ Committed and pushed
[Phase 4] ✅ Created PR #43
[Phase 5] ⏳ Waiting for CI Gate...
           ❌ CI failed — ruff found unused import
           🔧 Auto-fix attempt 1/3...
           ✅ Claude fixed: removed unused import
           ⏳ Waiting for CI Gate (retry)...
           ✅ CI Gate passed! (attempt 1)
[Phase 6] ✅ PR #43 merged to master
[Phase 7] ⏳ Waiting for Render deploy...
           ✅ Deploy complete
[Phase 8] ✅ E2E tests passed on live site
[Phase 9] ✅ Issue #42 closed

═══════════════════════════════════════════════
  🎉 SHIP COMPLETE — feat: DCA calculator
  Issue:  #42
  PR:     #43
  Branch: feat/dca-calculator-20260308
═══════════════════════════════════════════════
```

### 4. The Audit Trail

Every step is logged to the GitHub Issue:

> **Issue #42: feat: DCA calculator**
> - 🔗 PR #43 created
> - 🔧 CI failed (Run #12345). Starting auto-fix attempt 1/3...
> - ✅ CI Gate passed (attempt 1)
> - 🔀 PR #43 auto-merged to master
> - 🚀 Waiting for Render deploy...
> - 🧪 Running E2E tests...
> - ✅ E2E verification passed
> - ✅ **Closed** — delivery complete

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  VS Code                                                     │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Chat    │→ │ Copilot  │→ │ Code     │                   │
│  │ Request │  │ Implement│  │ Changes  │                   │
│  └─────────┘  └──────────┘  └────┬─────┘                   │
│                                   │                          │
│                         Ctrl+Shift+B or                      │
│                         .\ship.ps1 "feat: ..."               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ship.ps1 (local PowerShell)                                 │
│                                                              │
│  ┌──────┐  ┌────────┐  ┌──────┐  ┌────┐  ┌──────────────┐ │
│  │Issue │→ │Branch+ │→ │ PR   │→ │Push│→ │ CI Watch     │ │
│  │Create│  │Commit  │  │Create│  │    │  │ + Auto-Fix   │ │
│  └──────┘  └────────┘  └──────┘  └────┘  └──────┬───────┘ │
│                                                   │          │
│            ┌──────────────────────────────────────┘          │
│            │ CI fails? Run Claude Code locally (free)        │
│            │ (reads CLAUDE.md, fixes, verifies, pushes)      │
│            └──────────────────────────────────────┐          │
│                                                   ▼          │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │Auto-Merge │→ │ Staging      │→ │ E2E Staging Test    │  │
│  │(squash)   │  │ Deploy Wait  │  │ (Playwright)        │  │
│  └───────────┘  └──────────────┘  └──────────┬──────────┘  │
│                                               │              │
│                                     ┌─────────┴─────────┐   │
│                                     │ Close Issue #N     │   │
│                                     │ 🎉 Ship Complete   │   │
│                                     └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                   External Services
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────┐
        │ GitHub   │ │ GitHub   │ │ Render       │
        │ Issues   │ │ Actions  │ │ (deploy)     │
        │ (audit)  │ │ (CI)     │ │              │
        └──────────┘ └──────────┘ └──────────────┘
```

## CI Gate Jobs

The PR triggers the existing CI Gate workflow (`.github/workflows/pr-tests.yml`):

| Job | Blocking? | What it checks |
|---|---|---|
| `smoke-tests` | **YES** | API smoke tests with TestClient |
| `lint` | **YES** | Ruff lint + format + import check |
| `type-check` | Advisory | Mypy type checking |
| `deploy-staging` | — | Confirms staging will auto-deploy (only on master) |

## Auto-Fix: How Claude Code Works Locally

When CI fails, the script:

1. **Fetches logs** — `gh run view <id> --log-failed` gets the exact error output
2. **Builds a prompt** — includes the logs + instructions to read CLAUDE.md
3. **Runs Claude Code** — `claude -p "..."` with restricted tool access
   - Uses your **logged-in session** (Pro subscription, no API key needed)
   - Can only edit files, run ruff/mypy/pytest — no network, no secrets
4. **Commits the fix** — if Claude changed any files, commits and pushes
5. **Re-triggers CI** — the push to the branch re-triggers the CI Gate

Allowed tools for auto-fix:
```
Edit, Read, Write,
Bash(ruff*), Bash(mypy*), Bash(python*), Bash(pip*),
Bash(cat*), Bash(grep*), Bash(find*), Bash(head*), Bash(tail*), Bash(wc*)
```

## E2E Verification

After merge + deploy, the script runs `tests/test_live_site.py` against the real production URL with a focused `-k` filter:

```
test_login_page_loads or test_stock_detail_opens or test_dca_page_loads or test_dashboard_loads or test_market_page
```

This selects **4 critical-path tests** (not the full 105-test suite — that's for nightly). The filter uses `test_dashboard_loads` (not `test_dashboard`) to avoid accidentally matching `test_dashboard_api` and other API health tests.

### 401 Auto-Recovery

The `TestAPIHealth._fetch()` helper includes automatic 401 recovery. If a fetch returns 401 (stale auth cookie after deploy — e.g., `INVESTAI_SECRET` regenerated), it calls `_reauth()` to re-login via the browser and retries. This makes API health tests resilient to Render restarts.

### What it catches

- Deploy-time issues (missing env vars, migration failures)
- Environment differences (Render vs local)
- Feature regressions on the live site
- Stale auth cookies after deploy (via auto-recovery)

If E2E fails, the issue stays open and the nightly pipeline will also flag it.

## Nightly Safety Net

Even after `ship.ps1` completes, the nightly pipeline (`nightly-tests.yml`) runs every night at 2 AM UTC:

- Full browser-based test suite against the live site
- Auto-creates GitHub Issues on failure
- Auto-closes issues when tests pass again
- Triggers the cloud-based Claude Auto-Fix workflow (if API credits are funded)

## Prerequisites

| Tool | Check | Install |
|---|---|---|
| `gh` CLI | `gh auth status` | `winget install GitHub.cli` |
| `claude` CLI | `claude --version` | `npm install -g @anthropic-ai/claude-code` |
| Claude login | `claude` (opens browser) | One-time: sign in with Anthropic account |
| Git proxy | `git config --global http.proxy` | Auto-set by ship.ps1 |
| Playwright | `playwright install chromium` | `pip install playwright && playwright install` |
| Python deps | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` |

## File Map

```
finance-tracker/
├── ship.ps1                         # ← THE PIPELINE SCRIPT
├── run.ps1                          # Local dev server
├── CLAUDE.md                        # Claude Code project context
├── docs/
│   ├── ship-pipeline.md             # ← THIS DOCUMENT
│   ├── architecture.md              # System architecture
│   └── runbooks/
│       ├── render-deployment.md     # Render deploy guide
│       └── adding-market-regions.md
├── .vscode/
│   └── tasks.json                   # Ctrl+Shift+B integration
├── .github/workflows/
│   ├── pr-tests.yml                 # CI Gate (triggered by PR)
│   ├── nightly-tests.yml            # Nightly regression (2 AM UTC)
│   └── claude-fix.yml               # Cloud-based auto-fix (needs API credits)
└── tests/
    ├── test_api_smoke.py            # Fast smoke tests (CI Gate)
    ├── test_e2e.py                  # Full browser E2E (local)
    └── test_live_site.py            # Live site E2E (production)
```

## Conventional Commit Types

| Prefix | When to use | Auto-label |
|---|---|---|
| `feat:` | New feature | `enhancement` |
| `fix:` | Bug fix | `bug` |
| `perf:` | Performance improvement | `performance` |
| `security:` | Security fix | `security` |
| `test:` | Test changes | `enhancement` |
| `docs:` | Documentation | `enhancement` |
| `ci:` | CI/CD changes | `enhancement` |
| `refactor:` | Code restructure | `enhancement` |
