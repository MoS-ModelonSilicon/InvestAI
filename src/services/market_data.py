import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional, cast

from src.services import data_provider as dp

logger = logging.getLogger(__name__)

# ── Memory-conscious settings for free-tier hosting (512 MB) ──
_LOW_MEMORY = os.environ.get("LOW_MEMORY", "").lower() in ("1", "true", "yes")
try:
    threading.stack_size(2 * 1024 * 1024)  # 2 MB stacks (1 MB too small for yfinance/requests)
except Exception:
    pass  # some platforms don't support stack_size

_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = 1200  # 20 min — overlap with 15-min scheduler so cache never goes cold
# Must hold at least ALL_UNIVERSE × 2 (info: + quote: per symbol) + extras.
# 300 was too small — the warmer evicted Phase-1 info: entries (like INTC)
# before Phase 3 built the screener snapshot, causing missing search results.
CACHE_MAX_ENTRIES = 800

_warming = False
_warm_done = threading.Event()

STOCK_UNIVERSE = [
    # ── US: Technology ─────────────────────────────
    "AAPL",
    "MSFT",
    "GOOGL",
    "NVDA",
    "META",
    "AVGO",
    "ADBE",
    "CRM",
    "CSCO",
    "INTC",
    "AMD",
    "TXN",
    "QCOM",
    "AMAT",
    "NOW",
    "ORCL",
    "IBM",
    "MU",
    "PANW",
    "SNPS",
    "CDNS",
    "FTNT",
    "MRVL",
    # US: Consumer Cyclical
    "AMZN",
    "TSLA",
    "HD",
    "NKE",
    "SBUX",
    "LOW",
    "MCD",
    "TJX",
    "BKNG",
    "CMG",
    "ORLY",
    "LULU",
    "ABNB",
    "GM",
    "F",
    "RIVN",
    # US: Financial Services
    "BRK-B",
    "JPM",
    "V",
    "MA",
    "GS",
    "BLK",
    "AXP",
    "MS",
    "SCHW",
    "C",
    "BAC",
    "WFC",
    "CB",
    "PGR",
    "ICE",
    "CME",
    "SPGI",
    # US: Healthcare
    "UNH",
    "JNJ",
    "LLY",
    "ABT",
    "MRK",
    "TMO",
    "PFE",
    "ABBV",
    "DHR",
    "ISRG",
    "MDT",
    "AMGN",
    "GILD",
    "VRTX",
    "REGN",
    "BMY",
    "ZTS",
    # US: Industrials
    "CAT",
    "DE",
    "BA",
    "UNP",
    "HON",
    "MMM",
    "GE",
    "RTX",
    "LMT",
    "UPS",
    "FDX",
    "WM",
    "ETN",
    "ITW",
    "EMR",
    # US: Consumer Defensive
    "PG",
    "KO",
    "PEP",
    "COST",
    "WMT",
    "PM",
    "MO",
    "CL",
    "MDLZ",
    "KHC",
    "GIS",
    "SJM",
    "HSY",
    # US: Energy
    "XOM",
    "CVX",
    "COP",
    "EOG",
    "SLB",
    "MPC",
    "PSX",
    "VLO",
    "OXY",
    "DVN",
    "HAL",
    "FANG",
    "KMI",
    "WMB",
    "OKE",
    # US: Communication Services
    "DIS",
    "NFLX",
    "CMCSA",
    "T",
    "VZ",
    "TMUS",
    "GOOG",
    "CHTR",
    "EA",
    "TTWO",
    "MTCH",
    # US: Utilities
    "NEE",
    "DUK",
    "SO",
    "D",
    "SRE",
    "AEP",
    "EXC",
    "XEL",
    "WEC",
    "ED",
    # US: Real Estate
    "PLD",
    "AMT",
    "CCI",
    "EQIX",
    "PSA",
    "O",
    "SPG",
    "WELL",
    "DLR",
    # US: Basic Materials
    "LIN",
    "APD",
    "SHW",
    "ECL",
    "NEM",
    "FCX",
    "NUE",
    "DOW",
    "DD",
    # ── International (US-listed ADRs only) ───────
    # China / HK
    "BABA",
    "JD",
    "BIDU",
    "NIO",
    "LI",
    "XPEV",
    "PDD",
    "TME",
    "BEKE",
    # Japan
    "TM",
    "SONY",
    "MUFG",
    # Taiwan
    "TSM",
    # Europe
    "ASML",
    "NVO",
    "SAP",
    "SHEL",
    "AZN",
    "UL",
    "DEO",
    "TTE",
    "SPOT",
    # India
    "INFY",
    "WIT",
    "IBN",
    # Canada
    "SHOP",
    "RY",
    "TD",
    # Brazil
    "VALE",
    "PBR",
    "ITUB",
    "NU",
    # Singapore
    "SE",
    "GRAB",
    # Israel (US-listed)
    "TEVA",
    "CHKP",
    "NICE",
    "WIX",
    "MNDY",
    "CYBR",
    "ICL",
    "ESLT",
    "FVRR",
    "GLBE",
    "ZIM",
    "SEDG",
    "INMD",
    "CEVA",
    "ORA",
    "RDWR",
    "ALLT",
    "PAYONR",
    # Israel (TASE — via Yahoo Finance)
    "LUMI.TA",
    "POLI.TA",
    "DSCT.TA",
    "MZTF.TA",
    "BEZQ.TA",
    "CEL.TA",
    "PTNR.TA",
    "AZRG.TA",
    "MGDL.TA",
    "HAREL.TA",
    "DLEKG.TA",
    "ORL.TA",
    "STRS.TA",
    "ELCO.TA",
    "AMOT.TA",
]

