"""Verify staging + promote to prod + verify prod."""
import requests
import time
import json

proxies = {"http": "http://proxy-dmz.intel.com:911", "https": "http://proxy-dmz.intel.com:912"}
HEADERS = {"Authorization": "Bearer rnd_wKb6dejSU7BDZJDhPHUpL6vqVBEn", "Accept": "application/json"}
BASE_API = "https://api.render.com/v1"
STAGING_URL = "https://finance-tracker-staging.onrender.com"
PROD_URL = "https://investai-utho.onrender.com"
STAGING_SID = "srv-d6mn2cma2pns73d9r23g"
PROD_SID = "srv-d6jcdsvgi27c73d2uta0"

def check_site(url, label):
    print(f"\n=== {label}: {url} ===")
    # Health
    try:
        r = requests.get(f"{url}/health", proxies=proxies, timeout=30)
        print(f"  /health: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"    version: {data.get('version')}")
            print(f"    environment: {data.get('environment')}")
            print(f"    cache_ready: {data.get('cache_ready')}")
            print(f"    cache_entries: {data.get('cache_entries')}")
    except Exception as e:
        print(f"  /health: ERROR {e}")

    # HTML meta build tag
    try:
        r = requests.get(f"{url}/static/index.html", proxies=proxies, timeout=15)
        has_meta = '2026-03-08-staging-flow' in r.text
        print(f"  index.html: {r.status_code}, has build meta: {has_meta}")
    except Exception as e:
        print(f"  index.html: ERROR {e}")

    # Check deploy logs (latest deploy)
    sid = STAGING_SID if "staging" in url else PROD_SID
    try:
        r = requests.get(f"{BASE_API}/services/{sid}/deploys?limit=2", headers=HEADERS, proxies=proxies, timeout=15)
        for d in r.json():
            dep = d.get("deploy", d)
            print(f"  deploy: id={dep.get('id')} status={dep.get('status')} trigger={dep.get('trigger')} created={dep.get('createdAt')}")
    except Exception as e:
        print(f"  deploys: ERROR {e}")

# Step 1: Check staging
check_site(STAGING_URL, "STAGING")

# Step 2: Trigger prod promotion
print("\n=== PROMOTING TO PRODUCTION ===")
DEPLOY_HOOK = "https://api.render.com/deploy/srv-d6jcdsvgi27c73d2uta0?key=wnZP2EvMsZs"
r = requests.get(DEPLOY_HOOK, proxies=proxies, timeout=15)
print(f"Deploy hook response: {r.status_code}")

# Step 3: Wait for prod to deploy (build + start ~3min)
print("\nWaiting for prod deploy...")
for i in range(30):  # up to 5 minutes
    time.sleep(10)
    try:
        r = requests.get(f"{BASE_API}/services/{PROD_SID}/deploys?limit=1", headers=HEADERS, proxies=proxies, timeout=15)
        dep = r.json()[0].get("deploy", r.json()[0])
        status = dep.get("status", "?")
        print(f"  [{i*10}s] status={status}")
        if status in ("live", "update_failed", "build_failed", "canceled"):
            break
    except Exception as e:
        print(f"  [{i*10}s] ERROR {e}")

# Step 4: Check prod
check_site(PROD_URL, "PRODUCTION")

print("\n=== DONE ===")
