"""
PULSE v2 - Sector & Promoter-Group Map
Powers the Action Center: sector concentration, cluster risk (e.g. Adani complex),
and diversification truth-telling.
"""

SECTOR = {
    # Defence & Aerospace
    "BDL": "Defence", "BEL": "Defence", "HAL": "Defence", "ASTRAMICRO": "Defence",
    "MTARTECH": "Defence", "PARAS": "Defence", "AZAD": "Defence", "GRSE": "Defence",
    "MAZDOCK": "Defence", "ROSSTECH": "Defence",
    # Banks - PSU
    "SBIN": "PSU Banks", "BANKBARODA": "PSU Banks", "MAHABANK": "PSU Banks",
    "PNB": "PSU Banks", "UNIONBANK": "PSU Banks",
    # Banks - Private
    "HDFCBANK": "Private Banks", "ICICIBANK": "Private Banks", "AXISBANK": "Private Banks",
    "FEDERALBNK": "Private Banks", "BANDHANBNK": "Private Banks", "CUB": "Private Banks",
    # Finance / Markets
    "MUTHOOTFIN": "Finance", "MASFIN": "Finance", "FIVESTAR": "Finance",
    "JIOFIN": "Finance", "PFC": "Finance", "NAM-INDIA": "Finance", "CRAMC": "Finance",
    "MCX": "Finance", "CDSL": "Finance", "KFINTECH": "Finance", "NIVABUPA": "Finance",
    "IREDA": "Finance",
    # Adani infra trio handled by GROUP too
    "ATGL": "Gas & Utilities", "ADANIPORTS": "Ports & Logistics",
    "ADANIPOWER": "Power", "ADANIENSOL": "Power",
    # IT / Tech / EMS
    "INFY": "IT Services", "WIPRO": "IT Services", "HCLTECH": "IT Services",
    "PERSISTENT": "IT Services", "BSOFT": "IT Services", "TATAELXSI": "IT Services",
    "AFFLE": "IT Services", "SYSTANGO": "IT Services", "AXISCADES": "IT Services",
    "NETWEB": "Electronics/EMS", "KAYNES": "Electronics/EMS", "SYRMA": "Electronics/EMS",
    "EBGNG": "Electronics/EMS", "PGEL": "Electronics/EMS",
    # Power & Renewables
    "NTPC": "Power", "TATAPOWER": "Power", "JSWENERGY": "Power", "NLCINDIA": "Power",
    "GIPCL": "Power", "KPIGREEN": "Renewables", "PREMIERENE": "Renewables",
    "WAAREEENER": "Renewables", "EMMVEE": "Renewables", "UTLSOLAR": "Renewables",
    "NAVA": "Power",
    # Oil & Gas
    "IOC": "Oil & Gas", "GAIL": "Gas & Utilities", "PETRONET": "Gas & Utilities",
    "SOTL": "Oil & Gas",
    # Metals & Mining
    "NATIONALUM": "Metals & Mining", "HINDCOPPER": "Metals & Mining",
    "HINDZINC": "Metals & Mining", "NMDC": "Metals & Mining", "SAIL": "Metals & Mining",
    "TATASTEEL": "Metals & Mining", "MOIL": "Metals & Mining", "SANDUMA": "Metals & Mining",
    "COALINDIA": "Metals & Mining", "GMDCLTD": "Metals & Mining", "GRAVITA": "Metals & Mining",
    "CMPDI": "Metals & Mining", "RATNAVEER": "Metals & Mining",
    # Railways
    "RVNL": "Railways", "IRCTC": "Railways",
    # Infra / EPC / Construction
    "LT": "Infra & EPC", "NBCC": "Infra & EPC", "ASHOKA": "Infra & EPC",
    "HGINFRA": "Infra & EPC", "KEC": "Infra & EPC", "CEIGALL": "Infra & EPC",
    "BAJEL": "Infra & EPC", "WABAG": "Infra & EPC", "TARIL": "Infra & EPC",
    "EPACKPEB": "Infra & EPC", "SCI": "Ports & Logistics",
    # Capital Goods / Engineering
    "BHEL": "Capital Goods", "ELECON": "Capital Goods", "TDPOWERSYS": "Capital Goods",
    "CGPOWER": "Capital Goods", "PITTIENG": "Capital Goods", "HBLENGINE": "Capital Goods",
    "KEI": "Capital Goods", "APLAPOLLO": "Capital Goods", "CARBORUNIV": "Capital Goods",
    "AJAXENGG": "Capital Goods", "GVT&D": "Capital Goods", "AEROFLEX": "Capital Goods",
    # Auto & Components
    "TMPV": "Auto", "M&M": "Auto", "MOTHERSON": "Auto Components",
    "MSUMI": "Auto Components", "SANDHAR": "Auto Components", "FIEMIND": "Auto Components",
    "PRICOLLTD": "Auto Components", "SSWL": "Auto Components", "ASKAUTOLTD": "Auto Components",
    # Pharma & Healthcare
    "DIVISLAB": "Pharma", "ZYDUSLIFE": "Pharma", "FDC": "Pharma", "NGLFINE": "Pharma",
    "SHIVALIK": "Pharma", "ACUTAAS": "Pharma", "NH": "Healthcare",
    "ARTEMISMED": "Healthcare", "SURAKSHA": "Healthcare",
    # Chemicals
    "AARTIIND": "Chemicals", "AETHER": "Chemicals", "LXCHEM": "Chemicals",
    "ROSSARI": "Chemicals", "BHARATRAS": "Chemicals", "PAUSHAKLTD": "Chemicals",
    "POCL": "Chemicals", "INDIAGLYCO": "Chemicals", "PASUPTAC": "Chemicals",
    "STYRENIX": "Chemicals",
    # Consumer / Textiles / Retail
    "VBL": "Consumer", "KRBL": "Consumer", "TITAN": "Consumer",
    "WELSPUNLIV": "Textiles", "KPRMILL": "Textiles", "NITINSPIN": "Textiles",
    "BORANA": "Textiles", "MAFATIND": "Textiles", "PGIL": "Textiles",
    "SKYGOLD": "Consumer", "MAYURUNIQ": "Consumer", "CARYSIL": "Consumer",
    "AMBER": "Consumer Durables", "CROMPTON": "Consumer Durables",
    # Realty
    "GODREJPROP": "Realty", "ANANTRAJ": "Realty",
}

