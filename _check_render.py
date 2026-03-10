"""Quick check of Render deploy status for both staging & production."""
import requests, json

proxies = {"http": "http://proxy-dmz.intel.com:911", "https": "http://proxy-dmz.intel.com:912"}
HEADERS = {"Authorization": "Bearer rnd_wKb6dejSU7BDZJDhPHUpL6vqVBEn", "Accept": "application/json"}
BASE = "https://api.render.com/v1"
STAGING = "srv-d6mn2cma2pns73d9r23g"
PROD = "srv-d6jcdsvgi27c73d2uta0"

for label, sid in [("STAGING", STAGING), ("PRODUCTION", PROD)]:
    print(f"\n=== {label} ({sid}) ===")
    try:
        r = requests.get(f"{BASE}/services/{sid}/deploys?limit=3", headers=HEADERS, proxies=proxies, timeout=15)
        deploys = r.json()
        for d in deploys:
            dep = d.get("deploy", d)
            did = str(dep.get("id", "?"))[:16]
            status = dep.get("status", "?")
            trigger = dep.get("trigger", "?")
            commit = dep.get("commit", {})
            msg = str(commit.get("message", "?"))[:70]
            created = str(dep.get("createdAt", "?"))[:19]
            print(f"  {did}  status={status:<12} trigger={trigger:<10} created={created}  commit={msg}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Also get build logs from latest deploy
    try:
        latest_id = deploys[0].get("deploy", deploys[0]).get("id")
        if latest_id:
            r2 = requests.get(f"{BASE}/services/{sid}/deploys/{latest_id}/logs", headers=HEADERS, proxies=proxies, timeout=15)
            logs = r2.json()
            if isinstance(logs, list):
                # Show last 15 log lines
                for entry in logs[-15:]:
                    ts = str(entry.get("timestamp", ""))[:19]
                    msg = entry.get("message", "")
                    print(f"    [{ts}] {msg}")
            else:
                print(f"    logs response: {str(logs)[:200]}")
    except Exception as e:
        print(f"  LOGS ERROR: {e}")