ETF_UNIVERSE = [
    # Broad US Market
    "SPY",
    "QQQ",
    "VTI",
    "VOO",
    "IWM",
    "DIA",
    "RSP",
    # International / Emerging Markets
    "VEA",
    "VWO",
    "EFA",
    "IEMG",
    "FXI",  # FXI = China large-cap
    "MCHI",  # MSCI China
    "EWJ",  # Japan
    "EWY",  # South Korea
    "EWH",  # Hong Kong
    "EWT",  # Taiwan
    "INDA",  # India
    "EWZ",  # Brazil
    "EWG",  # Germany
    "EWU",  # UK
    "EWA",  # Australia
    "EWC",  # Canada
    # Bonds
    "BND",
    "AGG",
    "TLT",
    "LQD",
    "HYG",
    "TIP",
    "VCSH",
    "VCIT",
    # Dividend / Income
    "VIG",
    "VYM",
    "SCHD",
    "DVY",
    "HDV",
    "JEPI",
    # Sector ETFs
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLI",
    "XLP",
    "XLY",
    "XLB",
    "XLU",
    "XLRE",
    "XLC",
    # Thematic
    "ARKK",
    "ARKW",
    "SOXX",
    "SMH",
    "KWEB",
    "ICLN",
    "TAN",
    # Commodities
    "GLD",
    "SLV",
    "VNQ",
    "USO",
    "DBC",
]

ALL_UNIVERSE = STOCK_UNIVERSE + ETF_UNIVERSE

