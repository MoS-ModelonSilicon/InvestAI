"""Second pass: add ~80 more symbols to push past 1,000 and fix region map."""
from __future__ import annotations
import re, pathlib

TARGET = pathlib.Path(__file__).with_name("src") / "services" / "market_data.py"

# Additional stocks to push past 1,000 total symbols
MORE_STOCKS: dict[str, str] = {
    # More Technology
    "APPF": "AppFolio Inc",
    "PCOR": "Procore Technologies Inc",
    "CFLT": "Confluent Inc",
    "ALTR": "Altair Engineering Inc",
    "VRNS": "Varonis Systems Inc",
    "QTWO": "Q2 Holdings Inc",
    # More Financial Services
    "CADE": "Cadence Bank",
    "FNB": "FNB Corporation",
    "PIPR": "Piper Sandler Companies",
    "PJT": "PJT Partners Inc",
    # More Healthcare
    "TGTX": "TG Therapeutics Inc",
    "APLS": "Apellis Pharmaceuticals Inc",
    "VKTX": "Viking Therapeutics Inc",
    "PCVX": "Vaxcyte Inc",
    "BEAM": "Beam Therapeutics Inc",
    "PRCT": "PROCEPT BioRobotics Corporation",
    "NUVB": "Nuvation Bio Inc",
    # More Industrials
    "AAON": "AAON Inc",
    "SITE": "SiteOne Landscape Supply Inc",
    "AZEK": "AZEK Company Inc",
    "MTZ": "MasTec Inc",
    "STRL": "Sterling Infrastructure Inc",
    "RBC": "RBC Bearings Inc",
    "TTC": "Toro Company",
    "WEX": "WEX Inc",
    "ACM": "AECOM",
    # More Consumer Cyclical
    "JACK": "Jack in the Box Inc",
    "CAKE": "Cheesecake Factory Inc",
    "TRIP": "TripAdvisor Inc",
    "MMYT": "MakeMyTrip Limited",
    # More Consumer Defensive
    "SMPL": "Simply Good Foods Company",
    "LANC": "Lancaster Colony Corporation",
    "FDP": "Fresh Del Monte Produce Inc",
    # More Energy
    "SM": "SM Energy Company",
    "NOG": "Northern Oil and Gas Inc",
    "MTDR": "Matador Resources Company",
    "VNOM": "Viper Energy Inc",
    # More Communication
    "CARG": "CarGurus Inc",
    "YELP": "Yelp Inc",
    # More Utilities
    "SJW": "SJW Group",
    "WTRG": "Essential Utilities Inc",
    "CWT": "California Water Service Group",
    # More Real Estate
    "NNN": "NNN REIT Inc",  # might already exist, dedup will catch
    "AIRC": "Apartment Income REIT Corp",
    # More Basic Materials
    "RGLD": "Royal Gold Inc",
    "SCCO": "Southern Copper Corporation",
    "ATKR": "Atkore Inc",
    "OI": "O-I Glass Inc",
    "SON": "Sonoco Products Company",
    "GEF": "Greif Inc",
    "AMCR": "Amcor plc",
    # More Popular / High-visibility
    "OPEN": "Opendoor Technologies Inc",
    "MNDY": "monday.com Ltd",  # might already exist
    "AMBA": "Ambarella Inc",
    "DSGX": "Descartes Systems Group Inc",
    "SLAB": "Silicon Laboratories Inc",
    "NOVT": "Novanta Inc",
    "POWI": "Power Integrations Inc",
    "CALX": "Calix Inc",
    "JAMF": "Jamf Holding Corp",
    "TASK": "TaskUs Inc",
    "PUBM": "PubMatic Inc",
    "XPEL": "XPEL Inc",
    "CEIX": "CONSOL Energy Inc",
}

MORE_ETFS: dict[str, str] = {
    "SPLG": "SPDR Portfolio S&P 500 ETF",
    "SPTM": "SPDR Portfolio S&P 1500 Composite Stock Market ETF",
    "SPMD": "SPDR Portfolio S&P 400 Mid Cap ETF",
    "SPSM": "SPDR Portfolio S&P 600 Small Cap ETF",
    "VXF": "Vanguard Extended Market ETF",
    "ACWX": "iShares MSCI ACWI ex US ETF",
    "SHV": "iShares Short Treasury Bond ETF",
    "MGK": "Vanguard Mega Cap Growth ETF",
    "HACK": "ETFMG Prime Cyber Security ETF",
    "ROBO": "Robo Global Robotics and Automation Index ETF",
}


