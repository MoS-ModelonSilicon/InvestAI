import yfinance as yf
from datetime import datetime, timedelta
from src.services.market_data import _get_cached, _set_cache


def get_earnings_calendar(symbols: list[str]) -> list[dict]:
    """Fetch upcoming earnings dates for given symbols."""
    cache_key = f"earnings_cal:{','.join(sorted(symbols[:30]))}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    events = []
    for sym in symbols[:30]:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info or {}

            cal = ticker.calendar
            if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
                if isinstance(cal, dict):
                    ed = cal.get("Earnings Date")
                    if ed and isinstance(ed, list) and len(ed) > 0:
                        for d in ed:
                            events.append({
                                "symbol": sym,
                                "name": info.get("shortName", sym),
                                "event": "Earnings",
                                "date": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                            })
                    dividend_date = cal.get("Dividend Date")
                    if dividend_date:
                        d = dividend_date
                        events.append({
                            "symbol": sym,
                            "name": info.get("shortName", sym),
                            "event": "Dividend",
                            "date": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                        })
                    ex_dividend = cal.get("Ex-Dividend Date")
                    if ex_dividend:
                        d = ex_dividend
                        events.append({
                            "symbol": sym,
                            "name": info.get("shortName", sym),
                            "event": "Ex-Dividend",
                            "date": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                        })
        except Exception:
            continue

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
