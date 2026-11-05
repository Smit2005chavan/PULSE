"""
PULSE - Portfolio Parser
Reads the broker 'PortFolioEqtSummary' file (tab-separated .xls) and loads
holdings into the database with NSE symbol mapping.

Usage:
    python portfolio_parser.py path/to/PortFolioEqtSummary.xls
"""
import sys
import pandas as pd

from db import init_db, upsert_holding, all_holdings
from ticker_map import get_symbol


def parse_file(path: str) -> pd.DataFrame:
    """The broker file is actually tab-separated text with an .xls name.
    Fall back to real-Excel parsing if that ever changes."""
    try:
        df = pd.read_csv(path, sep="\t")
        if "Company Name" not in df.columns:
            raise ValueError("tab parse failed")
    except Exception:
        df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]
    required = ["Company Name", "Qty", "Average Cost Price"]
    for col in required:
        if col not in df.columns:
            raise SystemExit(f"Missing expected column: {col}")
    return df


def load_portfolio(path: str):
    init_db()
    df = parse_file(path)
    ok, verify, unmapped = 0, 0, []
    for _, row in df.iterrows():
        name = str(row["Company Name"]).strip()
        symbol, conf = get_symbol(name)
        if symbol is None:
            unmapped.append(name)
            upsert_holding(name, None, "UNMAPPED", float(row["Qty"]), float(row["Average Cost Price"]))
        else:
            upsert_holding(name, symbol, conf, float(row["Qty"]), float(row["Average Cost Price"]))
            if conf == "OK":
                ok += 1
            else:
                verify += 1

    print(f"Loaded {len(df)} holdings into database")
    print(f"   Mapped OK        : {ok}")
    print(f"   Needs VERIFY     : {verify}  (run validate_tickers.py to auto-check)")
    print(f"   UNMAPPED         : {len(unmapped)}")
    for n in unmapped:
        print(f"      - {n}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python portfolio_parser.py <portfolio_file.xls>")
        sys.exit(1)
    load_portfolio(sys.argv[1])
    print(f"\nTotal holdings in DB: {len(all_holdings())}")
