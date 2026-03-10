"""One-shot script to expand the data universe in market_data.py to 1,000+ symbols.

Run once then delete:
    python _expand_universe.py
"""

from __future__ import annotations
import re, textwrap, pathlib

TARGET = pathlib.Path(__file__).with_name("src") / "services" / "market_data.py"

# ── New stocks to add, organised by sector ───────────────────────────────
# Each value is (display_name,).  The key is the ticker symbol.
# Only symbols NOT already in STOCK_UNIVERSE should appear here.

NEW_STOCKS: dict[str, str] = {
    # ── Technology — S&P 500 / Russell 1000 expansion ────
    "INTU": "Intuit Inc",
    "KLAC": "KLA Corporation",
    "LRCX": "Lam Research Corporation",
    "NXPI": "NXP Semiconductors NV",
    "ON": "ON Semiconductor Corporation",
    "MPWR": "Monolithic Power Systems Inc",
    "ANSS": "Ansys Inc",
    "KEYS": "Keysight Technologies Inc",
    "ZBRA": "Zebra Technologies Corporation",
    "TER": "Teradyne Inc",
    "ENPH": "Enphase Energy Inc",
    "SMCI": "Super Micro Computer Inc",
    "CRWD": "CrowdStrike Holdings Inc",
    "DDOG": "Datadog Inc",
    "ZS": "Zscaler Inc",
    "SNOW": "Snowflake Inc",
    "NET": "Cloudflare Inc",
    "MDB": "MongoDB Inc",
    "PLTR": "Palantir Technologies Inc",
    "COIN": "Coinbase Global Inc",
    "ROKU": "Roku Inc",
    "TEAM": "Atlassian Corporation",
    "WDAY": "Workday Inc",
    "HUBS": "HubSpot Inc",
    "TTD": "The Trade Desk Inc",
    "SQ": "Block Inc",
    "RBLX": "Roblox Corporation",
    "U": "Unity Software Inc",
    "PATH": "UiPath Inc",
    "TWLO": "Twilio Inc",
    "OKTA": "Okta Inc",
    "VEEV": "Veeva Systems Inc",
    "TYL": "Tyler Technologies Inc",
    "MANH": "Manhattan Associates Inc",
    "GEN": "Gen Digital Inc",
    "FFIV": "F5 Inc",
    "JNPR": "Juniper Networks Inc",
    "AKAM": "Akamai Technologies Inc",
    "CDW": "CDW Corporation",
    "EPAM": "EPAM Systems Inc",
    "IT": "Gartner Inc",
    "BR": "Broadridge Financial Solutions Inc",
    "FSLR": "First Solar Inc",
    "ROP": "Roper Technologies Inc",
    "HPE": "Hewlett Packard Enterprise Co",
    "HPQ": "HP Inc",
    "DELL": "Dell Technologies Inc",
    "WDC": "Western Digital Corporation",
    "STX": "Seagate Technology Holdings",
    "NTAP": "NetApp Inc",
    "ANET": "Arista Networks Inc",
    "FICO": "Fair Isaac Corporation",
    "GDDY": "GoDaddy Inc",
    "PTC": "PTC Inc",
    "TRMB": "Trimble Inc",
    "APP": "AppLovin Corporation",
    "ADSK": "Autodesk Inc",
    "APH": "Amphenol Corporation",
    "ILMN": "Illumina Inc",
    "PSTG": "Pure Storage Inc",
    "NTNX": "Nutanix Inc",
    "ENTG": "Entegris Inc",
    "MSTR": "MicroStrategy Inc",
    "CIEN": "Ciena Corporation",
    "COHR": "Coherent Corp",
    "MKSI": "MKS Instruments Inc",
    "SWKS": "Skyworks Solutions Inc",
    "MCHP": "Microchip Technology Inc",
    "LSCC": "Lattice Semiconductor Corporation",
    "SMAR": "Smartsheet Inc",
    "CGNX": "Cognex Corporation",
    "TDY": "Teledyne Technologies Inc",
    "FTV": "Fortive Corporation",
    "VRSN": "VeriSign Inc",
    "OLED": "Universal Display Corporation",
    "DOCU": "DocuSign Inc",
    "ZM": "Zoom Video Communications Inc",
    "DT": "Dynatrace Inc",
    "GLOB": "Globant SA",
    "SSNC": "SS&C Technologies Holdings Inc",
    "BSY": "Bentley Systems Inc",
    "TENB": "Tenable Holdings Inc",
    "RPD": "Rapid7 Inc",
    "QLYS": "Qualys Inc",
    "FOUR": "Shift4 Payments Inc",
    "BILL": "BILL Holdings Inc",
    "S": "SentinelOne Inc",
    "IOT": "Samsara Inc",
    "ESTC": "Elastic NV",
    "GTLB": "GitLab Inc",
    "AFRM": "Affirm Holdings Inc",
    "HOOD": "Robinhood Markets Inc",
    "IONQ": "IonQ Inc",
    "ARM": "Arm Holdings plc",
    "CRDO": "Credo Technology Group Holding",
    "VRT": "Vertiv Holdings Co",
    "ALAB": "Astera Labs Inc",
    "ASAN": "Asana Inc",
    "NCNO": "nCino Inc",
    "AI": "C3.ai Inc",
    "UPST": "Upstart Holdings Inc",
    "WK": "Workiva Inc",
    "LOGI": "Logitech International SA",
    "PI": "Impinj Inc",
    "OTEX": "Open Text Corporation",
    "AMKR": "Amkor Technology Inc",
    "WOLF": "Wolfspeed Inc",
    "DIOD": "Diodes Incorporated",
    "CRUS": "Cirrus Logic Inc",
    "FORM": "FormFactor Inc",
    "RMBS": "Rambus Inc",
    "MTSI": "MACOM Technology Solutions",
    "ONTO": "Onto Innovation Inc",
    "FLEX": "Flex Ltd",
    "GWRE": "Guidewire Software Inc",
    "KD": "Kyndryl Holdings Inc",
    "PLAB": "Photronics Inc",
    "CAMT": "Camtek Ltd",
    # ── Financial Services — expansion ────────────────
    "PYPL": "PayPal Holdings Inc",
    "FIS": "Fidelity National Information Services",
    "FISV": "Fiserv Inc",
    "MCO": "Moody's Corporation",
    "AON": "Aon plc",
    "MMC": "Marsh & McLennan Companies Inc",
    "TRV": "Travelers Companies Inc",
    "AFL": "Aflac Incorporated",
    "MET": "MetLife Inc",
    "PRU": "Prudential Financial Inc",
    "AIG": "American International Group Inc",
    "ALL": "Allstate Corporation",
    "HIG": "Hartford Financial Services Group",
    "BK": "Bank of New York Mellon Corporation",
    "STT": "State Street Corporation",
    "NTRS": "Northern Trust Corporation",
    "USB": "U.S. Bancorp",
    "PNC": "PNC Financial Services Group Inc",
    "TFC": "Truist Financial Corporation",
    "FITB": "Fifth Third Bancorp",
    "RF": "Regions Financial Corporation",
    "KEY": "KeyCorp",
    "CFG": "Citizens Financial Group Inc",
    "HBAN": "Huntington Bancshares Inc",
    "MTB": "M&T Bank Corporation",
    "COF": "Capital One Financial Corporation",
    "DFS": "Discover Financial Services",
    "SYF": "Synchrony Financial",
    "NDAQ": "Nasdaq Inc",
    "MSCI": "MSCI Inc",
    "MKTX": "MarketAxess Holdings Inc",
    "CBOE": "Cboe Global Markets Inc",
    "TROW": "T. Rowe Price Group Inc",
    "BEN": "Franklin Resources Inc",
    "CINF": "Cincinnati Financial Corporation",
    "AJG": "Arthur J Gallagher & Co",
    "ACGL": "Arch Capital Group Ltd",
    "GL": "Globe Life Inc",
    "WRB": "W.R. Berkley Corporation",
    "FNF": "Fidelity National Financial Inc",
    "L": "Loews Corporation",
    "RE": "Everest Group Ltd",
    "RJF": "Raymond James Financial Inc",
    "LPLA": "LPL Financial Holdings Inc",
    "ALLY": "Ally Financial Inc",
    "SOFI": "SoFi Technologies Inc",
    "CMA": "Comerica Incorporated",
    "ZION": "Zions Bancorporation",
    "EWBC": "East West Bancorp Inc",
    "WAL": "Western Alliance Bancorporation",
    "IBKR": "Interactive Brokers Group Inc",
    "AIZ": "Assurant Inc",
    "FAF": "First American Financial Corporation",
    "ESNT": "Essent Group Ltd",
    "RNR": "RenaissanceRe Holdings Ltd",
    "AFG": "American Financial Group Inc",
    "KKR": "KKR & Co Inc",
    "APO": "Apollo Global Management Inc",
    "ARES": "Ares Management Corporation",
    "OWL": "Blue Owl Capital Inc",
    "VIRT": "Virtu Financial Inc",
    "KNSL": "Kinsale Capital Group Inc",
    "FHN": "First Horizon Corporation",
    "WBS": "Webster Financial Corporation",
    "PNFP": "Pinnacle Financial Partners Inc",
    "OZK": "Bank OZK",
    "SEIC": "SEI Investments Company",
    "HLI": "Houlihan Lokey Inc",
    "EVR": "Evercore Inc",
    "SF": "Stifel Financial Corp",
    # ── Healthcare — expansion ────────────────────────
    "CI": "Cigna Group",
    "ELV": "Elevance Health Inc",
    "CNC": "Centene Corporation",
    "HUM": "Humana Inc",
    "MCK": "McKesson Corporation",
    "CAH": "Cardinal Health Inc",
    "DXCM": "DexCom Inc",
    "IQV": "IQVIA Holdings Inc",
    "A": "Agilent Technologies Inc",
    "HOLX": "Hologic Inc",
    "BAX": "Baxter International Inc",
    "BDX": "Becton Dickinson and Company",
    "EW": "Edwards Lifesciences Corporation",
    "SYK": "Stryker Corporation",
    "BSX": "Boston Scientific Corporation",
    "HCA": "HCA Healthcare Inc",
    "IDXX": "IDEXX Laboratories Inc",
    "ALGN": "Align Technology Inc",
    "WAT": "Waters Corporation",
    "MTD": "Mettler-Toledo International Inc",
    "WST": "West Pharmaceutical Services Inc",
    "MRNA": "Moderna Inc",
    "BIIB": "Biogen Inc",
    "INCY": "Incyte Corporation",
    "HALO": "Halozyme Therapeutics Inc",
    "EXAS": "Exact Sciences Corporation",
    "CRL": "Charles River Laboratories International",
    "GEHC": "GE HealthCare Technologies Inc",
    "MOH": "Molina Healthcare Inc",
    "VTRS": "Viatris Inc",
    "XRAY": "DENTSPLY SIRONA Inc",
    "RVTY": "Revvity Inc",
    "BIO": "Bio-Rad Laboratories Inc",
    "TECH": "Bio-Techne Corporation",
    "HSIC": "Henry Schein Inc",
    "OGN": "Organon & Co",
    "PODD": "Insulet Corporation",
    "JAZZ": "Jazz Pharmaceuticals plc",
    "ALNY": "Alnylam Pharmaceuticals Inc",
    "NBIX": "Neurocrine Biosciences Inc",
    "SRPT": "Sarepta Therapeutics Inc",
    "BMRN": "BioMarin Pharmaceutical Inc",
    "ARGX": "argenx SE",
    "IRTC": "iRhythm Technologies Inc",
    "NTRA": "Natera Inc",
    "UTHR": "United Therapeutics Corporation",
    "INSM": "Insmed Incorporated",
    "LH": "Labcorp Holdings Inc",
    "DGX": "Quest Diagnostics Incorporated",
    "ENSG": "Ensign Group Inc",
    "MEDP": "Medpace Holdings Inc",
    "AVTR": "Avantor Inc",
    "RGEN": "Repligen Corporation",
    "AZTA": "Azenta Inc",
    "LNTH": "Lantheus Holdings Inc",
    "RVMD": "Revolution Medicines Inc",
    "CYTK": "Cytokinetics Incorporated",
    "ACHC": "Acadia Healthcare Company Inc",
    "CRSP": "CRISPR Therapeutics AG",
    "NTLA": "Intellia Therapeutics Inc",
    "STE": "STERIS plc",
    "MASI": "Masimo Corporation",
    "EXEL": "Exelixis Inc",
    "GKOS": "Glaukos Corporation",
    "GMED": "Globus Medical Inc",
    "DOCS": "Doximity Inc",
    "HIMS": "Hims & Hers Health Inc",
    # ── Industrials — expansion ───────────────────────
    "CTAS": "Cintas Corporation",
    "FAST": "Fastenal Company",
    "PCAR": "PACCAR Inc",
    "CMI": "Cummins Inc",
    "CSX": "CSX Corporation",
    "NSC": "Norfolk Southern Corporation",
    "GD": "General Dynamics Corporation",
    "NOC": "Northrop Grumman Corporation",
    "TXT": "Textron Inc",
    "LHX": "L3Harris Technologies Inc",
    "AXON": "Axon Enterprise Inc",
    "AME": "AMETEK Inc",
    "ROK": "Rockwell Automation Inc",
    "PH": "Parker-Hannifin Corporation",
    "IR": "Ingersoll Rand Inc",
    "DOV": "Dover Corporation",
    "GWW": "W.W. Grainger Inc",
    "ODFL": "Old Dominion Freight Line Inc",
    "XPO": "XPO Inc",
    "JBHT": "J.B. Hunt Transport Services Inc",
    "UBER": "Uber Technologies Inc",
    "DAL": "Delta Air Lines Inc",
    "UAL": "United Airlines Holdings Inc",
    "LUV": "Southwest Airlines Co",
    "CARR": "Carrier Global Corporation",
    "OTIS": "Otis Worldwide Corporation",
    "TT": "Trane Technologies plc",
    "VRSK": "Verisk Analytics Inc",
    "PAYC": "Paycom Software Inc",
    "PAYX": "Paychex Inc",
    "RSG": "Republic Services Inc",
    "WAB": "Westinghouse Air Brake Technologies",
    "PWR": "Quanta Services Inc",
    "EME": "EMCOR Group Inc",
    "SWK": "Stanley Black & Decker Inc",
    "LDOS": "Leidos Holdings Inc",
    "J": "Jacobs Solutions Inc",
    "HII": "HII (Huntington Ingalls Industries)",
    "GPN": "Global Payments Inc",
    "CPRT": "Copart Inc",
    "HUBB": "Hubbell Incorporated",
    "NDSN": "Nordson Corporation",
    "GNRC": "Generac Holdings Inc",
    "MAS": "Masco Corporation",
    "AOS": "A.O. Smith Corporation",
    "IEX": "IDEX Corporation",
    "ALLE": "Allegion plc",
    "LYFT": "Lyft Inc",
    "BLDR": "Builders FirstSource Inc",
    "URI": "United Rentals Inc",
    "TDG": "TransDigm Group Inc",
    "HEI": "HEICO Corporation",
    "BAH": "Booz Allen Hamilton Holding",
    "SAIA": "Saia Inc",
    "AGCO": "AGCO Corporation",
    "CNHI": "CNH Industrial NV",
    "OSK": "Oshkosh Corporation",
    "R": "Ryder System Inc",
    "CMC": "Commercial Metals Company",
    "ATI": "ATI Inc",
    "AIT": "Applied Industrial Technologies Inc",
    "MSA": "MSA Safety Incorporated",
    "SNA": "Snap-on Incorporated",
    "ITT": "ITT Inc",
    "GGG": "Graco Inc",
    "HWM": "Howmet Aerospace Inc",
    "XYL": "Xylem Inc",
    "MOD": "Modine Manufacturing Company",
    "TOST": "Toast Inc",
    "RXO": "RXO Inc",
    "FIX": "Comfort Systems USA Inc",
    "TNET": "TriNet Group Inc",
    "GEV": "GE Vernova Inc",
    "VLTO": "Veralto Corporation",
    "TREX": "Trex Company Inc",
    "DY": "Dycom Industries Inc",
    "TTEK": "Tetra Tech Inc",
    "EXPO": "Exponent Inc",
    "CLH": "Clean Harbors Inc",
    "WMS": "Advanced Drainage Systems Inc",
    "KBR": "KBR Inc",
    "FLR": "Fluor Corporation",
    "BWXT": "BWX Technologies Inc",
    "WSC": "WillScot Holdings Inc",
    "WDFC": "WD-40 Company",
    "WSO": "Watsco Inc",
    "AYI": "Acuity Brands Inc",
    "MLI": "Mueller Industries Inc",
    "POWL": "Powell Industries Inc",
    "HXL": "Hexcel Corporation",
    "RKLB": "Rocket Lab USA Inc",
    # ── Consumer Cyclical — expansion ─────────────────
    "DHI": "D.R. Horton Inc",
    "LEN": "Lennar Corporation",
    "PHM": "PulteGroup Inc",
    "NVR": "NVR Inc",
    "KMX": "CarMax Inc",
    "BBY": "Best Buy Co Inc",
    "EBAY": "eBay Inc",
    "ETSY": "Etsy Inc",
    "ROST": "Ross Stores Inc",
    "DECK": "Deckers Outdoor Corporation",
    "GRMN": "Garmin Ltd",
    "POOL": "Pool Corporation",
    "DRI": "Darden Restaurants Inc",
    "YUM": "Yum! Brands Inc",
    "DPZ": "Domino's Pizza Inc",
    "WYNN": "Wynn Resorts Limited",
    "LVS": "Las Vegas Sands Corp",
    "MGM": "MGM Resorts International",
    "CZR": "Caesars Entertainment Inc",
    "MAR": "Marriott International Inc",
    "HLT": "Hilton Worldwide Holdings Inc",
    "EXPE": "Expedia Group Inc",
    "APTV": "Aptiv PLC",
    "BWA": "BorgWarner Inc",
    "AZO": "AutoZone Inc",
    "GPC": "Genuine Parts Company",
    "TSCO": "Tractor Supply Company",
    "ULTA": "Ulta Beauty Inc",
    "TPR": "Tapestry Inc",
    "RL": "Ralph Lauren Corporation",
    "PVH": "PVH Corp",
    "HAS": "Hasbro Inc",
    "MAT": "Mattel Inc",
    "LKQ": "LKQ Corporation",
    "W": "Wayfair Inc",
    "DKNG": "DraftKings Inc",
    "DASH": "DoorDash Inc",
    "PENN": "PENN Entertainment Inc",
    "TOL": "Toll Brothers Inc",
    "LCID": "Lucid Group Inc",
    "RCL": "Royal Caribbean Cruises Ltd",
    "CCL": "Carnival Corporation",
    "NCLH": "Norwegian Cruise Line Holdings",
    "CROX": "Crocs Inc",
    "FIVE": "Five Below Inc",
    "OLLI": "Ollie's Bargain Outlet Holdings",
    "BROS": "Dutch Bros Inc",
    "WING": "Wingstop Inc",
    "TXRH": "Texas Roadhouse Inc",
    "CAVA": "CAVA Group Inc",
    "SFM": "Sprouts Farmers Market Inc",
    "ANF": "Abercrombie & Fitch Co",
    "SKX": "Skechers USA Inc",
    "TGT": "Target Corporation",
    "DLTR": "Dollar Tree Inc",
    "DG": "Dollar General Corporation",
    "BURL": "Burlington Stores Inc",
    "DKS": "Dick's Sporting Goods Inc",
    "CPNG": "Coupang Inc",
    "MELI": "MercadoLibre Inc",
    "WSM": "Williams-Sonoma Inc",
    "RH": "RH (Restoration Hardware)",
    "CHDN": "Churchill Downs Inc",
    "TPX": "Tempur Sealy International Inc",
    "ONON": "On Holding AG",
    "YETI": "YETI Holdings Inc",
    "SHAK": "Shake Shack Inc",
    "EAT": "Brinker International Inc",
    "AEO": "American Eagle Outfitters Inc",
    "LEVI": "Levi Strauss & Co",
    "BOOT": "Boot Barn Holdings Inc",
    "ASO": "Academy Sports and Outdoors Inc",
    "COLM": "Columbia Sportswear Company",
    "FL": "Foot Locker Inc",
    "SN": "SharkNinja Inc",
    "BIRK": "Birkenstock Holding plc",
    "DUOL": "Duolingo Inc",
    "CART": "Maplebear Inc (Instacart)",
    "TKO": "TKO Group Holdings Inc",
    # ── Consumer Defensive — expansion ────────────────
    "STZ": "Constellation Brands Inc",
    "MNST": "Monster Beverage Corporation",
    "KDP": "Keurig Dr Pepper Inc",
    "SYY": "Sysco Corporation",
    "KR": "Kroger Co",
    "ADM": "Archer-Daniels-Midland Company",
    "TSN": "Tyson Foods Inc",
    "HRL": "Hormel Foods Corporation",
    "CAG": "Conagra Brands Inc",
    "CPB": "Campbell Soup Company",
    "MKC": "McCormick & Company Inc",
    "CLX": "Clorox Company",
    "CHD": "Church & Dwight Co Inc",
    "WBA": "Walgreens Boots Alliance Inc",
    "EL": "Estee Lauder Companies Inc",
    "KVUE": "Kenvue Inc",
    "COR": "Cencora Inc",
    "LW": "Lamb Weston Holdings Inc",
    "CASY": "Casey's General Stores Inc",
    "TAP": "Molson Coors Beverage Company",
    "BG": "Bunge Global SA",
    "SAM": "Boston Beer Company Inc",
    "USFD": "US Foods Holding Corp",
    "CELH": "Celsius Holdings Inc",
    "POST": "Post Holdings Inc",
    "FLO": "Flowers Foods Inc",
    "INGR": "Ingredion Incorporated",
    "DAR": "Darling Ingredients Inc",
    "BJ": "BJ's Wholesale Club Holdings Inc",
    "K": "Kellanova",
    # ── Energy — expansion ────────────────────────────
    "LNG": "Cheniere Energy Inc",
    "EQT": "EQT Corporation",
    "CTRA": "Coterra Energy Inc",
    "APA": "APA Corporation",
    "HES": "Hess Corporation",
    "MRO": "Marathon Oil Corporation",
    "TRGP": "Targa Resources Corp",
    "BKR": "Baker Hughes Company",
    "DINO": "HF Sinclair Corporation",
    "AM": "Antero Midstream Corporation",
    "OVV": "Ovintiv Inc",
    "AR": "Antero Resources Corporation",
    "RRC": "Range Resources Corporation",
    "DTM": "DT Midstream Inc",
    "TPL": "Texas Pacific Land Corporation",
    "CNX": "CNX Resources Corporation",
    "SWN": "Southwestern Energy Company",
    "HP": "Helmerich & Payne Inc",
    "PTEN": "Patterson-UTI Energy Inc",
    "CHRD": "Chord Energy Corporation",
    "PR": "Permian Resources Corporation",
    "LBRT": "Liberty Energy Inc",
    "FTI": "TechnipFMC plc",
    "WFRD": "Weatherford International plc",
    "WHD": "Cactus Inc",
    # ── Communication Services — expansion ────────────
    "WBD": "Warner Bros. Discovery Inc",
    "FOXA": "Fox Corporation",
    "LYV": "Live Nation Entertainment Inc",
    "OMC": "Omnicom Group Inc",
    "IPG": "Interpublic Group of Companies Inc",
    "PINS": "Pinterest Inc",
    "SNAP": "Snap Inc",
    "PARA": "Paramount Global",
    "ZI": "ZoomInfo Technologies Inc",
    "IAC": "IAC Inc",
    "SIRI": "Sirius XM Holdings Inc",
    "NXST": "Nexstar Media Group Inc",
    # ── Utilities — expansion ─────────────────────────
    "AWK": "American Water Works Company Inc",
    "CMS": "CMS Energy Corporation",
    "CNP": "CenterPoint Energy Inc",
    "DTE": "DTE Energy Company",
    "ES": "Eversource Energy",
    "FE": "FirstEnergy Corp",
    "PEG": "Public Service Enterprise Group Inc",
    "PPL": "PPL Corporation",
    "AES": "AES Corporation",
    "EIX": "Edison International",
    "ETR": "Entergy Corporation",
    "LNT": "Alliant Energy Corporation",
    "NI": "NiSource Inc",
    "NRG": "NRG Energy Inc",
    "PNW": "Pinnacle West Capital Corporation",
    "VST": "Vistra Corp",
    "EVRG": "Evergy Inc",
    "ATO": "Atmos Energy Corporation",
    "CEG": "Constellation Energy Corporation",
    "PCG": "PG&E Corporation",
    "OTTR": "Otter Tail Corporation",
    "MDU": "MDU Resources Group Inc",
    # ── Real Estate — expansion ───────────────────────
    "AVB": "AvalonBay Communities Inc",
    "EQR": "Equity Residential",
    "MAA": "Mid-America Apartment Communities",
    "UDR": "UDR Inc",
    "ESS": "Essex Property Trust Inc",
    "IRM": "Iron Mountain Inc",
    "VICI": "VICI Properties Inc",
    "INVH": "Invitation Homes Inc",
    "SBAC": "SBA Communications Corporation",
    "KIM": "Kimco Realty Corporation",
    "REG": "Regency Centers Corporation",
    "BXP": "BXP Inc (Boston Properties)",
    "VTR": "Ventas Inc",
    "ARE": "Alexandria Real Estate Equities Inc",
    "HST": "Host Hotels & Resorts Inc",
    "CPT": "Camden Property Trust",
    "LAMR": "Lamar Advertising Company",
    "SLG": "SL Green Realty Corp",
    "CUZ": "Cousins Properties Inc",
    "OHI": "Omega Healthcare Investors Inc",
    "STAG": "STAG Industrial Inc",
    "CUBE": "CubeSmart",
    "NNN": "NNN REIT Inc",
    "EPRT": "Essential Properties Realty Trust",
    "ADC": "Agree Realty Corporation",
    "GLPI": "Gaming and Leisure Properties Inc",
    "WPC": "W.P. Carey Inc",
    "ELS": "Equity LifeStyle Properties Inc",
    "SUI": "Sun Communities Inc",
    "AMH": "American Homes 4 Rent",
    "REXR": "Rexford Industrial Realty Inc",
    "FR": "First Industrial Realty Trust Inc",
    "RHP": "Ryman Hospitality Properties Inc",
    "APLE": "Apple Hospitality REIT Inc",
    "MAC": "Macerich Company",
    # ── Basic Materials — expansion ───────────────────
    "CF": "CF Industries Holdings Inc",
    "MOS": "Mosaic Company",
    "ALB": "Albemarle Corporation",
    "EMN": "Eastman Chemical Company",
    "CE": "Celanese Corporation",
    "PPG": "PPG Industries Inc",
    "RPM": "RPM International Inc",
    "VMC": "Vulcan Materials Company",
    "MLM": "Martin Marietta Materials Inc",
    "STLD": "Steel Dynamics Inc",
    "CLF": "Cleveland-Cliffs Inc",
    "RS": "Reliance Inc",
    "X": "United States Steel Corporation",
    "PKG": "Packaging Corporation of America",
    "IP": "International Paper Company",
    "BLL": "Ball Corporation",
    "AVY": "Avery Dennison Corporation",
    "CTVA": "Corteva Inc",
    "FMC": "FMC Corporation",
    "IFF": "International Flavors & Fragrances",
    "WRK": "WestRock Company",
    "SEE": "Sealed Air Corporation",
    "CCJ": "Cameco Corporation",
    "TECK": "Teck Resources Limited",
    "BHP": "BHP Group Limited",
    "RIO": "Rio Tinto Group",
    "GOLD": "Barrick Gold Corporation",
    "AEM": "Agnico Eagle Mines Limited",
    "WPM": "Wheaton Precious Metals Corp",
    "OC": "Owens Corning",
    "AXTA": "Axalta Coating Systems Ltd",
    "BECN": "Beacon Roofing Supply Inc",
    "HCC": "Warrior Met Coal Inc",
    # ── Popular Growth & Momentum ─────────────────────
    "MARA": "Marathon Digital Holdings Inc",
    "RIOT": "Riot Platforms Inc",
    "CLSK": "CleanSpark Inc",
    "ACHR": "Archer Aviation Inc",
    "JOBY": "Joby Aviation Inc",
    "SOLV": "Solventum Corporation",
    "SPSC": "SPS Commerce Inc",
    "LMND": "Lemonade Inc",
    "MGNI": "Magnite Inc",
    "VERX": "Vertex Inc",
    "BLD": "TopBuild Corp",
    "RELY": "Remitly Global Inc",
}

