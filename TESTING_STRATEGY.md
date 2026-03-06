# InvestAI — Automated Testing & Self-Healing CI Strategy

## Current State

| Asset | Details |
|-------|---------|
| **Test framework** | pytest + Playwright (browser E2E) |
| **Test suites** | `test_e2e.py` (~25 classes, local+remote), `test_live_site.py` (~20 classes, remote) |
| **Total test classes** | ~45, covering login, dashboard, transactions, budgets, screener, portfolio, alerts, DCA, etc. |
| **Deployment** | Render (render.yaml), auto-deploy from git push |
| **CI/CD** | **None** — tests run manually from terminal |
| **Test modes** | Local server (`:8091`) or deployed site (`--live-url`) |

---

## Proposed Architecture: 3-Layer Testing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: TRIGGER                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │  Nightly  │  │ On Push  │  │ On PR    │  │  Manual   │  │
│  │  (cron)   │  │ (CI)     │  │ (gate)   │  │ (button)  │  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬─────┘  │
└────────┼─────────────┼─────────────┼─────────────┼──────────┘
         └─────────────┴─────────────┴─────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    LAYER 2: EXECUTE                         │
│                                                             │
│  ① Spin up server (local or use --live-url)                 │
│  ② Run pytest suite (parallelized by class)                 │
│  ③ Collect results → JUnit XML + HTML report + screenshots  │
│  ④ Generate structured failure report (JSON)                │
│                                                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                     ┌────────▼────────┐
                     │  All passed?    │──── YES ──→ ✅ Done, notify
                     └────────┬────────┘
                              │ NO
┌─────────────────────────────▼───────────────────────────────┐
│                    LAYER 3: AUTO-FIX                        │
│                                                             │
│  ① Parse failure report (test name, error, screenshot)      │
│  ② Feed to AI agent (Copilot / Claude API / local LLM)     │
│  ③ Agent reads relevant source files + test code            │
│  ④ Agent generates a fix (code patch)                       │
│  ⑤ Apply patch → re-run failed tests only                   │
│  ⑥ If pass → auto-commit on branch `autofix/<date>`        │
│  ⑦ Open PR for human review                                │
│  ⑧ If fail → escalate (notification with full report)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Option A: GitHub Actions (Recommended for Cloud)

**Best for:** Repo hosted on GitHub, want free CI minutes, industry standard.

### How it works
- GitHub Actions runs on a schedule (cron) or on every push/PR
- Uses Ubuntu runners with Playwright pre-installed
- Tests against the live Render deployment or a spun-up local server
- Uploads test artifacts (HTML reports, screenshots, JUnit XML)

### Pros
- Free for public repos (2,000 min/month for private)
- Native GitHub integration (PR checks, status badges, artifacts)
- Playwright has first-class GitHub Actions support
- Can trigger Render deploys and wait for them
- Secrets management for API keys

### Cons
- Needs internet access from runner (Finnhub API, yfinance)
- Intel proxy not relevant (runs in GitHub cloud)
- Limited control over runner environment

### Proposed Workflow

```yaml
# .github/workflows/nightly-tests.yml
name: Nightly Regression

on:
  schedule:
    - cron: '0 2 * * *'          # 2 AM UTC nightly
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:              # manual trigger button

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: playwright install chromium
      - name: Run E2E tests against live site
        run: |
          pytest tests/test_live_site.py \
            --live-url https://investai-utho.onrender.com \
            --junitxml=results/junit.xml \
            --html=results/report.html \
            -v --tb=long 2>&1 | tee results/output.log
        env:
          FINNHUB_API_KEY: ${{ secrets.FINNHUB_API_KEY }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: results/
```

---

## Option B: Local Scheduled Runner (Best for Intel Environment)

**Best for:** Behind corporate proxy, want to test locally, full control.

### How it works
- A PowerShell scheduled task runs nightly on your machine (or a shared server)
- Starts the local server, runs tests, generates report
- Sends results via email/Teams webhook/Discord
- Can also test the live Render site

