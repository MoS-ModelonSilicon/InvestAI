"""Monitor deploy + scheduler, then test all 12 advisor combos."""

import urllib.request, json, http.cookiejar, time, random

proxy = urllib.request.ProxyHandler({"https": "http://proxy-dmz.intel.com:911"})
opener = urllib.request.build_opener(proxy)
BASE = "https://investai-utho.onrender.com"
TARGET_VERSION = "ce93c28"

print(f"Waiting for version {TARGET_VERSION} to deploy...")
deployed_at = None
for i in range(40):
    time.sleep(30)
    try:
        req = urllib.request.Request(f"{BASE}/health")
        r = opener.open(req, timeout=15)
        data = json.loads(r.read())
        v = data.get("version", "?")
        cr = data.get("cache_ready", "?")
        ce = data.get("cache_entries", "?")
        combos = data.get("advisor_combos", {})
        diag = data.get("advisor_diag", None)
        cached = sum(1 for x in combos.values() if x) if isinstance(combos, dict) else "?"
        t = (i + 1) * 30
        marker = " <<< NEW" if v == TARGET_VERSION and not deployed_at else ""
        print(f"[{t}s] v={v} ready={cr} entries={ce} combos={cached}/12{marker}")

        if v == TARGET_VERSION and not deployed_at:
            deployed_at = t

        if isinstance(diag, dict) and diag:
            for k, val in sorted(diag.items()):
                print(f"  {k}: {val}")

        # Wait for all 12 combos to be cached
        if isinstance(combos, dict) and cached == 12:
            print("\nALL 12 COMBOS CACHED! Running full test...")
            break

        # Timeout: 15 min after deploy
        if deployed_at and (t - deployed_at) >= 900:
            print(f"\nTimeout: {cached}/12 combos after 15 min. Testing anyway...")
            break
    except Exception as e:
        print(f"[{(i + 1) * 30}s] {e}")

# Test all 12 combos with auth
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(proxy, urllib.request.HTTPCookieProcessor(cj))
email = f"bench{random.randint(10000, 99999)}@test.com"
reg_data = json.dumps({"email": email, "password": "TestPass123!", "name": "Bench"}).encode()
req = urllib.request.Request(f"{BASE}/auth/register", data=reg_data, headers={"Content-Type": "application/json"})
try:
    r = op.open(req, timeout=15)
    print(f"Registered {email}: {r.status}")
except urllib.error.HTTPError as e:
    print(f"Register: {e.code}")

results = []
for risk in ["balanced", "conservative", "aggressive"]:
    for period in ["1m", "3m", "6m", "1y"]:
        url = f"{BASE}/api/advisor/analyze?amount=10000&risk={risk}&period={period}"
        req = urllib.request.Request(url)
        t0 = time.time()
        try:
            r = op.open(req, timeout=120)
            body = r.read().decode()
            dt = time.time() - t0
            d = json.loads(body)
            n = len(d.get("rankings", []))
            bt = bool(d.get("backtest", {}).get("dates"))
            results.append(f"{risk:14s}/{period}: 200 {dt:.1f}s  rankings={n} backtest={bt}")
        except urllib.error.HTTPError as e:
            dt = time.time() - t0
            results.append(f"{risk:14s}/{period}: {e.code} {dt:.1f}s")

print("\n=== RESULTS ===")
for r in results:
    print(r)
ok = sum(1 for r in results if ": 200 " in r)
print(f"\nPassing: {ok}/12")
