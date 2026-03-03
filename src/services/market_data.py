import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 900  # 15 min

_warming = False
_warm_done = threading.Event()

STOCK_UNIVERSE = [
    # ── US: Technology ─────────────────────────────
    "AAPL", "MSFT", "GOOGL", "NVDA", "META", "AVGO", "ADBE", "CRM", "CSCO",
    "INTC", "AMD", "TXN", "QCOM", "AMAT", "NOW", "ORCL", "IBM", "MU", "PANW",
    "SNPS", "CDNS", "FTNT", "MRVL",
    # US: Consumer Cyclical
    "AMZN", "TSLA", "HD", "NKE", "SBUX", "LOW", "MCD", "TJX", "BKNG",
    "CMG", "ORLY", "LULU", "ABNB", "GM", "F", "RIVN",
    # US: Financial Services
    "BRK-B", "JPM", "V", "MA", "GS", "BLK", "AXP", "MS", "SCHW",
    "C", "BAC", "WFC", "CB", "PGR", "ICE", "CME", "SPGI",
    # US: Healthcare
    "UNH", "JNJ", "LLY", "ABT", "MRK", "TMO", "PFE", "ABBV", "DHR",
    "ISRG", "MDT", "AMGN", "GILD", "VRTX", "REGN", "BMY", "ZTS",
    # US: Industrials
    "CAT", "DE", "BA", "UNP", "HON", "MMM", "GE", "RTX", "LMT",
    "UPS", "FDX", "WM", "ETN", "ITW", "EMR",
    # US: Consumer Defensive
    "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL", "MDLZ",
    "KHC", "GIS", "SJM", "HSY",
    # US: Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY",
    "PXD", "DVN", "HAL", "FANG", "KMI", "WMB", "OKE",
    # US: Communication Services
    "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "GOOG", "CHTR", "EA",
    "TTWO", "MTCH",
    # US: Utilities
    "NEE", "DUK", "SO", "D", "SRE", "AEP", "EXC", "XEL", "WEC", "ED",
    # US: Real Estate
    "PLD", "AMT", "CCI", "EQIX", "PSA", "O", "SPG", "WELL", "DLR",
    # US: Basic Materials
    "LIN", "APD", "SHW", "ECL", "NEM", "FCX", "NUE", "DOW", "DD",

    # ── China / Hong Kong (HKEX) ──────────────────
    "1810.HK",  # Xiaomi
    "0700.HK",  # Tencent
    "9988.HK",  # Alibaba (HK listing)
    "9618.HK",  # JD.com (HK listing)
    "1211.HK",  # BYD
    "3690.HK",  # Meituan
    "9888.HK",  # Baidu (HK listing)
    "0992.HK",  # Lenovo
    "2015.HK",  # Li Auto (HK listing)
    "9866.HK",  # NIO (HK listing)
    "0005.HK",  # HSBC Holdings
    "0941.HK",  # China Mobile
    "2318.HK",  # Ping An Insurance
    "1299.HK",  # AIA Group
    "0388.HK",  # Hong Kong Exchanges
    # China / HK US-listed ADRs
    "BABA", "JD", "BIDU", "NIO", "LI", "XPEV", "PDD", "TME", "BEKE",

    # ── Japan (TSE) ───────────────────────────────
    "7203.T",   # Toyota
    "6758.T",   # Sony
    "7974.T",   # Nintendo
    "9984.T",   # SoftBank Group
    "6861.T",   # Keyence
    "6501.T",   # Hitachi
    "8306.T",   # Mitsubishi UFJ Financial
    # Japan US-listed ADRs
    "TM", "SONY", "MUFG",

    # ── South Korea (KRX) ─────────────────────────
    "005930.KS",  # Samsung Electronics
    "000660.KS",  # SK Hynix
    "005380.KS",  # Hyundai Motor
    "035420.KS",  # NAVER
    "035720.KS",  # Kakao

    # ── Taiwan ────────────────────────────────────
    "2330.TW",    # TSMC (local listing)
    "TSM",        # TSMC (US ADR)
    "2317.TW",    # Hon Hai / Foxconn

    # ── Europe ────────────────────────────────────
    "ASML.AS",    # ASML (Netherlands)
    "MC.PA",      # LVMH (France)
    "OR.PA",      # L'Oréal (France)
    "SAP.DE",     # SAP (Germany)
    "SIE.DE",     # Siemens (Germany)
    "BMW.DE",     # BMW (Germany)
    "ALV.DE",     # Allianz (Germany)
    "ADS.DE",     # Adidas (Germany)
    "SHEL.L",     # Shell (UK)
    "AZN.L",      # AstraZeneca (UK)
    "ULVR.L",     # Unilever (UK)
    "RIO.L",      # Rio Tinto (UK)
    "NESN.SW",    # Nestlé (Switzerland)
    "ROG.SW",     # Roche (Switzerland)
    "NOVN.SW",    # Novartis (Switzerland)
    # Europe US-listed ADRs
    "ASML", "NVO", "SAP", "SHEL", "AZN", "UL", "DEO", "TTE", "SPOT",

    # ── India ─────────────────────────────────────
    "RELIANCE.NS",  # Reliance Industries
    "TCS.NS",       # Tata Consultancy Services
    "HDFCBANK.NS",  # HDFC Bank
    "INFY.NS",      # Infosys (local)
    "WIPRO.NS",     # Wipro
    # India US-listed ADRs
    "INFY", "WIT", "IBN",

    # ── Australia ─────────────────────────────────
    "BHP.AX",     # BHP Group
    "CBA.AX",     # Commonwealth Bank
    "CSL.AX",     # CSL Limited
    "WDS.AX",     # Woodside Energy

    # ── Canada ────────────────────────────────────
    "SHOP.TO",    # Shopify (TSX)
    "RY.TO",      # Royal Bank of Canada
    "TD.TO",      # TD Bank
    "ENB.TO",     # Enbridge
    # Canada US-listed
    "SHOP", "RY", "TD",

    # ── Brazil ────────────────────────────────────
    "VALE3.SA",   # Vale
    "PETR4.SA",   # Petrobras
    "ITUB4.SA",   # Itaú Unibanco
    # Brazil US-listed ADRs
    "VALE", "PBR", "ITUB", "NU",

    # ── Singapore ─────────────────────────────────
    "D05.SI",     # DBS Group
    "SE",         # Sea Limited (US-listed)
    "GRAB",       # Grab Holdings (US-listed)

    # ── Israel (US-listed ADRs) ───────────────────
    "TEVA", "CHKP", "NICE", "WIX", "MNDY", "CYBR", "ICL", "ESLT",
    # Israel (TASE-listed)
    "TASE.TA", "LUMI.TA", "POLI.TA", "DSCT.TA", "FIBI.TA", "MZTF.TA",
    "HARL.TA", "BEZQ.TA", "CEL.TA", "AZRG.TA",
]

