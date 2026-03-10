$ErrorActionPreference = "Continue"
$prodUrl = "https://investai-utho.onrender.com"

Write-Host "=== DCA Dashboard Speed Test (with plans) ==="
Write-Host "Target: $prodUrl"
Write-Host ""

# Login
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = '{"email":"testuser-e2e@example.com","password":"TestPass123"}'
$null = Invoke-WebRequest -Uri "$prodUrl/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -WebSession $session -TimeoutSec 120 -UseBasicParsing
Write-Host "Logged in"

# Create 3 DCA plans
$symbols = @("AAPL", "MSFT", "GOOG")
foreach ($sym in $symbols) {
    $body = @{symbol=$sym; monthly_budget=200; dip_threshold=-15; dip_multiplier=2; is_long_term=$true; notes="speed test"} | ConvertTo-Json
    try {
        $null = Invoke-WebRequest -Uri "$prodUrl/api/dca/plans" -Method POST -Body $body -ContentType "application/json" -WebSession $session -TimeoutSec 60 -UseBasicParsing
        Write-Host "  Created plan: $sym"
    } catch {
        Write-Host "  Plan $sym skipped (exists or error)"
    }
}

# DCA Dashboard speed test
Write-Host ""
Write-Host "=== DCA Dashboard (3 plans, live market data) ==="
$times = @()
for ($i = 1; $i -le 5; $i++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-WebRequest -Uri "$prodUrl/api/dca/dashboard" -WebSession $session -TimeoutSec 120 -UseBasicParsing
        $sw.Stop()
        $ms = $sw.ElapsedMilliseconds
        $times += $ms
        $data = $resp.Content | ConvertFrom-Json
        $plans = @($data.plans).Count
        $opps = @($data.opportunities).Count
        $allocs = @($data.monthly_allocation.allocations).Count
        Write-Host "  Run ${i}: ${ms}ms - $plans plans, $opps opps, $allocs allocs"
    } catch {
        $sw.Stop()
        Write-Host "  Run ${i}: FAILED $($sw.ElapsedMilliseconds)ms"
    }
}
$avg = [math]::Round(($times | Measure-Object -Average).Average)
$minT = ($times | Measure-Object -Minimum).Minimum
$maxT = ($times | Measure-Object -Maximum).Maximum
Write-Host ""
Write-Host "  Dashboard: avg=${avg}ms, min=${minT}ms, max=${maxT}ms"

# DB-only endpoint for comparison
Write-Host ""
Write-Host "=== Plans endpoint (DB-only, no market calls) ==="
$ptimes = @()
for ($i = 1; $i -le 3; $i++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $resp = Invoke-WebRequest -Uri "$prodUrl/api/dca/plans" -WebSession $session -TimeoutSec 60 -UseBasicParsing
    $sw.Stop()
    $ptimes += $sw.ElapsedMilliseconds
    Write-Host "  Run ${i}: $($sw.ElapsedMilliseconds)ms"
}
$pavg = [math]::Round(($ptimes | Measure-Object -Average).Average)
Write-Host "  DB-only avg: ${pavg}ms"

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "  Network round-trip: ~${pavg}ms"
Write-Host "  DCA dashboard total: ~${avg}ms"
Write-Host "  Server processing time: ~$($avg - $pavg)ms"

# Cleanup
Write-Host ""
Write-Host "Cleaning up test plans..."
$plansResp = Invoke-WebRequest -Uri "$prodUrl/api/dca/plans" -WebSession $session -TimeoutSec 60 -UseBasicParsing
$allPlans = $plansResp.Content | ConvertFrom-Json
foreach ($p in $allPlans) {
    if ($p.notes -eq "speed test") {
        try {
            $null = Invoke-WebRequest -Uri "$prodUrl/api/dca/plans/$($p.id)" -Method DELETE -WebSession $session -TimeoutSec 30 -UseBasicParsing
            Write-Host "  Deleted $($p.symbol)"
        } catch {
            Write-Host "  Failed to delete $($p.symbol)"
        }
    }
}
Write-Host "Done!"