# ── Static name lookup (enables search before cache warms) ──────
# Maps symbol → display name so the screener can match by company name
# even when the data provider cache hasn't fetched the symbol yet.
KNOWN_NAMES: dict[str, str] = {
    # US: Technology
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc",
    "NVDA": "NVIDIA Corporation",
    "META": "Meta Platforms Inc",
    "AVGO": "Broadcom Inc",
    "ADBE": "Adobe Inc",
    "CRM": "Salesforce Inc",
    "CSCO": "Cisco Systems Inc",
    "INTC": "Intel Corporation",
    "AMD": "Advanced Micro Devices Inc",
    "TXN": "Texas Instruments Inc",
    "QCOM": "Qualcomm Inc",
    "AMAT": "Applied Materials Inc",
    "NOW": "ServiceNow Inc",
    "ORCL": "Oracle Corporation",
    "IBM": "International Business Machines",
    "MU": "Micron Technology Inc",
    "PANW": "Palo Alto Networks Inc",
    "SNPS": "Synopsys Inc",
    "CDNS": "Cadence Design Systems Inc",
    "FTNT": "Fortinet Inc",
    "MRVL": "Marvell Technology Inc",
    # US: Consumer Cyclical
    "AMZN": "Amazon.com Inc",
    "TSLA": "Tesla Inc",
    "HD": "Home Depot Inc",
    "NKE": "Nike Inc",
    "SBUX": "Starbucks Corporation",
    "LOW": "Lowe's Companies Inc",
    "MCD": "McDonald's Corporation",
    "TJX": "TJX Companies Inc",
    "BKNG": "Booking Holdings Inc",
    "CMG": "Chipotle Mexican Grill Inc",
    "ORLY": "O'Reilly Automotive Inc",
    "LULU": "Lululemon Athletica Inc",
    "ABNB": "Airbnb Inc",
    "GM": "General Motors Company",
    "F": "Ford Motor Company",
    "RIVN": "Rivian Automotive Inc",
    # US: Financial Services
    "BRK-B": "Berkshire Hathaway Inc",
    "JPM": "JPMorgan Chase & Co",
    "V": "Visa Inc",
    "MA": "Mastercard Inc",
    "GS": "Goldman Sachs Group Inc",
    "BLK": "BlackRock Inc",
    "AXP": "American Express Company",
    "MS": "Morgan Stanley",
    "SCHW": "Charles Schwab Corporation",
    "C": "Citigroup Inc",
    "BAC": "Bank of America Corporation",
    "WFC": "Wells Fargo & Company",
    "CB": "Chubb Limited",
    "PGR": "Progressive Corporation",
    "ICE": "Intercontinental Exchange Inc",
    "CME": "CME Group Inc",
    "SPGI": "S&P Global Inc",
    # US: Healthcare
    "UNH": "UnitedHealth Group Inc",
    "JNJ": "Johnson & Johnson",
    "LLY": "Eli Lilly and Company",
    "ABT": "Abbott Laboratories",
    "MRK": "Merck & Co Inc",
    "TMO": "Thermo Fisher Scientific Inc",
    "PFE": "Pfizer Inc",
    "ABBV": "AbbVie Inc",
    "DHR": "Danaher Corporation",
    "ISRG": "Intuitive Surgical Inc",
    "MDT": "Medtronic plc",
    "AMGN": "Amgen Inc",
    "GILD": "Gilead Sciences Inc",
    "VRTX": "Vertex Pharmaceuticals Inc",
    "REGN": "Regeneron Pharmaceuticals Inc",
    "BMY": "Bristol-Myers Squibb Company",
    "ZTS": "Zoetis Inc",
    # US: Industrials
    "CAT": "Caterpillar Inc",
    "DE": "Deere & Company",
    "BA": "Boeing Company",
    "UNP": "Union Pacific Corporation",
    "HON": "Honeywell International Inc",
    "MMM": "3M Company",
    "GE": "GE Aerospace",
    "RTX": "RTX Corporation Raytheon",
    "LMT": "Lockheed Martin Corporation",
    "UPS": "United Parcel Service Inc",
    "FDX": "FedEx Corporation",
    "WM": "Waste Management Inc",
    "ETN": "Eaton Corporation",
    "ITW": "Illinois Tool Works Inc",
    "EMR": "Emerson Electric Co",
    # US: Consumer Defensive
    "PG": "Procter & Gamble Company",
    "KO": "Coca-Cola Company",
    "PEP": "PepsiCo Inc",
    "COST": "Costco Wholesale Corporation",
    "WMT": "Walmart Inc",
    "PM": "Philip Morris International Inc",
    "MO": "Altria Group Inc",
    "CL": "Colgate-Palmolive Company",
    "MDLZ": "Mondelez International Inc",
    "KHC": "Kraft Heinz Company",
    "GIS": "General Mills Inc",
    "SJM": "J.M. Smucker Company",
    "HSY": "Hershey Company",
    # US: Energy
    "XOM": "Exxon Mobil Corporation",
    "CVX": "Chevron Corporation",
    "COP": "ConocoPhillips",
    "EOG": "EOG Resources Inc",
    "SLB": "Schlumberger Limited",
    "MPC": "Marathon Petroleum Corporation",
    "PSX": "Phillips 66",
    "VLO": "Valero Energy Corporation",
    "OXY": "Occidental Petroleum Corporation",
    "DVN": "Devon Energy Corporation",
    "HAL": "Halliburton Company",
    "FANG": "Diamondback Energy Inc",
    "KMI": "Kinder Morgan Inc",
    "WMB": "Williams Companies Inc",
    "OKE": "ONEOK Inc",
    # US: Communication Services
    "DIS": "Walt Disney Company",
    "NFLX": "Netflix Inc",
    "CMCSA": "Comcast Corporation",
    "T": "AT&T Inc",
    "VZ": "Verizon Communications Inc",
    "TMUS": "T-Mobile US Inc",
    "GOOG": "Alphabet Inc Class C",
    "CHTR": "Charter Communications Inc",
    "EA": "Electronic Arts Inc",
    "TTWO": "Take-Two Interactive Software",
    "MTCH": "Match Group Inc",
    # US: Utilities
    "NEE": "NextEra Energy Inc",
    "DUK": "Duke Energy Corporation",
    "SO": "Southern Company",
    "D": "Dominion Energy Inc",
    "SRE": "Sempra",
    "AEP": "American Electric Power Company",
    "EXC": "Exelon Corporation",
    "XEL": "Xcel Energy Inc",
    "WEC": "WEC Energy Group Inc",
    "ED": "Consolidated Edison Inc",
    # US: Real Estate
    "PLD": "Prologis Inc",
    "AMT": "American Tower Corporation",
    "CCI": "Crown Castle Inc",
    "EQIX": "Equinix Inc",
    "PSA": "Public Storage",
    "O": "Realty Income Corporation",
    "SPG": "Simon Property Group Inc",
    "WELL": "Welltower Inc",
    "DLR": "Digital Realty Trust Inc",
    # US: Basic Materials
    "LIN": "Linde plc",
    "APD": "Air Products and Chemicals Inc",
    "SHW": "Sherwin-Williams Company",
    "ECL": "Ecolab Inc",
    "NEM": "Newmont Corporation",
    "FCX": "Freeport-McMoRan Inc",
    "NUE": "Nucor Corporation",
    "DOW": "Dow Inc",
    "DD": "DuPont de Nemours Inc",
    # China / HK
    "BABA": "Alibaba Group Holding",
    "JD": "JD.com Inc",
    "BIDU": "Baidu Inc",
    "NIO": "NIO Inc",
    "LI": "Li Auto Inc",
    "XPEV": "XPeng Inc",
    "PDD": "PDD Holdings Inc Pinduoduo",
    "TME": "Tencent Music Entertainment",
    "BEKE": "KE Holdings Inc Beike",
    # Japan
    "TM": "Toyota Motor Corporation",
    "SONY": "Sony Group Corporation",
    "MUFG": "Mitsubishi UFJ Financial Group",
    # Taiwan
    "TSM": "Taiwan Semiconductor Manufacturing TSMC",
    # Europe
    "ASML": "ASML Holding NV",
    "NVO": "Novo Nordisk A/S",
    "SAP": "SAP SE",
    "SHEL": "Shell plc",
    "AZN": "AstraZeneca plc",
    "UL": "Unilever plc",
    "DEO": "Diageo plc",
    "TTE": "TotalEnergies SE",
    "SPOT": "Spotify Technology SA",
    # India
    "INFY": "Infosys Limited",
    "WIT": "Wipro Limited",
    "IBN": "ICICI Bank Limited",
    # Canada
    "SHOP": "Shopify Inc",
    "RY": "Royal Bank of Canada",
    "TD": "Toronto-Dominion Bank",
    # Brazil
    "VALE": "Vale SA",
    "PBR": "Petrobras Petroleo Brasileiro",
    "ITUB": "Itau Unibanco Holding",
    "NU": "Nu Holdings Ltd",
    # Singapore
    "SE": "Sea Limited",
    "GRAB": "Grab Holdings Limited",
    # Israel (US-listed)
    "TEVA": "Teva Pharmaceutical Industries",
    "CHKP": "Check Point Software Technologies",
    "NICE": "NICE Ltd",
    "WIX": "Wix.com Ltd",
    "MNDY": "monday.com Ltd",
    "CYBR": "CyberArk Software Ltd",
    "ICL": "ICL Group Ltd",
    "ESLT": "Elbit Systems Ltd",
    "FVRR": "Fiverr International Ltd",
    "GLBE": "Global-e Online Ltd",
    "ZIM": "ZIM Integrated Shipping Services",
    "SEDG": "SolarEdge Technologies Inc",
    "INMD": "InMode Ltd",
    "CEVA": "CEVA Inc",
    "ORA": "Ormat Technologies Inc",
    "RDWR": "Radware Ltd",
    "ALLT": "Allot Ltd",
    "PAYONR": "Payoneer Global Inc",
    # Israel (TASE)
    "LUMI.TA": "Bank Leumi",
    "POLI.TA": "Bank Hapoalim",
    "DSCT.TA": "Israel Discount Bank",
    "MZTF.TA": "Mizrahi Tefahot Bank",
    "BEZQ.TA": "Bezeq The Israeli Telecommunication Corp",
    "CEL.TA": "Cellcom Israel Ltd",
    "PTNR.TA": "Partner Communications Company",
    "AZRG.TA": "Azrieli Group Ltd",
    "MGDL.TA": "Migdal Insurance and Financial Holdings",
    "HAREL.TA": "Harel Insurance Investments and Financial Services",
    "DLEKG.TA": "Delek Group Ltd",
    "ORL.TA": "Bazan Group Oil Refineries",
    "STRS.TA": "Strauss Group Ltd",
    "ELCO.TA": "Elco Holdings Ltd",
    "AMOT.TA": "Amot Investments Ltd",
    # ── ETFs ──
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "VTI": "Vanguard Total Stock Market ETF",
    "VOO": "Vanguard S&P 500 ETF",
    "IWM": "iShares Russell 2000 ETF",
    "DIA": "SPDR Dow Jones Industrial Average ETF",
    "RSP": "Invesco S&P 500 Equal Weight ETF",
    "VEA": "Vanguard FTSE Developed Markets ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
    "EFA": "iShares MSCI EAFE ETF",
    "IEMG": "iShares Core MSCI Emerging Markets ETF",
    "FXI": "iShares China Large-Cap ETF",
    "MCHI": "iShares MSCI China ETF",
    "EWJ": "iShares MSCI Japan ETF",
    "EWY": "iShares MSCI South Korea ETF",
    "EWH": "iShares MSCI Hong Kong ETF",
    "EWT": "iShares MSCI Taiwan ETF",
    "INDA": "iShares MSCI India ETF",
    "EWZ": "iShares MSCI Brazil ETF",
    "EWG": "iShares MSCI Germany ETF",
    "EWU": "iShares MSCI United Kingdom ETF",
    "EWA": "iShares MSCI Australia ETF",
    "EWC": "iShares MSCI Canada ETF",
    "BND": "Vanguard Total Bond Market ETF",
    "AGG": "iShares Core US Aggregate Bond ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "LQD": "iShares iBoxx Investment Grade Corporate Bond ETF",
    "HYG": "iShares iBoxx High Yield Corporate Bond ETF",
    "TIP": "iShares TIPS Bond ETF",
    "VCSH": "Vanguard Short-Term Corporate Bond ETF",
    "VCIT": "Vanguard Intermediate-Term Corporate Bond ETF",
    "VIG": "Vanguard Dividend Appreciation ETF",
    "VYM": "Vanguard High Dividend Yield ETF",
    "SCHD": "Schwab US Dividend Equity ETF",
    "DVY": "iShares Select Dividend ETF",
    "HDV": "iShares Core High Dividend ETF",
    "JEPI": "JPMorgan Equity Premium Income ETF",
    "XLK": "Technology Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",
    "XLB": "Materials Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLC": "Communication Services Select Sector SPDR Fund",
    "ARKK": "ARK Innovation ETF",
    "ARKW": "ARK Next Generation Internet ETF",
    "SOXX": "iShares Semiconductor ETF",
    "SMH": "VanEck Semiconductor ETF",
    "KWEB": "KraneShares CSI China Internet ETF",
    "ICLN": "iShares Global Clean Energy ETF",
    "TAN": "Invesco Solar ETF",
    "GLD": "SPDR Gold Shares",
    "SLV": "iShares Silver Trust",
    "VNQ": "Vanguard Real Estate ETF",
    "USO": "United States Oil Fund",
    "DBC": "Invesco DB Commodity Index Tracking Fund",
}