# ── New ETFs to add ──────────────────────────────────────────────────────

NEW_ETFS: dict[str, str] = {
    "XBI": "SPDR S&P Biotech ETF",
    "IBB": "iShares Biotechnology ETF",
    "VTV": "Vanguard Value ETF",
    "VUG": "Vanguard Growth ETF",
    "IGSB": "iShares 1-5 Year Investment Grade Corporate Bond ETF",
    "GOVT": "iShares U.S. Treasury Bond ETF",
    "MTUM": "iShares MSCI USA Momentum Factor ETF",
    "QUAL": "iShares MSCI USA Quality Factor ETF",
    "ARKG": "ARK Genomic Revolution ETF",
    "CIBR": "First Trust NASDAQ Cybersecurity ETF",
    "LIT": "Global X Lithium & Battery Tech ETF",
    "BOTZ": "Global X Robotics & Artificial Intelligence ETF",
    "JETS": "U.S. Global Jets ETF",
    "BITO": "ProShares Bitcoin Strategy ETF",
    "XHB": "SPDR S&P Homebuilders ETF",
    "ITB": "iShares U.S. Home Construction ETF",
    "XRT": "SPDR S&P Retail ETF",
    "KRE": "SPDR S&P Regional Banking ETF",
    "XME": "SPDR S&P Metals and Mining ETF",
    "WCLD": "WisdomTree Cloud Computing Fund",
    "VGT": "Vanguard Information Technology ETF",
    "COWZ": "Pacer US Cash Cows 100 ETF",
    "QQQM": "Invesco NASDAQ 100 ETF",
    "IJR": "iShares Core S&P Small-Cap ETF",
    "IJH": "iShares Core S&P Mid-Cap ETF",
    "MDY": "SPDR S&P MidCap 400 ETF Trust",
    "IEFA": "iShares Core MSCI EAFE ETF",
    "ACWI": "iShares MSCI ACWI ETF",
    "EEM": "iShares MSCI Emerging Markets ETF",
    "SGOV": "iShares 0-3 Month Treasury Bond ETF",
    "SHY": "iShares 1-3 Year Treasury Bond ETF",
    "IEF": "iShares 7-10 Year Treasury Bond ETF",
    "PFF": "iShares Preferred and Income Securities ETF",
    "IYR": "iShares U.S. Real Estate ETF",
    "SCHG": "Schwab U.S. Large-Cap Growth ETF",
    "VBR": "Vanguard Small-Cap Value ETF",
}