def main() -> None:
    src = TARGET.read_text(encoding="utf-8")

    # Parse existing symbols
    m_stock = re.search(r"STOCK_UNIVERSE\s*=\s*\[", src)
    depth, stock_end = 0, 0
    for i in range(m_stock.end() - 1, len(src)):
        if src[i] == '[': depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0: stock_end = i; break
    existing_stocks = set(re.findall(r'"([^"]+)"', src[m_stock.end()-1:stock_end+1]))

    m_etf = re.search(r"ETF_UNIVERSE\s*=\s*\[", src)
    depth, etf_end = 0, 0
    for i in range(m_etf.end() - 1, len(src)):
        if src[i] == '[': depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0: etf_end = i; break
    existing_etfs = set(re.findall(r'"([^"]+)"', src[m_etf.end()-1:etf_end+1]))

    new_stocks = {k: v for k, v in MORE_STOCKS.items() if k not in existing_stocks}
    new_etfs = {k: v for k, v in MORE_ETFS.items() if k not in existing_etfs}
    print(f"Adding {len(new_stocks)} more stocks and {len(new_etfs)} more ETFs")

    # Insert stocks
    m = re.search(r"STOCK_UNIVERSE\s*=\s*\[", src)
    depth = 0
    for i in range(m.end()-1, len(src)):
        if src[i] == '[': depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0: stock_close = i; break
    lines = ["\n    # ── Second expansion pass ──"]
    for sym in new_stocks:
        lines.append(f'    "{sym}",')
    src = src[:stock_close] + "\n".join(lines) + "\n" + src[stock_close:]

    # Insert ETFs
    m = re.search(r"ETF_UNIVERSE\s*=\s*\[", src)
    depth = 0
    for i in range(m.end()-1, len(src)):
        if src[i] == '[': depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0: etf_close = i; break
    lines = ["\n    # ── More ETFs (second pass) ──"]
    for sym in new_etfs:
        lines.append(f'    "{sym}",')
    src = src[:etf_close] + "\n".join(lines) + "\n" + src[etf_close:]

    # Insert KNOWN_NAMES
    m = re.search(r"KNOWN_NAMES:\s*dict\[str,\s*str\]\s*=\s*\{", src)
    depth = 0
    for i in range(m.end()-1, len(src)):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: names_close = i; break
    all_new = {**new_stocks, **new_etfs}
    lines = ["\n    # ── Second expansion names ──"]
    for sym, name in all_new.items():
        lines.append(f'    "{sym}": "{name}",')
    src = src[:names_close] + "\n".join(lines) + "\n" + src[names_close:]

    # Fix _INTL: add "South Korea" and "Australia" entries
    # Find the _INTL dict and add new region entries before its closing }
    m_intl = re.search(r"_INTL\s*=\s*\{", src)
    if m_intl:
        depth = 0
        for i in range(m_intl.end()-1, len(src)):
            if src[i] == '{': depth += 1
            elif src[i] == '}':
                depth -= 1
                if depth == 0: intl_close = i; break
        # Check if these regions already exist
        intl_block = src[m_intl.start():intl_close+1]
        additions = []
        if '"South Korea"' not in intl_block:
            additions.append('    "South Korea": {"CPNG"},')
        if '"Australia"' not in intl_block:
            additions.append('    "Australia": {"BHP"},')
        if additions:
            insert_text = "\n" + "\n".join(additions) + "\n"
            src = src[:intl_close] + insert_text + src[intl_close:]

    TARGET.write_text(src, encoding="utf-8")

    # Re-count
    src2 = TARGET.read_text(encoding="utf-8")
    m_s = re.search(r"STOCK_UNIVERSE\s*=\s*\[", src2)
    depth = 0
    for i in range(m_s.end()-1, len(src2)):
        if src2[i] == '[': depth += 1
        elif src2[i] == ']':
            depth -= 1
            if depth == 0: block = src2[m_s.end()-1:i+1]; break
    stock_count = len(re.findall(r'"[^"]+"', block))

    m_e = re.search(r"ETF_UNIVERSE\s*=\s*\[", src2)
    depth = 0
    for i in range(m_e.end()-1, len(src2)):
        if src2[i] == '[': depth += 1
        elif src2[i] == ']':
            depth -= 1
            if depth == 0: block = src2[m_e.end()-1:i+1]; break
    etf_count = len(re.findall(r'"[^"]+"', block))

    print(f"\n✅ Done!")
    print(f"   STOCK_UNIVERSE: {stock_count} symbols")
    print(f"   ETF_UNIVERSE:   {etf_count} symbols")
    print(f"   ALL_UNIVERSE:   {stock_count + etf_count} symbols")


if __name__ == "__main__":
    main()