# ── Search aliases: maps alternate names (Hebrew, abbreviations) to symbols ──
# Each symbol can have multiple aliases. The screener search checks these
# so users can find stocks by typing in Hebrew or common local names.
SEARCH_ALIASES: dict[str, list[str]] = {
    # Israel — US-listed
    "TEVA": ["טבע", "teva pharmaceutical", "טבע תעשיות פרמצבטיות"],
    "CHKP": ["צ'ק פוינט", "צק פוינט", "check point", "צ'קפוינט"],
    "NICE": ["נייס", "נאיס"],
    "WIX": ["וויקס", "ויקס"],
    "MNDY": ["מאנדיי", "מנדיי", "monday"],
    "CYBR": ["סייברארק", "סייבר ארק", "cyberark"],
    "ICL": ["כיל", "כימיקלים לישראל", "israel chemicals"],
    "ESLT": ["אלביט", "אלביט מערכות", "elbit systems"],
    "FVRR": ["פייבר", "fiverr"],
    "GLBE": ["גלובל אי", "global-e"],
    "ZIM": ["צים", "צים שירותי ספנות", "zim shipping"],
    "SEDG": ["סולאראדג", "סולאר אדג", "solaredge"],
    "INMD": ["אינמוד", "inmode"],
    "CEVA": ["סבא", "ceva inc"],
    "ORA": ["אורמת", "ormat"],
    "RDWR": ["רדוור", "radware"],
    "ALLT": ["אלוט", "allot"],
    "PAYONR": ["פיוניר", "payoneer"],
    # Israel — TASE
    "LUMI.TA": ["לאומי", "בנק לאומי", "bank leumi"],
    "POLI.TA": ["הפועלים", "בנק הפועלים", "bank hapoalim"],
    "DSCT.TA": ["דיסקונט", "בנק דיסקונט", "discount bank"],
    "MZTF.TA": ["מזרחי טפחות", "מזרחי", "בנק מזרחי", "mizrahi tefahot"],
    "BEZQ.TA": ["בזק", "bezeq"],
    "CEL.TA": ["סלקום", "cellcom"],
    "PTNR.TA": ["פרטנר", "partner"],
    "AZRG.TA": ["עזריאלי", "קבוצת עזריאלי", "azrieli"],
    "MGDL.TA": ["מגדל", "מגדל ביטוח", "migdal"],
    "HAREL.TA": ["הראל", "הראל ביטוח", "harel"],
    "DLEKG.TA": ["דלק", "קבוצת דלק", "delek"],
    "ORL.TA": ["בזן", "בתי זיקוק", "bazan"],
    "STRS.TA": ["שטראוס", "strauss"],
    "ELCO.TA": ["אלקו", "elco"],
    "AMOT.TA": ["אמות", "amot"],
    # Major international — common alternate names
    "BABA": ["עליבאבא", "alibaba"],
    "TSM": ["טיאסאמסי", "tsmc", "taiwan semiconductor"],
    "ASML": ["אסמל"],
    "NVO": ["נובו נורדיסק", "novo nordisk"],
    "SONY": ["סוני"],
    "TM": ["טויוטה", "toyota"],
    "SHOP": ["שופיפיי", "shopify"],
}

