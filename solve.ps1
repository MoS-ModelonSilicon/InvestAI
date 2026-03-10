# ──────────────────────────────────────────────────────────────
# InvestAI — solve.ps1
#
# One-command ticket solver: reads a GitHub issue, implements
# the fix/feature via Claude Code, then ships it through the
# full pipeline (CI → merge → deploy → E2E verify).
#
# Usage:
#   .\solve.ps1 114          # solve issue #114
#   .\solve.ps1 114 -NoMerge # implement + CI, but leave PR open
#   .\solve.ps1 114 -DryRun  # implement only, don't ship
#
# Prerequisites:
#   - gh CLI authenticated (gh auth status)
#   - claude CLI logged in  (claude --version)
#   - git proxy configured  (Intel network)
# ──────────────────────────────────────────────────────────────

[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [int]$IssueNumber,                   # GitHub issue number, e.g. 114

    [switch]$NoMerge,                    # skip auto-merge (leave PR open for review)

    [switch]$DryRun,                     # implement only — don't run ship.ps1

    [int]$MaxFixAttempts = 3,            # max Claude auto-fix attempts (passed to ship.ps1)

    [string]$ProdUrl = "https://investai-utho.onrender.com"
)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

# ── Constants ──────────────────────────────────────────────
$Repo = "MoS-ModelonSilicon/InvestAI"