### Pros
- Works behind Intel proxy with no config changes
- Zero cost, uses existing machine
- Can test local code before pushing
- Full access to all tools (Copilot, git, etc.)

### Cons
- Machine must be on/awake
- Single point of failure
- Harder to share results with team

### Proposed Script

```powershell
# scripts/nightly-test.ps1
param(
    [string]$LiveUrl = "",    # empty = local server
    [switch]$AutoFix
)

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$resultsDir = "test-results/$timestamp"
New-Item -Path $resultsDir -ItemType Directory -Force

# Environment
$env:HTTP_PROXY  = "http://proxy-dmz.intel.com:911"
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912"
$env:NO_PROXY    = "127.0.0.1,localhost"
$env:FINNHUB_API_KEY = "your-key-here"

# Run tests
$pytestArgs = @(
    "tests/", "-v", "--tb=long",
    "--junitxml=$resultsDir/junit.xml",
    "--html=$resultsDir/report.html",
    "--screenshot=on"
)
if ($LiveUrl) { $pytestArgs += "--live-url", $LiveUrl }

python -m pytest @pytestArgs 2>&1 | Tee-Object "$resultsDir/output.log"
$exitCode = $LASTEXITCODE

# Parse results
$failures = Select-String -Path "$resultsDir/output.log" -Pattern "FAILED" |
    ForEach-Object { $_.Line }

if ($exitCode -ne 0 -and $AutoFix) {
    # Trigger AI auto-fix (see Layer 3)
    python scripts/autofix_agent.py --results "$resultsDir" --max-attempts 3
}

# Notify (webhook, email, etc.)
python scripts/notify.py --results "$resultsDir" --exit-code $exitCode
```

### Windows Task Scheduler Setup

```powershell
# Register as a nightly task (run once to set up)
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-File C:\...\finance-tracker\scripts\nightly-test.ps1 -AutoFix" `
    -WorkingDirectory "C:\...\finance-tracker"

$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

Register-ScheduledTask `
    -TaskName "InvestAI-NightlyTests" `
    -Action $action `
    -Trigger $trigger `
    -Description "Run E2E regression tests nightly"
```

---

## Option C: Hybrid (Recommended Overall)

Use **both** GitHub Actions AND local runner:

| Trigger | Runner | Target | Purpose |
|---------|--------|--------|---------|
| On push/PR | GitHub Actions | Live Render site | Gate merges |
| Nightly 2 AM | GitHub Actions | Live Render site | Catch regressions |
| On-demand | Local (PowerShell) | Local server | Dev testing |
| Weekly | Local | Live site | Deep regression + auto-fix |

---

## Layer 3: AI Auto-Fix Agent (The Self-Healing Part)

This is the most innovative part. An AI agent reads test failures and attempts to fix them.

### Architecture

```
test failure (JSON)
       │
       ▼
┌──────────────────┐
│  autofix_agent.py │
│                    │
│  1. Parse failure  │
│  2. Map to source  │─── reads src/ files, test code, error traces
│  3. Call AI API    │─── Claude API / OpenAI / local model
│  4. Get patch      │
│  5. Apply patch    │─── write changes to files
│  6. Re-run tests   │─── pytest --lf (last failed only)
│  7. If pass:       │
│     - git commit   │
│     - git push     │
│     - open PR      │
│  8. If fail:       │
│     - revert       │
│     - escalate     │
└──────────────────┘
```

### Implementation Approaches

#### Approach 1: Claude/OpenAI API Agent (Most Powerful)

```python
# scripts/autofix_agent.py (skeleton)
"""
AI-powered auto-fix agent.
Reads test failures, uses an LLM to generate fixes, validates them.
"""

import json, subprocess, os, sys
from pathlib import Path

