"""Quick debug script to check sparkline data from the API."""

import requests

BASE = "http://127.0.0.1:8091"
s = requests.Session()
s.proxies = {"http": None, "https": None}  # no proxy for localhost
s.trust_env = False

# Register + Login
r = s.post(f"{BASE}/auth/register", json={"email": "spark-debug@e2e.local", "password": "TestPass123"})
print(f"Register: {r.status_code}")
r = s.post(f"{BASE}/auth/login", json={"email": "spark-debug@e2e.local", "password": "TestPass123"})
print(f"Login: {r.status_code}")

# Test /api/market/featured
print("\n=== /api/market/featured ===")
r = s.get(f"{BASE}/api/market/featured", timeout=120)
print(f"Status: {r.status_code}")
data = r.json()
for stock in data:
    sp = stock.get("sparkline", [])
    sym = stock.get("symbol", "?")
    price = stock.get("price", "N/A")
    print(f"  {sym}: price={price}, sparkline_points={len(sp)}, sample={sp[:5] if sp else 'EMPTY'}")

# Test /api/market/home
print("\n=== /api/market/home ===")
r = s.get(f"{BASE}/api/market/home", timeout=120)
print(f"Status: {r.status_code}")
home = r.json()
for stock in home.get("featured", []):
    sp = stock.get("sparkline", [])
    sym = stock.get("symbol", "?")
    price = stock.get("price", "N/A")
    print(f"  {sym}: price={price}, sparkline_points={len(sp)}, sample={sp[:5] if sp else 'EMPTY'}")

# Direct sparkline test via data_provider
print("\n=== Direct data_provider.get_candles test ===")
import time, sys

sys.path.insert(0, ".")
from src.services import data_provider as dp

to_ts = int(time.time())
from_ts = to_ts - 5 * 86400  # 5 days

for sym in ["AAPL", "MSFT", "NVDA"]:
    candles = dp.get_candles(sym, "60", from_ts, to_ts)
    if candles and candles.get("c"):
        pts = candles["c"]
        print(f"  {sym}: {len(pts)} candle points, first 5: {pts[:5]}")
    else:
        print(f"  {sym}: NO CANDLES returned! candles={candles}")

# Direct fetch_sparklines test
print("\n=== Direct fetch_sparklines test ===")
from src.services.market_data import fetch_sparklines

sparks = fetch_sparklines(["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL"])
for sym, pts in sparks.items():
    print(f"  {sym}: {len(pts)} points, sample={pts[:5] if pts else 'EMPTY'}")
