from datetime import datetime, timedelta

from src.services import data_provider as dp
from src.services.market_data import _get_cached, _set_cache


def get_earnings_calendar(symbols: list[str]) -> list[dict]:
    """Fetch upcoming earnings dates for given symbols."""
    cache_key = f"earnings_cal:{','.join(sorted(symbols[:30]))}"
    cached = _get_cached(cache_key)
    if cached is not None:
        if isinstance(cached, list):
            return cached
        return []

    from_date = datetime.now().strftime("%Y-%m-%d")
    to_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    symbol_set = set(symbols[:30])
    raw = dp.get_earnings_calendar(from_date, to_date)

    events = []
    for item in raw:
        sym = item.get("symbol", "")
        if sym not in symbol_set:
            continue
        date_str = item.get("date", "")
        if not date_str:
            continue
        events.append({
            "symbol": sym,
            "name": sym,
            "event": "Earnings",
            "date": date_str,
        })

    events.sort(key=lambda x: x.get("date", ""))
    _set_cache(cache_key, events)
    return events


ECONOMIC_EVENTS = [
    {"event": "Federal Reserve Meeting", "frequency": "Every 6 weeks", "impact": "High",
     "description": "The Fed sets interest rates and monetary policy. Rate changes affect all investments."},
    {"event": "Non-Farm Payrolls", "frequency": "Monthly (1st Friday)", "impact": "High",
     "description": "Employment report showing jobs added/lost. Strong jobs = strong economy but may mean higher rates."},
    {"event": "Consumer Price Index (CPI)", "frequency": "Monthly", "impact": "High",
     "description": "Measures inflation. Higher CPI can lead to rate hikes, affecting stock and bond prices."},
    {"event": "GDP Report", "frequency": "Quarterly", "impact": "Medium",
     "description": "Gross Domestic Product measures total economic output. Shows if the economy is growing or shrinking."},
    {"event": "Earnings Season", "frequency": "Quarterly (Jan, Apr, Jul, Oct)", "impact": "High",
     "description": "Most large companies report quarterly results. Biggest driver of individual stock moves."},
    {"event": "Producer Price Index (PPI)", "frequency": "Monthly", "impact": "Medium",
     "description": "Measures wholesale inflation. A leading indicator of consumer inflation."},
    {"event": "Retail Sales", "frequency": "Monthly", "impact": "Medium",
     "description": "Tracks consumer spending at retail stores. Consumer spending drives ~70% of the US economy."},
    {"event": "FOMC Minutes", "frequency": "3 weeks after meeting", "impact": "Medium",
     "description": "Detailed notes from Fed meetings revealing policymaker thinking on economy and rates."},
]


def get_economic_events() -> list[dict]:
    return ECONOMIC_EVENTS