# ── New international region assignments ─────────────────────────────────
# Symbols that should NOT default to "US" in _REGION_MAP.

NEW_INTL: dict[str, list[str]] = {
    "South Korea": ["CPNG"],
    "Brazil": ["MELI"],                  # Argentine-founded, LatAm HQ
    "Australia": ["BHP"],
    "Europe": ["ARGX", "ARM", "BIRK", "ONON", "RIO", "LOGI", "GLOB", "ESTC", "CRSP"],
    "Canada": ["TECK", "CCJ", "OVV", "WPM", "AEM"],
    "Israel": ["CAMT"],
}


# ──────────────────────────────────────────────────────────────────────────
# Apply changes to market_data.py
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    src = TARGET.read_text(encoding="utf-8")

    # --- 0. Dedup: remove any symbols that already exist ----------------------
    # Parse existing STOCK_UNIVERSE
    m_stock = re.search(r"STOCK_UNIVERSE\s*=\s*\[", src)
    assert m_stock, "Could not find STOCK_UNIVERSE"
    # Find the matching ] for STOCK_UNIVERSE
    bracket_start = m_stock.end() - 1
    depth = 0
    stock_end = bracket_start
    for i in range(bracket_start, len(src)):
        if src[i] == '[':
            depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0:
                stock_end = i
                break
    existing_stock_block = src[bracket_start:stock_end + 1]
    existing_stocks = set(re.findall(r'"([^"]+)"', existing_stock_block))
    print(f"Existing STOCK_UNIVERSE: {len(existing_stocks)} symbols")

    # Parse existing ETF_UNIVERSE
    m_etf = re.search(r"ETF_UNIVERSE\s*=\s*\[", src)
    assert m_etf, "Could not find ETF_UNIVERSE"
    bracket_start_etf = m_etf.end() - 1
    depth = 0
    etf_end = bracket_start_etf
    for i in range(bracket_start_etf, len(src)):
        if src[i] == '[':
            depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0:
                etf_end = i
                break
    existing_etf_block = src[bracket_start_etf:etf_end + 1]
    existing_etfs = set(re.findall(r'"([^"]+)"', existing_etf_block))
    print(f"Existing ETF_UNIVERSE: {len(existing_etfs)} symbols")

    new_stocks = {k: v for k, v in NEW_STOCKS.items() if k not in existing_stocks}
    new_etfs = {k: v for k, v in NEW_ETFS.items() if k not in existing_etfs}
    print(f"New stocks to add: {len(new_stocks)}")
    print(f"New ETFs to add: {len(new_etfs)}")

    # --- 1. Update CACHE_MAX_ENTRIES ------------------------------------------
    src = re.sub(
        r"CACHE_MAX_ENTRIES\s*=\s*\d+",
        "CACHE_MAX_ENTRIES = 2500",
        src,
        count=1,
    )

    # --- 2. Insert new stocks at end of STOCK_UNIVERSE ------------------------
    # Find the closing ] of STOCK_UNIVERSE by matching brackets
    m = re.search(r"STOCK_UNIVERSE\s*=\s*\[", src)
    assert m
    depth = 0
    for i in range(m.end() - 1, len(src)):
        if src[i] == '[':
            depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0:
                stock_close = i
                break

    # Build insertion block
    lines = ["\n    # ── S&P 500 + Russell 1000 Expansion (auto-generated) ──"]
    # Group by comment prefix embedded in NEW_STOCKS ordering
    for sym, name in new_stocks.items():
        lines.append(f'    "{sym}",')
    insertion_stocks = "\n".join(lines) + "\n"
    src = src[:stock_close] + insertion_stocks + src[stock_close:]

    # --- 3. Insert new ETFs at end of ETF_UNIVERSE ----------------------------
    m = re.search(r"ETF_UNIVERSE\s*=\s*\[", src)
    assert m
    depth = 0
    for i in range(m.end() - 1, len(src)):
        if src[i] == '[':
            depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0:
                etf_close = i
                break

    lines = ["\n    # ── Additional ETFs (expansion) ──"]
    for sym, name in new_etfs.items():
        lines.append(f'    "{sym}",')
    insertion_etfs = "\n".join(lines) + "\n"
    src = src[:etf_close] + insertion_etfs + src[etf_close:]

    # --- 4. Insert new KNOWN_NAMES entries ------------------------------------
    # Find the closing } of KNOWN_NAMES
    m = re.search(r"KNOWN_NAMES:\s*dict\[str,\s*str\]\s*=\s*\{", src)
    assert m, "Could not find KNOWN_NAMES"
    depth = 0
    for i in range(m.end() - 1, len(src)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                names_close = i
                break

    all_new = {**new_stocks, **new_etfs}
    lines = ["\n    # ── Expansion names (auto-generated) ──"]
    for sym, name in all_new.items():
        lines.append(f'    "{sym}": "{name}",')
    insertion_names = "\n".join(lines) + "\n"
    src = src[:names_close] + insertion_names + src[names_close:]

    # --- 5. Update _INTL region map for new international stocks --------------
    for region, syms in NEW_INTL.items():
        # Find the region set in _INTL and add symbols
        # Pattern: "Region": {"SYM1", "SYM2", ...}
        pattern = re.escape(f'"{region}"') + r":\s*\{"
        m = re.search(pattern, src)
        if m:
            # Find the closing } of this set
            depth = 0
            for i in range(m.end() - 1, len(src)):
                if src[i] == '{':
                    depth += 1
                elif src[i] == '}':
                    depth -= 1
                    if depth == 0:
                        set_close = i
                        break
            # Add new symbols before closing }
            new_entries = ", ".join(f'"{s}"' for s in syms)
            src = src[:set_close] + ", " + new_entries + src[set_close:]
        else:
            print(f"WARNING: Region '{region}' not found in _INTL, skipping")

    # --- 6. Write back -------------------------------------------------------
    TARGET.write_text(src, encoding="utf-8")

    # --- 7. Final count -------------------------------------------------------
    src2 = TARGET.read_text(encoding="utf-8")
    # Re-parse to count
    m = re.search(r"ALL_UNIVERSE\s*=\s*STOCK_UNIVERSE\s*\+\s*ETF_UNIVERSE", src2)
    # Count items in STOCK_UNIVERSE
    m_s = re.search(r"STOCK_UNIVERSE\s*=\s*\[", src2)
    depth = 0
    for i in range(m_s.end() - 1, len(src2)):
        if src2[i] == '[': depth += 1
        elif src2[i] == ']':
            depth -= 1
            if depth == 0:
                block = src2[m_s.end() - 1:i + 1]
                break
    stock_count = len(re.findall(r'"[^"]+"', block))

    m_e = re.search(r"ETF_UNIVERSE\s*=\s*\[", src2)
    depth = 0
    for i in range(m_e.end() - 1, len(src2)):
        if src2[i] == '[': depth += 1
        elif src2[i] == ']':
            depth -= 1
            if depth == 0:
                block = src2[m_e.end() - 1:i + 1]
                break
    etf_count = len(re.findall(r'"[^"]+"', block))

    print(f"\n✅ Done!")
    print(f"   STOCK_UNIVERSE: {stock_count} symbols")
    print(f"   ETF_UNIVERSE:   {etf_count} symbols")
    print(f"   ALL_UNIVERSE:   {stock_count + etf_count} symbols")
    print(f"   CACHE_MAX_ENTRIES: 2500")


if __name__ == "__main__":
    main()