# ── Colors ─────────────────────────────────────────────────
function Write-Step  { param([string]$msg) Write-Host "`n▶ $msg" -ForegroundColor Cyan }
function Write-OK    { param([string]$msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn  { param([string]$msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Fail  { param([string]$msg) Write-Host "  ❌ $msg" -ForegroundColor Red }
function Write-Info  { param([string]$msg) Write-Host "  ℹ️  $msg" -ForegroundColor Gray }

# ══════════════════════════════════════════════════════════════
#  PHASE 1 — PREFLIGHT
# ══════════════════════════════════════════════════════════════

Write-Step "Phase 1: Preflight checks"

# Ensure Intel proxy
if (-not $env:HTTPS_PROXY) {
    $env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912"
    Write-Info "Set HTTPS_PROXY for Intel network"
}

# Ensure we're on master
$currentBranch = git rev-parse --abbrev-ref HEAD
if ($currentBranch -ne "master") {
    Write-Warn "Not on master (on: $currentBranch). Switching..."
    git stash --include-untracked 2>&1 | Out-Null
    git checkout master 2>&1 | Out-Null
    git pull origin master 2>&1 | Out-Null
}

# Make sure we're up-to-date
git pull origin master 2>&1 | Out-Null
Write-OK "On master, up-to-date"

# Verify tools
$ghOk = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "gh CLI not authenticated. Run: gh auth login"; exit 1 }
Write-OK "gh CLI authenticated"

$claudeOk = claude --version 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "claude CLI not found. Install: npm i -g @anthropic-ai/claude-code"; exit 1 }
Write-OK "claude CLI ready: $claudeOk"

# ══════════════════════════════════════════════════════════════
#  PHASE 2 — READ THE ISSUE
# ══════════════════════════════════════════════════════════════

Write-Step "Phase 2: Reading issue #${IssueNumber}"

$IssueJson = gh issue view $IssueNumber --repo $Repo --json title,body,labels,state 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Could not fetch issue #${IssueNumber} from $Repo"
    Write-Info $IssueJson
    exit 1
}

$Issue = $IssueJson | ConvertFrom-Json
$IssueTitle = $Issue.title
$IssueBody  = $Issue.body
$IssueState = $Issue.state
$Labels     = ($Issue.labels | ForEach-Object { $_.name }) -join ", "

if ($IssueState -eq "CLOSED") {
    Write-Warn "Issue #${IssueNumber} is already CLOSED: $IssueTitle"
    $yn = Read-Host "  Continue anyway? (y/N)"
    if ($yn -notin @("y","Y","yes")) { exit 0 }
}

Write-OK "Issue #${IssueNumber}: $IssueTitle"
Write-Info "Labels: $Labels"
Write-Info "Body: $($IssueBody.Substring(0, [Math]::Min(200, $IssueBody.Length)))..."

# ── Determine commit type from title or labels ──
$CommitType = "feat"
if ($IssueTitle -match "^(feat|fix|perf|docs|test|ci|security|refactor):") {
    $CommitType = $Matches[1]
} elseif ($Labels -match "bug") {
    $CommitType = "fix"
} elseif ($Labels -match "performance") {
    $CommitType = "perf"
}

# Build commit title: strip existing prefix if present, re-add normalized
$CleanTitle = $IssueTitle -replace "^(feat|fix|perf|docs|test|ci|security|refactor):\s*", ""
$CommitTitle = "${CommitType}: ${CleanTitle}"

Write-OK "Commit title: $CommitTitle"

# ══════════════════════════════════════════════════════════════
#  PHASE 3 — IMPLEMENT VIA CLAUDE CODE
# ══════════════════════════════════════════════════════════════

Write-Step "Phase 3: Implementing with Claude Code"

# Build the prompt with full issue context
$ClaudePrompt = @"
You are an expert engineer working on the InvestAI project.

FIRST: Read the CLAUDE.md file for full project context, rules, architecture, and conventions.
THEN: Read the relevant src/CLAUDE.md, static/CLAUDE.md, and tests/CLAUDE.md for area-specific rules.

YOUR TASK — Implement GitHub Issue #${IssueNumber}:

**Title:** $IssueTitle

**Description:**
$IssueBody

IMPLEMENTATION RULES:
1. Read CLAUDE.md first for project architecture and coding rules
2. Research the existing codebase before writing any code (read relevant files)
3. Implement the feature/fix completely:
   - Backend: router in src/routers/, service in src/services/, schema in src/schemas/
   - Frontend: vanilla JS in static/js/, HTML section in static/index.html, CSS in static/style.css
   - Tests: add smoke tests in tests/test_api_smoke.py
4. Follow all CLAUDE.md rules strictly:
   - Vanilla JS only (no React/Vue/Angular)
   - No raw SQL — use SQLAlchemy ORM
   - Keep files under 400 lines
   - Business logic in services/, HTTP in routers/
   - Filter all user data by user_id
5. After implementing, verify your work:
   - Run: ruff check src/ tests/ && ruff format src/ tests/
   - Run: mypy src/ --config-file=pyproject.toml
   - Run: TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short
6. Fix any lint, type, or test errors before finishing
7. Do NOT modify .github/, CLAUDE.md, or ship.ps1/solve.ps1

The commit message will be: "$CommitTitle (closes #${IssueNumber})"
"@

Write-Info 'Launching Claude Code (this may take a few minutes)...'

claude -p $ClaudePrompt `
    --allowedTools 'Edit,Read,Write,Bash(ruff*),Bash(mypy*),Bash(python*),Bash(pip*),Bash(cat*),Bash(grep*),Bash(find*),Bash(head*),Bash(tail*),Bash(wc*),Bash(ls*),Bash(cd*)' `
    2>&1 | Tee-Object -Variable ClaudeOutput | Out-Null

# ── Check if Claude made changes ──
$changes  = git diff --name-only
$newFiles = git ls-files --others --exclude-standard
$allChanges = @()
if ($changes)  { $allChanges += $changes }
if ($newFiles) { $allChanges += $newFiles }

$ClosesTag = 'closes #' + $IssueNumber
$ShipHint = '  .\ship.ps1 "' + $CommitTitle + ' ' + '(' + $ClosesTag + ')"'

if ($allChanges.Count -eq 0) {
    Write-Fail "Claude Code made no changes. Aborting."
    Write-Info "You can inspect the output and re-run, or implement manually then run:"
    Write-Info $ShipHint
    exit 1
}

Write-OK "Claude implemented changes in $($allChanges.Count) file(s):"
foreach ($f in $allChanges) { Write-Info "  $f" }

# ══════════════════════════════════════════════════════════════
#  PHASE 4 — LOCAL VERIFICATION
# ══════════════════════════════════════════════════════════════

Write-Step "Phase 4: Local verification"

# Format
Write-Info "Running ruff format..."
python -m ruff format src/ tests/ 2>&1 | Out-Null
Write-OK "Formatted"

# Lint
Write-Info "Running ruff check..."
$lintResult = python -m ruff check src/ tests/ 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Lint warnings (non-blocking):"
    Write-Info ($lintResult | Select-Object -Last 5 | Out-String)
}
else { Write-OK "Lint clean" }

