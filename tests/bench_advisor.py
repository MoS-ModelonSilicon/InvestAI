"""Benchmark smart advisor endpoints on live site."""
import requests, time, os, json

proxies = {'https': 'http://proxy-dmz.intel.com:911', 'http': 'http://proxy-dmz.intel.com:911'}
base = 'https://investai-utho.onrender.com'

s = requests.Session()
s.proxies = proxies

email = os.environ.get('ADMIN_EMAIL', 'admin@investai.com')
pwd = os.environ.get('ADMIN_PASSWORD', 'admin123')

print(f'Logging in as {email}...')
r = s.post(f'{base}/auth/login', json={'email': email, 'password': pwd}, timeout=30)
print(f'Login: {r.status_code}')
if r.status_code != 200:
    r = s.post(f'{base}/auth/register', json={'email': email, 'password': pwd, 'name': 'Test'}, timeout=30)
    print(f'Register: {r.status_code}')
    r = s.post(f'{base}/auth/login', json={'email': email, 'password': pwd}, timeout=30)
    print(f'Login retry: {r.status_code}')

# Cache status
print('\n=== CACHE STATUS ===')
r = s.get(f'{base}/api/market/cache-status', timeout=30)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    cs = r.json()
    print(json.dumps(cs, indent=2)[:2000])

# Test combos
combos = [
    ('balanced', '1y'), ('balanced', '6m'), ('balanced', '3m'), ('balanced', '1m'),
    ('conservative', '1y'), ('aggressive', '1y'),
]

print('\n=== ADVISOR ENDPOINT TIMING ===')
results = []
for risk, period in combos:
    url = f'{base}/api/advisor/analyze?amount=10000&risk={risk}&period={period}'
    start = time.time()
    try:
        r = s.get(url, timeout=180)
        elapsed = time.time() - start
        has_data = 'portfolio' in r.text[:500] if r.status_code == 200 else False
        label = f'{risk}/{period}'
        tag = 'SLOW' if elapsed > 5 else 'OK'
        print(f'{label:25s} | {r.status_code} | {elapsed:6.1f}s | {len(r.text):6d} chars | portfolio={has_data} | {tag}')
        if r.status_code != 200:
            print(f'  Body: {r.text[:300]}')
        results.append((label, elapsed, r.status_code))
    except Exception as e:
        elapsed = time.time() - start
        print(f'{risk}/{period}: ERROR after {elapsed:.1f}s: {e}')
        results.append((f'{risk}/{period}', elapsed, 'ERROR'))

print('\n=== SUMMARY ===')
for label, elapsed, status in results:
    tag = 'SLOW' if elapsed > 5 else 'FAST'
    print(f'{label:25s} {elapsed:6.1f}s  [{tag}]')
