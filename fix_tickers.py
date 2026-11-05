"""
PULSE - Ticker Auto-Fixer
Tries candidate NSE symbols for the 7 failed companies (new IPOs / renames),
finds which one actually returns data on Yahoo, and updates the database
automatically. Also uses Yahoo Search as a fallback.

Usage:
    python fix_tickers.py
"""
import yfinance as yf

from db import get_conn

# company_name (as in DB) : list of candidate NSE symbols to try, best guess first
CANDIDATES = {
    "AJAX ENGINEERING LIMITED":       ["AJAXENGG", "AJAX"],
    "CANARA ROBECO ASSET MANAGEMENT": ["CRAMC", "CANROBECO", "CANARAROB", "CANRAMC"],
    "CENTRAL MINE PLANNING N DESIGN": ["CMPDIL", "CMPDI"],
    "EPACK PREFAB TECHNOLOGIES LTD":  ["EPACKPREFAB", "EPACKPFB", "EPPL"],
    "FUJIYAMA POWER SYSTEMS LIMITED": ["FUJIYAMA", "UTLSOLAR", "FPSL"],
    "GNG ELECTRONICS LIMITED":        ["GNGEL", "GNG"],
    "TATA MOTORS LIMITED":            ["TMPV", "TMCV", "TMLCV", "TATAMOTORS"],
}


def works(symbol: str) -> bool:
    try:
        h = yf.Ticker(f"{symbol}.NS").history(period="5d")
        return h is not None and len(h) > 0
    except Exception:
        return False


def yahoo_search(company: str):
    """Fallback: ask Yahoo search for .NS symbols matching the company name."""
    try:
        s = yf.Search(company, max_results=8)
        for q in s.quotes:
            sym = q.get("symbol", "")
            if sym.endswith(".NS"):
                yield sym.replace(".NS", "")
    except Exception:
        return


def fix():
    fixed, unfixed = [], []
    with get_conn() as c:
        for company, cands in CANDIDATES.items():
            print(f"\n{company}")
            found = None
            for sym in cands:
                print(f"   trying {sym} ...", end=" ")
                if works(sym):
                    print("WORKS")
                    found = sym
                    break
                print("no")
            if not found:
                print("   -> trying Yahoo search fallback...")
                for sym in yahoo_search(company):
                    if sym in cands:
                        continue
                    print(f"   trying {sym} (from search) ...", end=" ")
                    if works(sym):
                        print("WORKS")
                        found = sym
                        break
                    print("no")
            if found:
                c.execute(
                    "UPDATE holdings SET nse_symbol=?, map_status='OK' WHERE company_name=?",
                    (found, company),
                )
                fixed.append((company, found))
            else:
                unfixed.append(company)

    print("\n" + "=" * 60)
    print(f"FIXED {len(fixed)}:")
    for comp, sym in fixed:
        print(f"   {comp}  ->  {sym}")
    if unfixed:
        print(f"\nSTILL UNFIXED {len(unfixed)} (google '<name> NSE symbol' and tell me):")
        for comp in unfixed:
            print(f"   - {comp}")
    print("\nNow run:  python price_fetcher.py")


if __name__ == "__main__":
    fix()