# Build a reverse lookup: lowercase alias → symbol for fast matching
_ALIAS_TO_SYMBOL: dict[str, str] = {}
for _sym, _aliases in SEARCH_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_TO_SYMBOL[_alias.lower()] = _sym

SECTORS = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Consumer Cyclical",
    "Industrials",
    "Communication Services",
    "Consumer Defensive",
    "Energy",
    "Basic Materials",
    "Real Estate",
    "Utilities",
]

REGIONS = [
    "US",
    "China / Hong Kong",
    "Japan",
    "South Korea",
    "Taiwan",
    "Europe",
    "India",
    "Australia",
    "Canada",
    "Brazil",
    "Singapore",
    "Israel",
]

_REGION_MAP = {}
_INTL = {
    "China / Hong Kong": {"BABA", "JD", "BIDU", "NIO", "LI", "XPEV", "PDD", "TME", "BEKE"},
    "Japan": {"TM", "SONY", "MUFG"},
    "Taiwan": {"TSM"},
    "Europe": {"ASML", "NVO", "SAP", "SHEL", "AZN", "UL", "DEO", "TTE", "SPOT"},
    "India": {"INFY", "WIT", "IBN"},
    "Canada": {"SHOP", "RY", "TD"},
    "Brazil": {"VALE", "PBR", "ITUB", "NU"},
    "Singapore": {"SE", "GRAB"},
    "Israel": {
        "TEVA", "CHKP", "NICE", "WIX", "MNDY", "CYBR", "ICL", "ESLT",
        "FVRR", "GLBE", "ZIM", "SEDG", "INMD", "CEVA", "ORA", "RDWR", "ALLT", "PAYONR",
        "LUMI.TA", "POLI.TA", "DSCT.TA", "MZTF.TA", "BEZQ.TA", "CEL.TA", "PTNR.TA",
        "AZRG.TA", "MGDL.TA", "HAREL.TA", "DLEKG.TA", "ORL.TA", "STRS.TA", "ELCO.TA", "AMOT.TA",
    },
}
for region, syms in _INTL.items():
    for sym in syms:
        _REGION_MAP[sym] = region
for sym in STOCK_UNIVERSE:
    if sym not in _REGION_MAP:
        _REGION_MAP[sym] = "US"


def get_region(symbol: str) -> str:
    return _REGION_MAP.get(symbol, "US")


MAX_WORKERS = 2 if _LOW_MEMORY else 5

WARM_PRIORITY = [
    "SPY",
    "QQQ",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "TSLA",
    "JPM",
    "NFLX",
    "AMD",
    "XOM",
    "LLY",
    "BABA",
    "TSM",
    "V",
    "MA",
    "BRK-B",
    "UNH",
    "JNJ",
    "PG",
    "HD",
    "DIS",
    "COST",
    "INTC",
    "VTI",
    "VOO",
    "IWM",
    "BND",
    "VIG",
    "SCHD",
    "XLK",
    "XLF",
    "ARKK",
    "GLD",
    "VNQ",
    "SOXX",
]


def _get_cached(key: str) -> Any:
    with _cache_lock:
        if key in _cache:
            ts, data = _cache[key]
            if time.time() - ts < CACHE_TTL:
                return data
    return None


def _set_cache(key: str, data: Any) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), data)
        # Evict expired entries when cache grows too large
        if len(_cache) > CACHE_MAX_ENTRIES:
            _evict_expired()


def _evict_expired():
    """Remove expired entries from cache. Must be called under _cache_lock."""
    now = time.time()
    expired = [k for k, (ts, _) in _cache.items() if now - ts >= CACHE_TTL]
    for k in expired:
        del _cache[k]
    # If still too large, evict oldest entries
    if len(_cache) > CACHE_MAX_ENTRIES:
        by_age = sorted(_cache.items(), key=lambda x: x[1][0])
        to_remove = len(_cache) - CACHE_MAX_ENTRIES + 50  # free 50 extra slots
        for k, _ in by_age[:to_remove]:
            del _cache[k]