ETF_UNIVERSE = [
    # Broad US Market
    "SPY", "QQQ", "VTI", "VOO", "IWM", "DIA", "RSP",
    # International / Emerging Markets
    "VEA", "VWO", "EFA", "IEMG", "FXI",   # FXI = China large-cap
    "MCHI",  # MSCI China
    "EWJ",   # Japan
    "EWY",   # South Korea
    "EWH",   # Hong Kong
    "EWT",   # Taiwan
    "INDA",  # India
    "EWZ",   # Brazil
    "EWG",   # Germany
    "EWU",   # UK
    "EWA",   # Australia
    "EWC",   # Canada
    # Bonds
    "BND", "AGG", "TLT", "LQD", "HYG", "TIP", "VCSH", "VCIT",
    # Dividend / Income
    "VIG", "VYM", "SCHD", "DVY", "HDV", "JEPI",
    # Sector ETFs
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLB", "XLU", "XLRE", "XLC",
    # Thematic
    "ARKK", "ARKW", "SOXX", "SMH", "KWEB", "ICLN", "TAN",
    # Commodities
    "GLD", "SLV", "VNQ", "USO", "DBC",
]

ALL_UNIVERSE = STOCK_UNIVERSE + ETF_UNIVERSE

SECTORS = [
    "Technology", "Financial Services", "Healthcare", "Consumer Cyclical",
    "Industrials", "Communication Services", "Consumer Defensive", "Energy",
    "Basic Materials", "Real Estate", "Utilities",
]

REGIONS = [
    "US", "China / Hong Kong", "Japan", "South Korea", "Taiwan",
    "Europe", "India", "Australia", "Canada", "Brazil", "Singapore", "Israel",
]

