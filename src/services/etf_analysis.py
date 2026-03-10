"""ETF deep analysis service — holdings, overlap, comparison, screening.

Provides:
  - Curated top-10 holdings per ETF
  - Holdings overlap between any two ETFs
  - Category / region / type classification
  - ETF-vs-ETF comparison
  - Screening with filters (expense ratio, AUM, yield, category)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.services.market_data import ETF_UNIVERSE, fetch_batch

logger = logging.getLogger(__name__)

# ── ETF category classifications ──────────────────────────────
ETF_CATEGORIES: dict[str, dict[str, str]] = {
    # Broad US Market
    "SPY": {"category": "US Large Cap", "region": "US", "type": "Equity", "focus": "Broad Market"},
    "QQQ": {"category": "US Large Cap Growth", "region": "US", "type": "Equity", "focus": "Tech-Heavy"},
    "VTI": {"category": "US Total Market", "region": "US", "type": "Equity", "focus": "Broad Market"},
    "VOO": {"category": "US Large Cap", "region": "US", "type": "Equity", "focus": "Broad Market"},
    "IWM": {"category": "US Small Cap", "region": "US", "type": "Equity", "focus": "Small Cap"},
    "DIA": {"category": "US Large Cap", "region": "US", "type": "Equity", "focus": "Blue Chip"},
    "RSP": {"category": "US Large Cap", "region": "US", "type": "Equity", "focus": "Equal Weight"},
    # International / Emerging
    "VEA": {"category": "Intl Developed", "region": "International", "type": "Equity", "focus": "Developed"},
    "VWO": {"category": "Emerging Markets", "region": "Emerging", "type": "Equity", "focus": "Broad EM"},
    "EFA": {"category": "Intl Developed", "region": "International", "type": "Equity", "focus": "Developed"},
    "IEMG": {"category": "Emerging Markets", "region": "Emerging", "type": "Equity", "focus": "Broad EM"},
    "FXI": {"category": "China", "region": "Asia", "type": "Equity", "focus": "China Large-Cap"},
    "MCHI": {"category": "China", "region": "Asia", "type": "Equity", "focus": "China"},
    "EWJ": {"category": "Japan", "region": "Asia", "type": "Equity", "focus": "Japan"},
    "EWY": {"category": "South Korea", "region": "Asia", "type": "Equity", "focus": "South Korea"},
    "EWH": {"category": "Hong Kong", "region": "Asia", "type": "Equity", "focus": "Hong Kong"},
    "EWT": {"category": "Taiwan", "region": "Asia", "type": "Equity", "focus": "Taiwan"},
    "INDA": {"category": "India", "region": "Asia", "type": "Equity", "focus": "India"},
    "EWZ": {"category": "Brazil", "region": "Latin America", "type": "Equity", "focus": "Brazil"},
    "EWG": {"category": "Germany", "region": "Europe", "type": "Equity", "focus": "Germany"},
    "EWU": {"category": "United Kingdom", "region": "Europe", "type": "Equity", "focus": "UK"},
    "EWA": {"category": "Australia", "region": "Asia-Pacific", "type": "Equity", "focus": "Australia"},
    "EWC": {"category": "Canada", "region": "North America", "type": "Equity", "focus": "Canada"},
    "IEFA": {"category": "Intl Developed", "region": "International", "type": "Equity", "focus": "Developed"},
    "ACWI": {"category": "Global", "region": "Global", "type": "Equity", "focus": "All-World"},
    "EEM": {"category": "Emerging Markets", "region": "Emerging", "type": "Equity", "focus": "Broad EM"},
    "ACWX": {"category": "Intl All-World ex-US", "region": "International", "type": "Equity", "focus": "Ex-US"},
    # Bonds
    "BND": {"category": "US Total Bond", "region": "US", "type": "Bond", "focus": "Investment Grade"},
    "AGG": {"category": "US Aggregate Bond", "region": "US", "type": "Bond", "focus": "Investment Grade"},
    "TLT": {"category": "US Long-Term Treasury", "region": "US", "type": "Bond", "focus": "Treasury"},
    "LQD": {"category": "US Investment Grade Corp", "region": "US", "type": "Bond", "focus": "Corporate"},
    "HYG": {"category": "US High Yield Corp", "region": "US", "type": "Bond", "focus": "High Yield"},
    "TIP": {"category": "US TIPS", "region": "US", "type": "Bond", "focus": "Inflation-Protected"},
    "VCSH": {"category": "US Short-Term Corp", "region": "US", "type": "Bond", "focus": "Short Duration"},
    "VCIT": {"category": "US Intermediate Corp", "region": "US", "type": "Bond", "focus": "Intermediate"},
    "IGSB": {"category": "US Short-Term Corp", "region": "US", "type": "Bond", "focus": "Short Duration"},
    "GOVT": {"category": "US Treasury", "region": "US", "type": "Bond", "focus": "Treasury"},
    "SGOV": {"category": "US Ultra-Short Treasury", "region": "US", "type": "Bond", "focus": "Cash-Like"},
    "SHY": {"category": "US Short-Term Treasury", "region": "US", "type": "Bond", "focus": "Short Duration"},
    "IEF": {"category": "US Intermediate Treasury", "region": "US", "type": "Bond", "focus": "Treasury"},
    "SHV": {"category": "US Short Treasury", "region": "US", "type": "Bond", "focus": "Cash-Like"},
    "PFF": {"category": "US Preferred Stock", "region": "US", "type": "Bond", "focus": "Preferred"},
    # Dividend / Income
    "VIG": {"category": "US Dividend Growth", "region": "US", "type": "Equity", "focus": "Dividend Growth"},
    "VYM": {"category": "US High Dividend", "region": "US", "type": "Equity", "focus": "High Yield"},
    "SCHD": {"category": "US Dividend", "region": "US", "type": "Equity", "focus": "Quality Dividend"},
    "DVY": {"category": "US Dividend Select", "region": "US", "type": "Equity", "focus": "High Yield"},
    "HDV": {"category": "US High Dividend", "region": "US", "type": "Equity", "focus": "High Yield"},
    "JEPI": {"category": "US Equity Income", "region": "US", "type": "Equity", "focus": "Options Income"},
    "COWZ": {"category": "US Value", "region": "US", "type": "Equity", "focus": "Cash Flow"},
    # Sector ETFs
    "XLK": {"category": "Technology", "region": "US", "type": "Sector", "focus": "Technology"},
    "XLF": {"category": "Financials", "region": "US", "type": "Sector", "focus": "Financials"},
    "XLE": {"category": "Energy", "region": "US", "type": "Sector", "focus": "Energy"},
    "XLV": {"category": "Healthcare", "region": "US", "type": "Sector", "focus": "Healthcare"},
    "XLI": {"category": "Industrials", "region": "US", "type": "Sector", "focus": "Industrials"},
    "XLP": {"category": "Consumer Staples", "region": "US", "type": "Sector", "focus": "Staples"},
    "XLY": {"category": "Consumer Discretionary", "region": "US", "type": "Sector", "focus": "Discretionary"},
    "XLB": {"category": "Materials", "region": "US", "type": "Sector", "focus": "Materials"},
    "XLU": {"category": "Utilities", "region": "US", "type": "Sector", "focus": "Utilities"},
    "XLRE": {"category": "Real Estate", "region": "US", "type": "Sector", "focus": "Real Estate"},
    "XLC": {"category": "Communication", "region": "US", "type": "Sector", "focus": "Communication"},
    "XBI": {"category": "Biotech", "region": "US", "type": "Sector", "focus": "Biotech"},
    "IBB": {"category": "Biotech", "region": "US", "type": "Sector", "focus": "Biotech"},
    "KRE": {"category": "Regional Banks", "region": "US", "type": "Sector", "focus": "Banking"},
    "XME": {"category": "Metals & Mining", "region": "US", "type": "Sector", "focus": "Metals"},
    "XRT": {"category": "Retail", "region": "US", "type": "Sector", "focus": "Retail"},
    "XHB": {"category": "Homebuilders", "region": "US", "type": "Sector", "focus": "Housing"},
    "ITB": {"category": "Homebuilders", "region": "US", "type": "Sector", "focus": "Housing"},
    # Thematic
    "ARKK": {"category": "Disruptive Innovation", "region": "Global", "type": "Thematic", "focus": "Innovation"},
    "ARKW": {"category": "Next Gen Internet", "region": "Global", "type": "Thematic", "focus": "Internet"},
    "ARKG": {"category": "Genomic Revolution", "region": "Global", "type": "Thematic", "focus": "Genomics"},
    "SOXX": {"category": "Semiconductors", "region": "US", "type": "Thematic", "focus": "Semiconductors"},
    "SMH": {"category": "Semiconductors", "region": "Global", "type": "Thematic", "focus": "Semiconductors"},
    "KWEB": {"category": "China Internet", "region": "Asia", "type": "Thematic", "focus": "China Tech"},
    "ICLN": {"category": "Clean Energy", "region": "Global", "type": "Thematic", "focus": "Clean Energy"},
    "TAN": {"category": "Solar Energy", "region": "Global", "type": "Thematic", "focus": "Solar"},
    "CIBR": {"category": "Cybersecurity", "region": "Global", "type": "Thematic", "focus": "Cybersecurity"},
    "LIT": {"category": "Lithium & Battery", "region": "Global", "type": "Thematic", "focus": "Batteries"},
    "BOTZ": {"category": "Robotics & AI", "region": "Global", "type": "Thematic", "focus": "Robotics"},
    "JETS": {"category": "Airlines", "region": "US", "type": "Thematic", "focus": "Airlines"},
    "BITO": {"category": "Bitcoin Futures", "region": "Global", "type": "Alternative", "focus": "Crypto"},
    "WCLD": {"category": "Cloud Computing", "region": "Global", "type": "Thematic", "focus": "Cloud"},
    "HACK": {"category": "Cybersecurity", "region": "Global", "type": "Thematic", "focus": "Cybersecurity"},
    "ROBO": {"category": "Robotics & AI", "region": "Global", "type": "Thematic", "focus": "Robotics"},
    # Commodities
    "GLD": {"category": "Gold", "region": "Global", "type": "Commodity", "focus": "Gold"},
    "SLV": {"category": "Silver", "region": "Global", "type": "Commodity", "focus": "Silver"},
    "VNQ": {"category": "US Real Estate", "region": "US", "type": "Real Estate", "focus": "REITs"},
    "IYR": {"category": "US Real Estate", "region": "US", "type": "Real Estate", "focus": "REITs"},
    "USO": {"category": "Crude Oil", "region": "Global", "type": "Commodity", "focus": "Oil"},
    "DBC": {"category": "Commodities Basket", "region": "Global", "type": "Commodity", "focus": "Diversified"},
    # Factor / Style
    "VTV": {"category": "US Large Cap Value", "region": "US", "type": "Equity", "focus": "Value"},
    "VUG": {"category": "US Large Cap Growth", "region": "US", "type": "Equity", "focus": "Growth"},
    "MTUM": {"category": "US Momentum", "region": "US", "type": "Factor", "focus": "Momentum"},
    "QUAL": {"category": "US Quality", "region": "US", "type": "Factor", "focus": "Quality"},
    "VGT": {"category": "US Info Tech", "region": "US", "type": "Sector", "focus": "Technology"},
    "QQQM": {"category": "US Large Cap Growth", "region": "US", "type": "Equity", "focus": "Tech-Heavy"},
    "SCHG": {"category": "US Large Cap Growth", "region": "US", "type": "Equity", "focus": "Growth"},
    "VBR": {"category": "US Small Cap Value", "region": "US", "type": "Equity", "focus": "Small Value"},
    "SPLG": {"category": "US Large Cap", "region": "US", "type": "Equity", "focus": "Broad Market"},
    "MGK": {"category": "US Mega Cap Growth", "region": "US", "type": "Equity", "focus": "Mega Cap"},
    "IJR": {"category": "US Small Cap", "region": "US", "type": "Equity", "focus": "Small Cap"},
    "IJH": {"category": "US Mid Cap", "region": "US", "type": "Equity", "focus": "Mid Cap"},
    "MDY": {"category": "US Mid Cap", "region": "US", "type": "Equity", "focus": "Mid Cap"},
    "SPTM": {"category": "US Total Market", "region": "US", "type": "Equity", "focus": "Broad Market"},
    "SPMD": {"category": "US Mid Cap", "region": "US", "type": "Equity", "focus": "Mid Cap"},
    "SPSM": {"category": "US Small Cap", "region": "US", "type": "Equity", "focus": "Small Cap"},
    "VXF": {"category": "US Extended Market", "region": "US", "type": "Equity", "focus": "Mid+Small"},
}

# ── Curated top holdings (top ~10 per major ETF) ─────────────
_TOP_HOLDINGS: dict[str, list[dict[str, Any]]] = {
    "SPY": [
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 7.1},
        {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 6.5},
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 6.2},
        {"symbol": "AMZN", "name": "Amazon.com Inc", "weight": 3.8},
        {"symbol": "META", "name": "Meta Platforms", "weight": 2.6},
        {"symbol": "GOOGL", "name": "Alphabet Inc A", "weight": 2.1},
        {"symbol": "GOOG", "name": "Alphabet Inc C", "weight": 1.8},
        {"symbol": "BRK.B", "name": "Berkshire Hathaway B", "weight": 1.7},
        {"symbol": "LLY", "name": "Eli Lilly", "weight": 1.5},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 1.5},
    ],
    "QQQ": [
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 8.9},
        {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 8.1},
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 7.8},
        {"symbol": "AMZN", "name": "Amazon.com Inc", "weight": 5.3},
        {"symbol": "META", "name": "Meta Platforms", "weight": 3.6},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 3.4},
        {"symbol": "GOOGL", "name": "Alphabet Inc A", "weight": 2.8},
        {"symbol": "GOOG", "name": "Alphabet Inc C", "weight": 2.5},
        {"symbol": "COST", "name": "Costco Wholesale", "weight": 2.4},
        {"symbol": "TSLA", "name": "Tesla Inc", "weight": 2.2},
    ],
    "VTI": [
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 6.4},
        {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 5.9},
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 5.5},
        {"symbol": "AMZN", "name": "Amazon.com Inc", "weight": 3.4},
        {"symbol": "META", "name": "Meta Platforms", "weight": 2.4},
        {"symbol": "GOOGL", "name": "Alphabet Inc A", "weight": 1.9},
        {"symbol": "GOOG", "name": "Alphabet Inc C", "weight": 1.6},
        {"symbol": "BRK.B", "name": "Berkshire Hathaway B", "weight": 1.5},
        {"symbol": "LLY", "name": "Eli Lilly", "weight": 1.4},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 1.3},
    ],
    "VOO": [
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 7.1},
        {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 6.5},
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 6.2},
        {"symbol": "AMZN", "name": "Amazon.com Inc", "weight": 3.8},
        {"symbol": "META", "name": "Meta Platforms", "weight": 2.6},
        {"symbol": "GOOGL", "name": "Alphabet Inc A", "weight": 2.1},
        {"symbol": "GOOG", "name": "Alphabet Inc C", "weight": 1.8},
        {"symbol": "BRK.B", "name": "Berkshire Hathaway B", "weight": 1.7},
        {"symbol": "LLY", "name": "Eli Lilly", "weight": 1.5},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 1.5},
    ],
    "IWM": [
        {"symbol": "SMCI", "name": "Super Micro Computer", "weight": 0.7},
        {"symbol": "INSM", "name": "Insmed Inc", "weight": 0.5},
        {"symbol": "FNF", "name": "Fidelity National Financial", "weight": 0.4},
        {"symbol": "EWBC", "name": "East West Bancorp", "weight": 0.4},
        {"symbol": "IBKR", "name": "Interactive Brokers", "weight": 0.4},
        {"symbol": "CRS", "name": "Carpenter Technology", "weight": 0.4},
        {"symbol": "CASY", "name": "Casey's General Stores", "weight": 0.4},
        {"symbol": "MTG", "name": "MGIC Investment", "weight": 0.3},
        {"symbol": "LUMN", "name": "Lumen Technologies", "weight": 0.3},
        {"symbol": "FTNT", "name": "Fortinet Inc", "weight": 0.3},
    ],
    "SCHD": [
        {"symbol": "ABBV", "name": "AbbVie Inc", "weight": 4.5},
        {"symbol": "HD", "name": "Home Depot", "weight": 4.3},
        {"symbol": "AMGN", "name": "Amgen Inc", "weight": 4.2},
        {"symbol": "CVX", "name": "Chevron Corp", "weight": 4.1},
        {"symbol": "MRK", "name": "Merck & Co", "weight": 4.0},
        {"symbol": "VZ", "name": "Verizon Comm", "weight": 3.9},
        {"symbol": "KO", "name": "Coca-Cola Co", "weight": 3.8},
        {"symbol": "PEP", "name": "PepsiCo Inc", "weight": 3.7},
        {"symbol": "CSCO", "name": "Cisco Systems", "weight": 3.5},
        {"symbol": "TXN", "name": "Texas Instruments", "weight": 3.4},
    ],
    "XLK": [
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 16.5},
        {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 14.8},
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 14.2},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 5.1},
        {"symbol": "CRM", "name": "Salesforce Inc", "weight": 2.5},
        {"symbol": "ORCL", "name": "Oracle Corp", "weight": 2.3},
        {"symbol": "AMD", "name": "Advanced Micro Devices", "weight": 2.0},
        {"symbol": "ADBE", "name": "Adobe Inc", "weight": 1.9},
        {"symbol": "NOW", "name": "ServiceNow", "weight": 1.8},
        {"symbol": "INTU", "name": "Intuit Inc", "weight": 1.5},
    ],
    "GLD": [
        {"symbol": "GOLD", "name": "Gold Bullion", "weight": 100.0},
    ],
    "VIG": [
        {"symbol": "AAPL", "name": "Apple Inc", "weight": 4.5},
        {"symbol": "MSFT", "name": "Microsoft Corp", "weight": 4.2},
        {"symbol": "JPM", "name": "JPMorgan Chase", "weight": 3.5},
        {"symbol": "UNH", "name": "UnitedHealth Group", "weight": 3.3},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 2.8},
        {"symbol": "V", "name": "Visa Inc", "weight": 2.5},
        {"symbol": "HD", "name": "Home Depot", "weight": 2.2},
        {"symbol": "MA", "name": "Mastercard", "weight": 2.0},
        {"symbol": "PG", "name": "Procter & Gamble", "weight": 1.9},
        {"symbol": "COST", "name": "Costco", "weight": 1.8},
    ],
    "SOXX": [
        {"symbol": "NVDA", "name": "NVIDIA Corp", "weight": 9.8},
        {"symbol": "AVGO", "name": "Broadcom Inc", "weight": 8.5},
        {"symbol": "AMD", "name": "Advanced Micro Devices", "weight": 7.2},
        {"symbol": "QCOM", "name": "Qualcomm Inc", "weight": 6.0},
        {"symbol": "TXN", "name": "Texas Instruments", "weight": 5.5},
        {"symbol": "INTC", "name": "Intel Corp", "weight": 4.8},
        {"symbol": "MU", "name": "Micron Technology", "weight": 4.5},
        {"symbol": "MRVL", "name": "Marvell Technology", "weight": 4.0},
        {"symbol": "LRCX", "name": "Lam Research", "weight": 3.8},
        {"symbol": "KLAC", "name": "KLA Corp", "weight": 3.5},
    ],
    "ARKK": [
        {"symbol": "TSLA", "name": "Tesla Inc", "weight": 11.5},
        {"symbol": "COIN", "name": "Coinbase Global", "weight": 8.2},
        {"symbol": "ROKU", "name": "Roku Inc", "weight": 7.5},
        {"symbol": "SQ", "name": "Block Inc", "weight": 6.0},
        {"symbol": "PATH", "name": "UiPath Inc", "weight": 5.5},
        {"symbol": "SHOP", "name": "Shopify Inc", "weight": 5.0},
        {"symbol": "PLTR", "name": "Palantir Technologies", "weight": 4.5},
        {"symbol": "RBLX", "name": "Roblox Corp", "weight": 4.0},
        {"symbol": "DKNG", "name": "DraftKings Inc", "weight": 3.5},
        {"symbol": "U", "name": "Unity Software", "weight": 3.0},
    ],
}

# ── Approximate expense ratios (basis points → percentage) ────
_EXPENSE_RATIOS: dict[str, float] = {
    "SPY": 0.09,
    "QQQ": 0.20,
    "VTI": 0.03,
    "VOO": 0.03,
    "IWM": 0.19,
    "DIA": 0.16,
    "RSP": 0.20,
    "VEA": 0.05,
    "VWO": 0.08,
    "EFA": 0.32,
    "IEMG": 0.09,
    "FXI": 0.74,
    "MCHI": 0.59,
    "EWJ": 0.50,
    "EWY": 0.59,
    "EWH": 0.50,
    "EWT": 0.59,
    "INDA": 0.65,
    "EWZ": 0.59,
    "EWG": 0.50,
    "EWU": 0.50,
    "EWA": 0.50,
    "EWC": 0.50,
    "BND": 0.03,
    "AGG": 0.03,
    "TLT": 0.15,
    "LQD": 0.14,
    "HYG": 0.49,
    "TIP": 0.19,
    "VCSH": 0.04,
    "VCIT": 0.04,
    "VIG": 0.05,
    "VYM": 0.06,
    "SCHD": 0.06,
    "DVY": 0.38,
    "HDV": 0.08,
    "JEPI": 0.35,
    "XLK": 0.09,
    "XLF": 0.09,
    "XLE": 0.09,
    "XLV": 0.09,
    "XLI": 0.09,
    "XLP": 0.09,
    "XLY": 0.09,
    "XLB": 0.09,
    "XLU": 0.09,
    "XLRE": 0.09,
    "XLC": 0.09,
    "ARKK": 0.75,
    "ARKW": 0.82,
    "SOXX": 0.35,
    "SMH": 0.35,
    "KWEB": 0.70,
    "ICLN": 0.40,
    "TAN": 0.69,
    "GLD": 0.40,
    "SLV": 0.50,
    "VNQ": 0.12,
    "USO": 0.60,
    "DBC": 0.87,
    "XBI": 0.35,
    "IBB": 0.44,
    "VTV": 0.04,
    "VUG": 0.04,
    "IGSB": 0.04,
    "GOVT": 0.05,
    "MTUM": 0.15,
    "QUAL": 0.15,
    "ARKG": 0.75,
    "CIBR": 0.60,
    "LIT": 0.75,
    "BOTZ": 0.68,
    "JETS": 0.60,
    "BITO": 0.95,
    "XHB": 0.35,
    "ITB": 0.40,
    "XRT": 0.35,
    "KRE": 0.35,
    "XME": 0.35,
    "WCLD": 0.45,
    "VGT": 0.10,
    "COWZ": 0.49,
    "QQQM": 0.15,
    "IJR": 0.06,
    "IJH": 0.05,
    "MDY": 0.23,
    "IEFA": 0.07,
    "ACWI": 0.32,
    "EEM": 0.68,
    "SGOV": 0.09,
    "SHY": 0.15,
    "IEF": 0.15,
    "PFF": 0.46,
    "IYR": 0.39,
    "SCHG": 0.04,
    "VBR": 0.07,
    "SPLG": 0.02,
    "SPTM": 0.03,
    "SPMD": 0.03,
    "SPSM": 0.03,
    "VXF": 0.06,
    "ACWX": 0.32,
    "SHV": 0.15,
    "MGK": 0.07,
    "HACK": 0.60,
    "ROBO": 0.95,
}

# ── Sector allocation per ETF (approximate %) ────────────────
_SECTOR_ALLOC: dict[str, dict[str, float]] = {
    "SPY": {
        "Technology": 31.5,
        "Healthcare": 12.1,
        "Financials": 13.0,
        "Consumer Discretionary": 10.2,
        "Communication": 8.9,
        "Industrials": 8.5,
        "Consumer Staples": 5.8,
        "Energy": 3.6,
        "Utilities": 2.4,
        "Real Estate": 2.2,
        "Materials": 1.8,
    },
    "QQQ": {
        "Technology": 51.2,
        "Communication": 16.0,
        "Consumer Discretionary": 13.5,
        "Healthcare": 6.8,
        "Consumer Staples": 4.5,
        "Industrials": 4.0,
        "Energy": 1.5,
        "Utilities": 1.0,
        "Financials": 0.8,
        "Real Estate": 0.5,
        "Materials": 0.2,
    },
    "VTI": {
        "Technology": 29.5,
        "Healthcare": 12.5,
        "Financials": 13.5,
        "Consumer Discretionary": 10.0,
        "Communication": 8.5,
        "Industrials": 9.0,
        "Consumer Staples": 5.5,
        "Energy": 4.0,
        "Utilities": 2.8,
        "Real Estate": 2.7,
        "Materials": 2.0,
    },
    "SCHD": {
        "Healthcare": 15.5,
        "Financials": 14.0,
        "Technology": 12.0,
        "Consumer Staples": 11.5,
        "Industrials": 10.5,
        "Energy": 10.0,
        "Communication": 8.0,
        "Consumer Discretionary": 7.0,
        "Utilities": 5.5,
        "Materials": 4.0,
        "Real Estate": 2.0,
    },
    "ARKK": {
        "Technology": 35.0,
        "Communication": 20.0,
        "Healthcare": 18.0,
        "Financials": 12.0,
        "Consumer Discretionary": 10.0,
        "Industrials": 5.0,
    },
}

# ── Geography allocation per ETF (approximate %) ─────────────
_GEO_ALLOC: dict[str, dict[str, float]] = {
    "SPY": {"United States": 100.0},
    "QQQ": {"United States": 97.0, "Other": 3.0},
    "VTI": {"United States": 100.0},
    "VOO": {"United States": 100.0},
    "VEA": {
        "Japan": 20.5,
        "United Kingdom": 13.5,
        "France": 8.0,
        "Switzerland": 7.5,
        "Germany": 7.0,
        "Canada": 6.5,
        "Australia": 6.0,
        "Other": 31.0,
    },
    "VWO": {
        "China": 28.0,
        "India": 18.0,
        "Taiwan": 16.0,
        "Brazil": 6.0,
        "Saudi Arabia": 4.0,
        "South Korea": 3.5,
        "South Africa": 3.0,
        "Other": 21.5,
    },
    "IEMG": {
        "China": 25.0,
        "India": 17.0,
        "Taiwan": 17.5,
        "South Korea": 11.0,
        "Brazil": 5.5,
        "Other": 24.0,
    },
    "ACWI": {
        "United States": 62.0,
        "Japan": 5.5,
        "United Kingdom": 3.5,
        "China": 3.0,
        "France": 2.5,
        "Germany": 2.0,
        "Other": 21.5,
    },
    "ARKK": {"United States": 85.0, "Canada": 5.0, "Other": 10.0},
}


def _get_etf_meta(symbol: str) -> dict[str, str]:
    """Return category metadata for an ETF symbol."""
    return ETF_CATEGORIES.get(
        symbol,
        {
            "category": "Other",
            "region": "Unknown",
            "type": "Equity",
            "focus": "General",
        },
    )


def get_etf_list() -> list[dict[str, Any]]:
    """Return all ETFs with market data + metadata for the screener table."""
    all_data = fetch_batch(ETF_UNIVERSE, cached_only=True, include_stale=True)
    items: list[dict[str, Any]] = []
    for d in all_data:
        if not d:
            continue
        sym = d["symbol"]
        meta = _get_etf_meta(sym)
        items.append(
            {
                "symbol": sym,
                "name": d.get("name", sym),
                "price": d.get("price"),
                "market_cap": d.get("market_cap"),
                "dividend_yield": d.get("dividend_yield"),
                "expense_ratio": _EXPENSE_RATIOS.get(sym),
                "category": meta["category"],
                "region": meta["region"],
                "type": meta["type"],
                "focus": meta["focus"],
                "week52_high": d.get("week52_high"),
                "week52_low": d.get("week52_low"),
                "pct_from_high": d.get("pct_from_high"),
                "beta": d.get("beta"),
            }
        )
    return items


def get_etf_detail(symbol: str) -> Optional[dict[str, Any]]:
    """Return deep analysis for a single ETF."""
    symbol = symbol.upper()
    batch = fetch_batch([symbol], cached_only=True, include_stale=True)
    if not batch:
        return None
    d = batch[0]
    meta = _get_etf_meta(symbol)
    holdings = _TOP_HOLDINGS.get(symbol, [])
    sectors = _SECTOR_ALLOC.get(symbol, {})
    geography = _GEO_ALLOC.get(symbol, {})

    # Calculate concentration metrics
    top5_weight = sum(h["weight"] for h in holdings[:5]) if holdings else 0
    top10_weight = sum(h["weight"] for h in holdings[:10]) if holdings else 0

    return {
        "symbol": symbol,
        "name": d.get("name", symbol),
        "price": d.get("price"),
        "market_cap": d.get("market_cap"),
        "dividend_yield": d.get("dividend_yield"),
        "expense_ratio": _EXPENSE_RATIOS.get(symbol),
        "category": meta["category"],
        "region": meta["region"],
        "type": meta["type"],
        "focus": meta["focus"],
        "week52_high": d.get("week52_high"),
        "week52_low": d.get("week52_low"),
        "pct_from_high": d.get("pct_from_high"),
        "beta": d.get("beta"),
        "pe_ratio": d.get("pe_ratio"),
        "holdings": holdings,
        "top5_concentration": round(top5_weight, 1),
        "top10_concentration": round(top10_weight, 1),
        "sector_allocation": sectors,
        "geography_allocation": geography,
    }


def compare_etfs(symbols: list[str]) -> dict[str, Any]:
    """Compare 2–5 ETFs side by side."""
    symbols = [s.upper() for s in symbols[:5]]
    all_data = fetch_batch(symbols, cached_only=True, include_stale=True)
    data_map = {d["symbol"]: d for d in all_data if d}

    items: list[dict[str, Any]] = []
    for sym in symbols:
        d = data_map.get(sym)
        if not d:
            continue
        meta = _get_etf_meta(sym)
        items.append(
            {
                "symbol": sym,
                "name": d.get("name", sym),
                "price": d.get("price"),
                "market_cap": d.get("market_cap"),
                "dividend_yield": d.get("dividend_yield"),
                "expense_ratio": _EXPENSE_RATIOS.get(sym),
                "category": meta["category"],
                "region": meta["region"],
                "type": meta["type"],
                "beta": d.get("beta"),
                "pe_ratio": d.get("pe_ratio"),
                "week52_high": d.get("week52_high"),
                "week52_low": d.get("week52_low"),
                "pct_from_high": d.get("pct_from_high"),
                "top_holdings": _TOP_HOLDINGS.get(sym, [])[:5],
            }
        )
    return {"count": len(items), "items": items}


def compute_overlap(sym_a: str, sym_b: str) -> dict[str, Any]:
    """Compute holdings overlap between two ETFs."""
    sym_a = sym_a.upper()
    sym_b = sym_b.upper()
    h_a = _TOP_HOLDINGS.get(sym_a, [])
    h_b = _TOP_HOLDINGS.get(sym_b, [])

    set_a = {h["symbol"] for h in h_a}
    set_b = {h["symbol"] for h in h_b}
    common = set_a & set_b

    overlap_details: list[dict[str, Any]] = []
    for sym in sorted(common):
        wa = next((h["weight"] for h in h_a if h["symbol"] == sym), 0)
        wb = next((h["weight"] for h in h_b if h["symbol"] == sym), 0)
        name = next((h["name"] for h in h_a if h["symbol"] == sym), sym)
        overlap_details.append(
            {
                "symbol": sym,
                "name": name,
                "weight_a": wa,
                "weight_b": wb,
            }
        )

    total_a = len(set_a) or 1
    total_b = len(set_b) or 1
    pct_a = round(len(common) / total_a * 100, 1)
    pct_b = round(len(common) / total_b * 100, 1)

    return {
        "etf_a": sym_a,
        "etf_b": sym_b,
        "overlap_count": len(common),
        "total_a": len(set_a),
        "total_b": len(set_b),
        "overlap_pct_a": pct_a,
        "overlap_pct_b": pct_b,
        "common_holdings": overlap_details,
    }


def screen_etfs(
    *,
    etf_type: Optional[str] = None,
    region: Optional[str] = None,
    max_expense: Optional[float] = None,
    min_yield: Optional[float] = None,
    category: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Filter ETFs by criteria."""
    all_etfs = get_etf_list()
    results = []
    for etf in all_etfs:
        if etf_type and etf.get("type", "").lower() != etf_type.lower():
            continue
        if region and etf.get("region", "").lower() != region.lower():
            continue
        if max_expense is not None:
            er = etf.get("expense_ratio")
            if er is None or er > max_expense:
                continue
        if min_yield is not None:
            dy = etf.get("dividend_yield")
            if dy is None or dy < min_yield:
                continue
        if category and category.lower() not in etf.get("category", "").lower():
            continue
        results.append(etf)
    return results