def fetch_stock_info(symbol: str, full: bool = True) -> Optional[dict[str, Any]]:
    cached = _get_cached(f"info:{symbol}")
    if isinstance(cached, dict):
        return cast(dict[str, Any], cached)

    try:
        # data_provider already tries Yahoo first, Finnhub fallback
        quote = dp.get_quote(symbol)
        if not quote or quote.get("c", 0) <= 0:
            return None

        profile = dp.get_profile(symbol) or {}
        metrics: dict = dp.get_metrics(symbol) if full else None  # type: ignore[assignment]
        if metrics is None:
            metrics = {}

        price = quote["c"]
        prev_close = quote.get("pc", price)
        _set_cache(
            f"quote:{symbol}",
            {
                "symbol": symbol,
                "name": profile.get("name", symbol),
                "price": round(price, 2),
                "change": round(quote.get("d", price - prev_close), 2),
                "change_pct": round(quote.get("dp", 0), 2),
                "market_cap": (profile.get("marketCapitalization", 0) or 0) * 1_000_000,
                "volume": 0,
                "day_high": round(quote.get("h", price), 2),
                "day_low": round(quote.get("l", price), 2),
            },
        )

        price = quote["c"]
        w52_high = metrics.get("52WeekHigh")
        w52_low = metrics.get("52WeekLow")
        pct_from_high = round((price - w52_high) / w52_high * 100, 1) if w52_high and price else None
        pct_from_low = round((price - w52_low) / w52_low * 100, 1) if w52_low and price else None

        raw_div = metrics.get("dividendYieldIndicatedAnnual")
        div_yield = round(raw_div, 2) if raw_div else None
        if div_yield is not None and div_yield > 20:
            div_yield = None

        mcap_millions = profile.get("marketCapitalization", 0) or 0
        market_cap = mcap_millions * 1_000_000

        result = {
            "symbol": symbol,  # Always use the requested symbol, not Finnhub's ticker
            # which may include exchange suffixes (e.g. RY.TO, TTE.PA)
            "name": profile.get("name", symbol),
            "sector": profile.get("finnhubIndustry", "N/A"),
            "industry": profile.get("finnhubIndustry", "N/A"),
            "price": round(price, 2),
            "market_cap": market_cap,
            "pe_ratio": metrics.get("peTTM"),
            "forward_pe": metrics.get("peAnnual"),
            "dividend_yield": div_yield,
            "beta": metrics.get("beta"),
            "year_change": None,
            "recommendation": None,
            "expense_ratio": None,
            "asset_type": _classify_asset_fh(profile),
            "total_assets": None,
            "three_year_return": None,
            "five_year_return": None,
            "week52_high": w52_high,
            "week52_low": w52_low,
            "pct_from_high": pct_from_high,
            "pct_from_low": pct_from_low,
            "profit_margin": metrics.get("netProfitMarginTTM"),
            "revenue_growth": metrics.get("revenueGrowthTTMYoy"),
            "earnings_growth": metrics.get("epsGrowthTTMYoy"),
            "debt_to_equity": metrics.get("totalDebt/totalEquityQuarterly"),
            "return_on_equity": metrics.get("roeTTM"),
            "free_cash_flow": metrics.get("freeCashFlowTTM"),
            "current_ratio": metrics.get("currentRatio"),
            "price_to_book": metrics.get("priceToBook"),
            "trailing_eps": metrics.get("trailingEps"),
            "book_value": metrics.get("bookValue"),
            "target_mean_price": metrics.get("targetMeanPrice"),
            "target_high_price": metrics.get("targetHighPrice"),
            "target_low_price": metrics.get("targetLowPrice"),
            "num_analysts": None,
            "summary": "",
            "region": get_region(symbol),
        }
        _set_cache(f"info:{symbol}", result)
        return result
    except Exception as e:
        logger.warning("fetch_stock_info error for %s: %s", symbol, e)
        return None


def fetch_batch(symbols: list[str], cached_only: bool = False) -> list[dict]:
    """Fetch info for multiple symbols. If cached_only=True, skip uncached symbols."""
    cached_results = []
    uncached = []

    for sym in symbols:
        c = _get_cached(f"info:{sym}")
        if c and c.get("price", 0) > 0:
            cached_results.append(c)
        else:
            uncached.append(sym)

    if not uncached or cached_only:
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


def _pct(val: object) -> Optional[float]:
    if val is None:
        return None
    v = float(val)  # type: ignore[arg-type]
    return round(v * 100, 2) if abs(v) < 10 else round(v, 2)


def _pct_safe(val: object) -> Optional[float]:
    """Convert to percentage, guarding against values already in % form."""
    if val is None:
        return None
    v = float(val)  # type: ignore[arg-type]
    if abs(v) > 1:
        return round(v, 2)
    return round(v * 100, 2)


def _classify_asset(info: dict) -> str:
    qtype = info.get("quoteType", "").upper()
    if qtype == "ETF":
        return "ETF"
    if qtype == "MUTUALFUND":
        return "Fund"
    return "Stock"


def _classify_asset_fh(profile: dict) -> str:
    """Classify asset type from Finnhub profile data."""
    exchange = (profile.get("exchange") or "").upper()
    if "ETF" in exchange or profile.get("ticker", "") in ETF_UNIVERSE:
        return "ETF"
    return "Stock"