_REGION_MAP = {}
for sym in STOCK_UNIVERSE:
    if sym.endswith(".HK") or sym in ("BABA", "JD", "BIDU", "NIO", "LI", "XPEV", "PDD", "TME", "BEKE"):
        _REGION_MAP[sym] = "China / Hong Kong"
    elif sym.endswith(".T") or sym in ("TM", "SONY", "MUFG"):
        _REGION_MAP[sym] = "Japan"
    elif sym.endswith(".KS"):
        _REGION_MAP[sym] = "South Korea"
    elif sym.endswith(".TW") or sym == "TSM":
        _REGION_MAP[sym] = "Taiwan"
    elif sym.endswith((".AS", ".PA", ".DE", ".L", ".SW")) or sym in ("ASML", "NVO", "SAP", "SHEL", "AZN", "UL", "DEO", "TTE", "SPOT"):
        _REGION_MAP[sym] = "Europe"
    elif sym.endswith(".NS") or sym in ("INFY", "WIT", "IBN"):
        _REGION_MAP[sym] = "India"
    elif sym.endswith(".AX"):
        _REGION_MAP[sym] = "Australia"
    elif sym.endswith(".TO") or sym in ("SHOP", "RY", "TD"):
        _REGION_MAP[sym] = "Canada"
    elif sym.endswith(".SA") or sym in ("VALE", "PBR", "ITUB", "NU"):
        _REGION_MAP[sym] = "Brazil"
    elif sym.endswith(".SI") or sym in ("SE", "GRAB"):
        _REGION_MAP[sym] = "Singapore"
    elif sym.endswith(".TA") or sym in ("TEVA", "CHKP", "NICE", "WIX", "MNDY", "CYBR", "ICL", "ESLT"):
        _REGION_MAP[sym] = "Israel"
    else:
        _REGION_MAP[sym] = "US"


def get_region(symbol: str) -> str:
    return _REGION_MAP.get(symbol, "US")

MAX_WORKERS = 25


def _get_cached(key: str) -> Optional[dict]:
    with _cache_lock:
        if key in _cache:
            ts, data = _cache[key]
            if time.time() - ts < CACHE_TTL:
                return data
    return None


def _set_cache(key: str, data):
    with _cache_lock:
        _cache[key] = (time.time(), data)


def fetch_stock_info(symbol: str) -> Optional[dict]:
    cached = _get_cached(f"info:{symbol}")
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or "symbol" not in info:
            return None

        raw_div = info.get("dividendYield")
        div_yield = _pct_safe(raw_div)
        if div_yield is not None and div_yield > 20:
            div_yield = None

        price = info.get("currentPrice", info.get("regularMarketPrice", info.get("previousClose", 0)))
        w52_high = info.get("fiftyTwoWeekHigh")
        w52_low = info.get("fiftyTwoWeekLow")
        pct_from_high = round((price - w52_high) / w52_high * 100, 1) if w52_high and price else None
        pct_from_low = round((price - w52_low) / w52_low * 100, 1) if w52_low and price else None

        result = {
            "symbol": info.get("symbol", symbol),
            "name": info.get("shortName", info.get("longName", symbol)),
            "sector": info.get("sector", info.get("category", "N/A")),
            "industry": info.get("industry", "N/A"),
            "price": price,
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": div_yield,
            "beta": info.get("beta"),
            "year_change": _pct(info.get("52WeekChange")),
            "recommendation": info.get("recommendationKey"),
            "expense_ratio": _pct_safe(info.get("annualReportExpenseRatio")),
            "asset_type": _classify_asset(info),
            "total_assets": info.get("totalAssets"),
            "three_year_return": _pct(info.get("threeYearAverageReturn")),
            "five_year_return": _pct(info.get("fiveYearAverageReturn")),
            "week52_high": w52_high,
            "week52_low": w52_low,
            "pct_from_high": pct_from_high,
            "pct_from_low": pct_from_low,
            "profit_margin": _pct(info.get("profitMargins")),
            "revenue_growth": _pct(info.get("revenueGrowth")),
            "earnings_growth": _pct(info.get("earningsGrowth")),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": _pct(info.get("returnOnEquity")),
            "free_cash_flow": info.get("freeCashflow"),
            "target_mean_price": info.get("targetMeanPrice"),
            "target_high_price": info.get("targetHighPrice"),
            "target_low_price": info.get("targetLowPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "summary": info.get("longBusinessSummary", ""),
            "region": get_region(symbol),
        }
        _set_cache(f"info:{symbol}", result)
        return result
    except Exception:
        return None


def fetch_batch(symbols: list[str]) -> list[dict]:
    """Fetch info for multiple symbols in parallel."""
    cached_results = []
    uncached = []

    for sym in symbols:
        c = _get_cached(f"info:{sym}")
        if c and c.get("price", 0) > 0:
            cached_results.append(c)
        else:
            uncached.append(sym)

    if not uncached:
        return cached_results

    fresh = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_stock_info, sym): sym for sym in uncached}
        for future in as_completed(futures):
            try:
                info = future.result()
                if info and info.get("price", 0) > 0:
                    fresh.append(info)
            except Exception:
                pass

    return cached_results + fresh


def _pct(val) -> Optional[float]:
    if val is None:
        return None
    return round(val * 100, 2) if abs(val) < 10 else round(val, 2)


def _pct_safe(val) -> Optional[float]:
    """Convert to percentage, guarding against values already in % form."""
    if val is None:
        return None
    if abs(val) > 1:
        return round(val, 2)
    return round(val * 100, 2)