GROUP = {
    "ATGL": "Adani Group", "ADANIPORTS": "Adani Group",
    "ADANIPOWER": "Adani Group", "ADANIENSOL": "Adani Group",
    "TATASTEEL": "Tata Group", "TATAPOWER": "Tata Group", "TATAELXSI": "Tata Group",
    "TMPV": "Tata Group", "TITAN": "Tata Group",
    "SBIN": "PSU", "BANKBARODA": "PSU", "MAHABANK": "PSU", "PNB": "PSU",
    "UNIONBANK": "PSU", "NTPC": "PSU", "NLCINDIA": "PSU", "COALINDIA": "PSU",
    "SAIL": "PSU", "NMDC": "PSU", "MOIL": "PSU", "GMDCLTD": "PSU", "HINDCOPPER": "PSU",
    "NATIONALUM": "PSU", "BHEL": "PSU", "BEL": "PSU", "HAL": "PSU", "BDL": "PSU",
    "GRSE": "PSU", "MAZDOCK": "PSU", "IOC": "PSU", "GAIL": "PSU", "PFC": "PSU",
    "IREDA": "PSU", "RVNL": "PSU", "IRCTC": "PSU", "NBCC": "PSU", "SCI": "PSU",
    "GIPCL": "PSU", "CMPDI": "PSU", "HINDZINC": "Vedanta Group",
    "M&M": "Mahindra Group", "GODREJPROP": "Godrej Group",
    "JIOFIN": "Reliance Group", "MOTHERSON": "Motherson Group", "MSUMI": "Motherson Group",
}


def sector_of(symbol: str) -> str:
    return SECTOR.get(symbol, "Other")


def group_of(symbol: str) -> str:
    return GROUP.get(symbol, "")
