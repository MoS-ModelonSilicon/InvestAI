# run.ps1 — InvestAI local development server
# Usage: .\run.ps1 [-Port 8091]

param(
    [int]$Port = 8091
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ── Intel proxy (auto-detected) ──
$env:HTTP_PROXY  = "http://proxy-dmz.intel.com:911"
$env:HTTPS_PROXY = "http://proxy-dmz.intel.com:912"
$env:USE_INTEL_PROXY = "1"
$env:NO_PROXY = "127.0.0.1,localhost"

# ── Kill any existing server on this port ──
Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# ── Clean slate (optional: reset DB) ──
# Remove-Item finance.db -Force -ErrorAction SilentlyContinue

Write-Host "Starting InvestAI on http://127.0.0.1:$Port ..." -ForegroundColor Cyan
python -m uvicorn src.main:app --host 127.0.0.1 --port $Port