def _classify_asset(info: dict) -> str:
    qtype = info.get("quoteType", "").upper()
    if qtype == "ETF":
        return "ETF"
    if qtype == "MUTUALFUND":
        return "Fund"
    return "Stock"


def format_market_cap(cap: float) -> str:
    if not cap:
        return "N/A"
    if cap >= 1e12:
        return f"${cap/1e12:.1f}T"
    if cap >= 1e9:
        return f"${cap/1e9:.1f}B"
    if cap >= 1e6:
        return f"${cap/1e6:.0f}M"
    return f"${cap:,.0f}"


QUOTE_CACHE_TTL = 90  # live quotes refresh faster than full info


def fetch_live_quotes(symbols: list[str]) -> list[dict]:
    cache_key = "live_quotes:" + ",".join(symbols)
    with _cache_lock:
        if cache_key in _cache:
            ts, data = _cache[cache_key]
            if time.time() - ts < QUOTE_CACHE_TTL:
                return data

    results = []
    try:
        df = yf.download(
            symbols, period="5d", interval="1d",
            group_by="ticker", progress=False, threads=True,
        )
        if df.empty:
            return results

        _names = _batch_resolve_names(symbols)

        for sym in symbols:
            try:
                if len(symbols) == 1:
                    sym_df = df
                else:
                    sym_df = df[sym]

                closes = sym_df["Close"].dropna()
                if len(closes) < 1:
                    continue

                price = float(closes.iloc[-1])
                prev = float(closes.iloc[-2]) if len(closes) >= 2 else price
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0

                highs = sym_df["High"].dropna()
                lows = sym_df["Low"].dropna()
                vols = sym_df["Volume"].dropna()

                results.append({
                    "symbol": sym,
                    "name": _names.get(sym, sym),
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "market_cap": 0,
                    "volume": int(vols.iloc[-1]) if len(vols) else 0,
                    "day_high": round(float(highs.iloc[-1]), 2) if len(highs) else round(price, 2),
                    "day_low": round(float(lows.iloc[-1]), 2) if len(lows) else round(price, 2),
                })
            except Exception:
                continue
    except Exception as e:
        logger.warning("fetch_live_quotes error: %s", e)

    if results:
        _set_cache(cache_key, results)
    return results


def _batch_resolve_names(symbols: list[str]) -> dict[str, str]:
    """Pull display names from the info cache if available, otherwise use symbol."""
    names = {}
    for sym in symbols:
        cached = _get_cached(f"info:{sym}")
        if cached:
            names[sym] = cached.get("name", sym)
        else:
            names[sym] = sym
    return names


def fetch_sparklines(symbols: list[str], period: str = "5d", interval: str = "1h") -> dict[str, list[float]]:
    cache_key = f"sparklines:{','.join(symbols)}:{period}:{interval}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result = {}
    try:
        data = yf.download(symbols, period=period, interval=interval, group_by="ticker", progress=False, threads=True)
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    closes = data["Close"].dropna().tolist()
                else:
                    closes = data[sym]["Close"].dropna().tolist()
                result[sym] = [round(v, 2) for v in closes]
            except Exception:
                result[sym] = []
    except Exception:
        pass

    _set_cache(cache_key, result)
    return result


# ── Background cache warming ────────────────────

def warm_cache():
    """Pre-fetch all universe data in background so screener is instant."""
    global _warming
    if _warming:
        return
    _warming = True
    logger.info("Cache warm: starting for %d symbols", len(ALL_UNIVERSE))
    t0 = time.time()
    fetch_batch(ALL_UNIVERSE)
    elapsed = time.time() - t0
    logger.info("Cache warm: done in %.1fs, %d symbols cached", elapsed, len(ALL_UNIVERSE))
    _warm_done.set()
    _warming = False


def start_cache_warmer():
    """Launch background thread that warms cache on startup and refreshes periodically."""
    def _loop():
        while True:
            try:
                warm_cache()
            except Exception as e:
                logger.error("Cache warmer error: %s", e)
            time.sleep(CACHE_TTL - 60)  # refresh 1 min before expiry

    t = threading.Thread(target=_loop, daemon=True, name="cache-warmer")
    t.start()


def get_cache_status() -> dict:
    """Return how many symbols are cached and whether warming is in progress."""
    with _cache_lock:
        now = time.time()
        cached_count = sum(
            1 for k, (ts, _) in _cache.items()
            if k.startswith("info:") and now - ts < CACHE_TTL
        )
    return {
        "cached": cached_count,
        "total": len(ALL_UNIVERSE),
        "warming": _warming,
        "ready": _warm_done.is_set(),
    }