def format_market_cap(cap: float) -> str:
    if not cap:
        return "N/A"
    if cap >= 1e12:
        return f"${cap / 1e12:.1f}T"
    if cap >= 1e9:
        return f"${cap / 1e9:.1f}B"
    if cap >= 1e6:
        return f"${cap / 1e6:.0f}M"
    return f"${cap:,.0f}"


QUOTE_CACHE_TTL = 300  # 5 min cache for live quotes


def fetch_live_quotes(symbols: list[str]) -> list[dict]:
    cache_key = "live_quotes:" + ",".join(symbols)
    with _cache_lock:
        if cache_key in _cache:
            ts, data = _cache[cache_key]
            if time.time() - ts < QUOTE_CACHE_TTL:
                return data  # type: ignore[no-any-return]

    results = []
    _names = _batch_resolve_names(symbols)
    uncached_syms = []

    for sym in symbols:
        cached = _get_cached(f"quote:{sym}")
        if cached:
            cached["name"] = _names.get(sym, sym)
            results.append(cached)
            continue
        info = _get_cached(f"info:{sym}")
        if info and info.get("price", 0) > 0:
            entry = {
                "symbol": sym,
                "name": info.get("name", sym),
                "price": info["price"],
                "change": 0,
                "change_pct": 0,
                "market_cap": info.get("market_cap", 0),
                "volume": 0,
                "day_high": info["price"],
                "day_low": info["price"],
            }
            results.append(entry)
            continue
        uncached_syms.append(sym)

    def _fetch_one_quote(sym):
        try:
            quote = dp.get_quote(sym)
            if not quote or quote.get("c", 0) <= 0:
                return None
            price = quote["c"]
            prev = quote.get("pc", price)
            change = quote.get("d", price - prev)
            change_pct = quote.get("dp", (change / prev * 100) if prev else 0)
            entry = {
                "symbol": sym,
                "name": _names.get(sym, sym),
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "market_cap": 0,
                "volume": 0,
                "day_high": round(quote.get("h", price), 2),
                "day_low": round(quote.get("l", price), 2),
            }
            _set_cache(f"quote:{sym}", entry)
            return entry
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_one_quote, sym): sym for sym in uncached_syms}
        for future in as_completed(futures):
            entry = future.result()
            if entry:
                results.append(entry)

    sym_order = {s: i for i, s in enumerate(symbols)}
    results.sort(key=lambda x: sym_order.get(x["symbol"], 999))

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


_sparkline_lock = threading.Lock()  # prevent concurrent duplicate fetches