# Type check
Write-Info "Running mypy..."
$mypyResult = python -m mypy src/ --config-file=pyproject.toml 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Type check issues (non-blocking):"
    Write-Info ($mypyResult | Select-Object -Last 5 | Out-String)
}
else { Write-OK "Type check clean" }

# Tests
Write-Info "Running smoke tests..."
$env:TESTING = "1"
$testResult = python -m pytest tests/test_api_smoke.py -q --tb=short 2>&1
$testExit = $LASTEXITCODE
if ($testExit -ne 0) {
    Write-Warn "Some tests failed:"
    Write-Info ($testResult | Select-Object -Last 10 | Out-String)
    $yn = Read-Host "  Continue to ship anyway? (y/N)"
    if ($yn -notin @("y","Y","yes")) {
        Write-Info "Aborting. Fix tests and run:"
        Write-Info $ShipHint
        exit 1
    }
}
else {
    $passLine = ($testResult | Select-String "passed") | Select-Object -Last 1
    Write-OK "Tests: $passLine"
}

# ══════════════════════════════════════════════════════════════
#  PHASE 5 — SHIP (or stop if -DryRun)
# ══════════════════════════════════════════════════════════════

if ($DryRun) {
    Write-Step "DryRun mode — stopping before ship"
    Write-OK "Changes are ready in your working tree."
    Write-Info "To ship manually, run:"
    Write-Info $ShipHint
    exit 0
}

Write-Step "Phase 5: Shipping via pipeline"

# Stage everything
git add -A 2>&1 | Out-Null

# Build ship args
$ShipTitle = $CommitTitle + ' ' + '(' + $ClosesTag + ')'
$shipArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", "$PSScriptRoot\ship.ps1",
    $ShipTitle
)
if ($NoMerge) { $shipArgs += "-NoMerge" }
$shipArgs += "-MaxFixAttempts"
$shipArgs += $MaxFixAttempts

Write-Info "Running: .\ship.ps1 $ShipTitle"

# Execute ship pipeline
& powershell @shipArgs
$ShipExit = $LASTEXITCODE

if ($ShipExit -ne 0) {
    Write-Fail "Ship pipeline exited with code $ShipExit"
    Write-Info "Check the output above for details."
    exit $ShipExit
}

# ══════════════════════════════════════════════════════════════
#  PHASE 6 — VERIFY ON LIVE SITE
# ══════════════════════════════════════════════════════════════

Write-Step "Phase 6: Verifying on live site"

# Wait a moment for production to catch up
Start-Sleep -Seconds 10

try {
    $health = Invoke-RestMethod -Uri "$ProdUrl/health" -TimeoutSec 30
    Write-OK "Live site version: $($health.version) | Status: $($health.status)"
}
catch {
    Write-Warn "Could not reach $ProdUrl/health — production may need manual promote"
}

# ══════════════════════════════════════════════════════════════
#  DONE
# ══════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  🎉 SOLVE COMPLETE — Issue #${IssueNumber}" -ForegroundColor Green
Write-Host "  $CommitTitle" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
