"""Fix prod ENVIRONMENT env var + re-check both sites."""
import requests
import time

proxies = {"http": "http://proxy-dmz.intel.com:911", "https": "http://proxy-dmz.intel.com:912"}
HEADERS = {"Authorization": "Bearer rnd_wKb6dejSU7BDZJDhPHUpL6vqVBEn", "Accept": "application/json", "Content-Type": "application/json"}
BASE_API = "https://api.render.com/v1"
PROD_SID = "srv-d6jcdsvgi27c73d2uta0"
STAGING_SID = "srv-d6mn2cma2pns73d9r23g"

# Fix prod ENVIRONMENT
print("=== Setting ENVIRONMENT=production on prod ===")
r = requests.put(f"{BASE_API}/services/{PROD_SID}/env-vars/ENVIRONMENT", headers=HEADERS, json={"value": "production"}, proxies=proxies, timeout=15)
print(f"Status: {r.status_code} Response: {r.text[:100]}")

# Wait a moment then check both sites
print("\nWaiting 5s for staging deploy to finish...")
time.sleep(5)

for label, url in [("STAGING", "https://finance-tracker-staging.onrender.com"), ("PRODUCTION", "https://investai-utho.onrender.com")]:
    print(f"\n=== {label} ===")
    try:
        r = requests.get(f"{url}/health", proxies=proxies, timeout=30)
        print(f"  /health: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            print(f"    version={d.get('version')} env={d.get('environment')} cache_ready={d.get('cache_ready')} entries={d.get('cache_entries')}")
    except Exception as e:
        print(f"  /health: ERROR {e}")

    try:
        r = requests.get(f"{url}/static/index.html", proxies=proxies, timeout=15)
        has_meta = '2026-03-08-staging-flow' in r.text
        print(f"  index.html: {r.status_code}, build meta: {has_meta}")
    except Exception as e:
        print(f"  index.html: ERROR {e}")

    # Latest deploy status
    sid = STAGING_SID if "staging" in url else PROD_SID
    try:
        r = requests.get(f"{BASE_API}/services/{sid}/deploys?limit=1", headers=HEADERS, proxies=proxies, timeout=15)
        dep = r.json()[0].get("deploy", r.json()[0])
        print(f"  latest deploy: status={dep.get('status')} trigger={dep.get('trigger')}")
    except Exception as e:
        print(f"  deploys: ERROR {e}")

    # Login test
    try:
        r = requests.post(f"{url}/auth/login", json={"email": "yaronklein1@gmail.com", "password": "Inv3stAI!2026$ecure"}, proxies=proxies, timeout=15)
        print(f"  login: {r.status_code}")
        if r.status_code == 200:
            cookies = r.cookies
            r2 = requests.get(f"{url}/auth/me", cookies=cookies, proxies=proxies, timeout=15)
            print(f"  /auth/me: {r2.status_code} {r2.text[:100]}")
    except Exception as e:
        print(f"  login: ERROR {e}")