def fetch_sparklines(symbols: list[str], period: str = "5d", interval: str = "1h") -> dict[str, list[float]]:
    # Use daily resolution as primary — hourly is unreliable on both Yahoo and Finnhub free tier
    cache_key = f"sparklines:{','.join(symbols)}:daily"
    cached_raw = _get_cached(cache_key)
    cached: dict[str, list[float]] | None = cached_raw if isinstance(cached_raw, dict) else None
    if cached:
        # Serve cache if it has data for all symbols OR if it's reasonably full
        filled = sum(1 for v in cached.values() if v)
        if filled == len(symbols):
            return cached
        if filled >= len(symbols) * 0.5:
            # Serve partial cache — better than empty charts
            logger.info("Sparkline cache partial (%d/%d filled), serving stale + refreshing gaps", filled, len(symbols))

    # Serialize sparkline fetches: if another thread is already fetching,
    # wait for it then return the (now-cached) result instead of doubling API calls.
    acquired = _sparkline_lock.acquire(timeout=30)
    if not acquired:
        logger.warning("Sparkline fetch lock timeout — returning cached/empty")
        return cached if cached else {s: [] for s in symbols}

    try:
        # Re-check cache — another thread may have just populated it
        cached_raw2 = _get_cached(cache_key)
        cached = cached_raw2 if isinstance(cached_raw2, dict) else None
        if cached:
            filled = sum(1 for v in cached.values() if v)
            if filled == len(symbols):
                return cached

        period_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "1y": 365}
        days = period_map.get(period, 5)

        # Round timestamps to the nearest hour so data_provider candle cache
        # (keyed by symbol:from_ts:to_ts) actually gets hits across page loads
        # instead of creating a unique cache key every second.
        now = int(time.time())
        to_ts = (now // 3600) * 3600 + 3600  # end of current UTC hour
        from_ts = to_ts - max(days * 2, 10) * 86400

        # Merge with existing cache so previously-successful symbols aren't lost
        result = dict(cached) if cached else {}

        # Fetch symbols that are missing or empty, using daily resolution (most reliable)
        symbols_to_fetch = [s for s in symbols if not result.get(s)]
        if not symbols_to_fetch and cached:
            return cached

        # Fetch each symbol independently — isolate failures so one bad symbol
        # doesn't kill Yahoo for the rest (each call handles its own fallback)
        for i, sym in enumerate(symbols_to_fetch):
            try:
                candles = dp.get_candles(sym, "D", from_ts, to_ts)
                if candles and candles.get("c") and len(candles["c"]) > 1:
                    result[sym] = [round(v, 2) for v in candles["c"]]
                else:
                    result[sym] = result.get(sym, [])
                    logger.warning("Sparkline: no daily candles for %s", sym)
            except Exception as e:
                result[sym] = result.get(sym, [])
                logger.warning("Sparkline: exception for %s: %s", sym, e)
            # Small delay between symbols to smooth Finnhub rate-limit consumption
            if i < len(symbols_to_fetch) - 1:
                time.sleep(0.3)

        # Last-resort batch fallback: if per-symbol fetches failed for some symbols,
        # try yf.download() which batches all symbols in ONE HTTP call.
        # This avoids Yahoo rate-limiting that kills per-symbol Ticker.history() calls.
        # Skip in TESTING mode to avoid hanging on external HTTP calls.
        _testing = os.environ.get("TESTING") == "1"
        still_empty = [s for s in symbols if not result.get(s)]
        if still_empty and not _testing:
            logger.info("Sparkline: %d/%d still empty, trying batch yf.download()", len(still_empty), len(symbols))
            try:
                batch = dp.batch_download_candles(still_empty, period="1mo", interval="1d")
                for sym, candles in batch.items():
                    if candles and candles.get("c") and len(candles["c"]) > 1:
                        result[sym] = [round(v, 2) for v in candles["c"]]
            except Exception as e:
                logger.warning("Sparkline batch download failed: %s", e)

        # Ensure all requested symbols have a key
        for sym in symbols:
            if sym not in result:
                result[sym] = []

        # Cache strategy: always cache what we have; use shorter TTL for partial results
        empty_count = sum(1 for s in symbols if not result.get(s))
        if empty_count == 0:
            _set_cache(cache_key, result)
        elif empty_count < len(symbols):
            # Partial success: cache for 5 minutes to reduce API hammering
            # but still retry relatively soon
            with _cache_lock:
                _cache[cache_key] = (time.time() - CACHE_TTL + 300, result)
            logger.warning("Sparkline partial (%d/%d empty), cached 5min", empty_count, len(symbols))
        # If all empty, don't cache at all

        return result
    finally:
        _sparkline_lock.release()


# ── Scheduler-friendly refresh for homepage symbols ──────────

# Canonical list of symbols that appear on the homepage ticker + featured
# cards.  Duplicated from routers/market.py to avoid a circular import.
_ACTIVE_SYMBOLS = list(
    dict.fromkeys(
        [
            "SPY",
            "QQQ",
            "AAPL",
            "MSFT",
            "GOOGL",
            "NVDA",
            "TSLA",
            "AMZN",
        ]
    )
)
_FEATURED_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL"]


def refresh_active_symbols():
    """Pre-warm live quotes + sparklines for homepage symbols.

    Called by the background scheduler every ~2 min so the first user
    hitting /api/market/home sees instant results instead of waiting
    for 10+ quote fetches.
    """
    logger.info("refresh_active_symbols: refreshing %d symbols", len(_ACTIVE_SYMBOLS))
    try:
        fetch_live_quotes(_ACTIVE_SYMBOLS)
    except Exception:
        logger.exception("refresh_active_symbols: quotes failed")

    try:
        fetch_sparklines(_FEATURED_SYMBOLS)
    except Exception:
        logger.exception("refresh_active_symbols: sparklines failed")

    logger.info("refresh_active_symbols: done")


# ── Background cache warming ────────────────────


def warm_cache():
    """Phase 1: priority symbols (fast). Phase 2: rest of universe (background batches)."""
    global _warming
    if _warming:
        return
    _warming = True

    # Phase 1 — priority symbols for homepage (small batches to stay under rate limits)
    logger.info("Cache warm phase 1: %d priority symbols", len(WARM_PRIORITY))
    t0 = time.time()
    batch_size = 8
    for i in range(0, len(WARM_PRIORITY), batch_size):
        batch = WARM_PRIORITY[i : i + batch_size]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(fetch_stock_info, sym, True): sym for sym in batch}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception:
                    pass
        if i + batch_size < len(WARM_PRIORITY):
            time.sleep(2)  # breathe between batches to avoid rate-limit pileup
    logger.info("Cache warm phase 1 done in %.1fs", time.time() - t0)
    _warm_done.set()

    # Phase 2 — remaining universe (sequential batches, no rush)
    rest = [s for s in ALL_UNIVERSE if not _get_cached(f"info:{s}")]
    if rest:
        logger.info("Cache warm phase 2: %d remaining symbols", len(rest))
        for i in range(0, len(rest), batch_size):
            batch = rest[i : i + batch_size]
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(fetch_stock_info, sym, True): sym for sym in batch}
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception:
                        pass
            time.sleep(3)  # larger pause between phase-2 batches
        logger.info("Cache warm phase 2 done in %.1fs total", time.time() - t0)

    # Phase 3 — build screener snapshot now that all data is cached
    try:
        from src.services.screener import refresh_screener_snapshot

        refresh_screener_snapshot()
    except Exception:
        logger.exception("Failed to refresh screener snapshot after cache warm")

    # Persist market cache snapshot to DB
    try:
        from src.services.persistence import save_market_cache_snapshot

        with _cache_lock:
            save_market_cache_snapshot(dict(_cache))
    except Exception:
        logger.exception("Failed to persist market cache snapshot")

    _warming = False


def start_cache_warmer():
    """Launch background thread that warms cache on startup and refreshes periodically."""

    def _loop():
        while True:
            try:
                warm_cache()
            except Exception as e:
                logger.error("Cache warmer error: %s", e)
            # Evict stale cache entries between warm cycles
            with _cache_lock:
                _evict_expired()
                logger.info("Cache size after eviction: %d entries", len(_cache))
            time.sleep(CACHE_TTL - 60)  # refresh 1 min before expiry

    t = threading.Thread(target=_loop, daemon=True, name="cache-warmer")
    t.start()


def get_cache_status() -> dict:
    """Return how many symbols are cached and whether warming is in progress."""
    with _cache_lock:
        now = time.time()
        cached_count = sum(1 for k, (ts, _) in _cache.items() if k.startswith("info:") and now - ts < CACHE_TTL)
    return {
        "cached": cached_count,
        "total": len(ALL_UNIVERSE),
        "warming": _warming,
        "ready": _warm_done.is_set(),
    }
