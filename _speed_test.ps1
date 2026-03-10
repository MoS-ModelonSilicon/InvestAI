$ErrorActionPreference = "Continue"
$prodUrl = "https://investai-utho.onrender.com"

Write-Host "=== DCA Dashboard Speed Test ==="
Write-Host "Target: $prodUrl"
Write-Host ""

# Step 1: Wake up the server
Write-Host "Waking up server..."
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $r = Invoke-WebRequest -Uri "$prodUrl/login" -UseBasicParsing -TimeoutSec 120
    $sw.Stop()
    Write-Host "  Server up: HTTP $($r.StatusCode) in $($sw.ElapsedMilliseconds)ms"
} catch {
    $sw.Stop()
    Write-Host "  Wake-up request took $($sw.ElapsedMilliseconds)ms (may have timed out): $($_.Exception.Message)"
    Write-Host "  Continuing anyway..."
}

# Step 2: Login
Write-Host ""
Write-Host "Logging in..."
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = '{"email":"testuser-e2e@example.com","password":"TestPass123"}'
try {
    $loginResp = Invoke-WebRequest -Uri "$prodUrl/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -WebSession $session -TimeoutSec 60 -UseBasicParsing
    Write-Host "  Login: HTTP $($loginResp.StatusCode)"
    $cookies = $session.Cookies.GetCookies($prodUrl)
    Write-Host "  Cookies: $($cookies.Count) received"
} catch {
    Write-Host "  Login FAILED: $($_.Exception.Message)"
    exit 1
}

# Step 3: Speed test
Write-Host ""
Write-Host "=== Running 5 DCA dashboard requests ==="
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
        Write-Host "  Run ${i}: ${ms}ms - $plans plans, $opps opps, $allocs allocations"
    } catch {
        $sw.Stop()
        Write-Host "  Run ${i}: FAILED after $($sw.ElapsedMilliseconds)ms - $($_.Exception.Message)"
    }
}

if ($times.Count -gt 0) {
    $avg = [math]::Round(($times | Measure-Object -Average).Average)
    $minT = ($times | Measure-Object -Minimum).Minimum
    $maxT = ($times | Measure-Object -Maximum).Maximum
    Write-Host ""
    Write-Host "=== Results ==="
    Write-Host "  Avg: ${avg}ms"
    Write-Host "  Min: ${minT}ms"
    Write-Host "  Max: ${maxT}ms"
    Write-Host "  Runs: $($times.Count)/5 succeeded"
}