def parse_failures(junit_xml_path: str) -> list[dict]:
    """Parse JUnit XML into structured failure records."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(junit_xml_path)
    failures = []
    for tc in tree.iter("testcase"):
        fail = tc.find("failure")
        if fail is not None:
            failures.append({
                "test_class": tc.get("classname"),
                "test_name": tc.get("name"),
                "message": fail.get("message", ""),
                "traceback": fail.text or "",
            })
    return failures

def map_failure_to_files(failure: dict) -> list[str]:
    """Heuristic: extract file paths from traceback."""
    import re
    paths = re.findall(r'File "([^"]+)"', failure["traceback"])
    # Filter to project files only
    return [p for p in paths if "finance-tracker" in p]

def ask_ai_for_fix(failure: dict, source_files: dict[str, str]) -> str:
    """Send failure context to AI, get back a unified diff."""
    import anthropic  # or openai

    prompt = f"""
    A test is failing. Fix the SOURCE CODE (not the test) to make it pass.

    **Test:** {failure['test_class']}::{failure['test_name']}
    **Error:** {failure['message']}
    **Traceback:**
    {failure['traceback']}

    **Relevant source files:**
    {json.dumps(source_files, indent=2)}

    Return ONLY a JSON object with file patches:
    {{"patches": [{{"file": "path", "old": "exact old text", "new": "new text"}}]}}
    """

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text

def apply_and_verify(patches, failed_test: str) -> bool:
    """Apply patches, run the specific failed test, return True if it passes."""
    # Apply patches...
    result = subprocess.run(
        [sys.executable, "-m", "pytest", failed_test, "-x", "--tb=short"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def git_commit_and_pr(failures_fixed: list[str]):
    """Commit fixes and create a PR."""
    branch = f"autofix/{__import__('datetime').date.today()}"
    subprocess.run(["git", "checkout", "-b", branch])
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m",
                     f"🤖 Auto-fix: {len(failures_fixed)} test(s) repaired"])
    subprocess.run(["git", "push", "origin", branch])
    # Use gh CLI to open PR
    subprocess.run(["gh", "pr", "create",
                     "--title", f"🤖 Auto-fix {len(failures_fixed)} failures",
                     "--body", "Automated fixes from nightly regression."])
```

#### Approach 2: Copilot Chat CLI Integration

Use GitHub Copilot's CLI to generate fixes:

```bash
# For each failure, ask Copilot to fix it
gh copilot suggest "fix this test failure: <error message>"
```

#### Approach 3: Cursor/Windsurf Agent Rules

Create an agent rule file that Cursor can use as a "fix test failures" workflow:

```markdown
# .cursor/rules/autofix.mdc
When test failures are detected:
1. Read the JUnit XML at test-results/latest/junit.xml
2. For each failure, read the traceback and identify the source file
3. Fix the source code (not the test) to resolve the error
4. Run only the previously-failed tests to verify
5. If verified, commit with message "🤖 autofix: <test name>"
```

---

## Concrete Recommendation: What to Build

### Phase 1 — Foundation (Week 1) ✅ Start Here

| Task | Effort |
|------|--------|
| Add `pytest-html` and `pytest-json-report` to requirements.txt | 5 min |
| Create GitHub Actions workflow for push/PR/nightly | 1 hour |
| Add JUnit XML + HTML report generation | 15 min |
| Add test result artifact upload | 15 min |
| Create `scripts/nightly-test.ps1` for local scheduled runs | 30 min |

### Phase 2 — Reporting & Notifications (Week 2)

| Task | Effort |
|------|--------|
| Create `scripts/notify.py` — send results to Discord/Teams/email | 1 hour |
| Add Slack/Discord webhook integration | 30 min |
| Create a test dashboard (simple HTML page with historical results) | 2 hours |
| Badge in README showing test status | 5 min |

### Phase 3 — AI Auto-Fix Agent (Week 3-4)

| Task | Effort |
|------|--------|
| Create `scripts/autofix_agent.py` with failure parser | 2 hours |
| Integrate Claude/OpenAI API for fix generation | 3 hours |
| Add patch application + verification loop | 2 hours |
| Add git commit + PR creation | 1 hour |
| Add safety guardrails (max changes, revert on fail, human review required) | 2 hours |

### Phase 4 — Polish (Ongoing)

| Task | Effort |
|------|--------|
| Flaky test detection (mark tests that fail intermittently) | 2 hours |
| Test parallelization (`pytest-xdist`) | 1 hour |
| Screenshot-on-failure for visual regression | 1 hour |
| Historical trend tracking (pass rate over time) | 3 hours |

---

## Test Categories & Run Schedule

```
┌─────────────────────┬──────────┬───────────┬──────────────┐
│ Suite               │ Duration │ Schedule  │ Trigger      │
├─────────────────────┼──────────┼───────────┼──────────────┤
│ Smoke (5 key tests) │ ~1 min   │ Every PR  │ push/PR      │
│ Core E2E            │ ~5 min   │ On merge  │ push to main │
│ Full Regression     │ ~15 min  │ Nightly   │ cron 2AM     │
│ Live Site Deep      │ ~20 min  │ Weekly    │ cron Sunday  │
│ Performance/Load    │ ~10 min  │ Weekly    │ cron Sunday  │
└─────────────────────┴──────────┴───────────┴──────────────┘
```

### Marking tests by tier:

```python
# conftest.py - add markers
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: critical path tests (~1 min)")
    config.addinivalue_line("markers", "core: core feature E2E tests (~5 min)")
    config.addinivalue_line("markers", "deep: deep regression tests (~15 min)")
```

```python
# Usage in tests:
@pytest.mark.smoke
class TestLogin: ...

@pytest.mark.core
class TestDashboardFlow: ...

@pytest.mark.deep
class TestScreenerAPI: ...
```

```bash
# Run by tier:
pytest -m smoke              # PR gate
pytest -m "smoke or core"    # on merge
pytest                       # nightly (everything)
```

---

## Safety Guardrails for Auto-Fix

The auto-fix agent must have strict guardrails:

1. **Never modify test files** — Only fix source code, not tests (tests define expected behavior)
2. **Max 3 files changed per fix** — Prevents runaway changes
3. **Max 50 lines changed** — Keeps patches small and reviewable
4. **Always create a branch** — Never commit directly to `main`
5. **Require PR approval** — Human must review before merge
6. **Revert on secondary failure** — If fix breaks other tests, roll back
7. **Rate limit** — Max 3 auto-fix attempts per nightly run
8. **Audit log** — Record every AI prompt, response, and applied patch

---

## Required Dependencies to Add

```
# requirements-test.txt (new file, test-only deps)
pytest
playwright
pytest-playwright
pytest-html           # HTML reports
pytest-json-report    # Machine-readable JSON results
pytest-xdist          # Parallel test execution
anthropic             # Claude API for auto-fix (Phase 3)
```

---

## Summary: Which Option to Pick?

| Your Situation | Recommended |
|----------------|-------------|
| Repo is on GitHub, want standard CI | **Option A** (GitHub Actions) |
| Behind Intel proxy, want local control | **Option B** (Local runner) |
| Want the best of both worlds | **Option C** (Hybrid) ✅ |
| Want AI auto-fix ASAP | Start with Phase 1 + Phase 3 |

**My recommendation:** Start with **Option C (Hybrid)** — set up GitHub Actions for the cloud CI pipeline and keep the local PowerShell runner for development. Then add the AI auto-fix agent in Phase 3 for the self-healing loop. This gives you:

- ✅ Nightly regression on live site (GitHub Actions)
- ✅ PR gating (no broken code merges)
- ✅ Local testing with Intel proxy (PowerShell script)
- ✅ AI-powered auto-fix with human review (Claude API agent)
- ✅ Full audit trail and safety guardrails
