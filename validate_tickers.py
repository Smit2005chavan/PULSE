"""
PULSE - Ticker Validator
Auto-checks every mapped symbol against Yahoo Finance and reports which
ones are wrong so you can fix ticker_map.py once and forget it.

Usage:
    python validate_tickers.py
"""
import yfinance as yf

from ticker_map import TICKER_MAP, to_yf


def validate():
    good, bad = [], []
    items = list(TICKER_MAP.items())
    print(f"Validating {len(items)} tickers against Yahoo Finance...\n")

    for name, (symbol, conf) in items:
        try:
            t = yf.Ticker(to_yf(symbol))
            hist = t.history(period="5d")
            if hist is not None and len(hist) > 0:
                good.append((name, symbol, conf))
                flag = "" if conf == "OK" else "  (was VERIFY - now confirmed)"
                print(f"  OK   {symbol:<12} {name[:35]}{flag}")
            else:
                bad.append((name, symbol, conf))
                print(f"  BAD  {symbol:<12} {name[:35]}  <- no data, wrong symbol?")
        except Exception as e:
            bad.append((name, symbol, conf))
            print(f"  ERR  {symbol:<12} {name[:35]}  <- {type(e).__name__}")

    print(f"\nResult: {len(good)} valid, {len(bad)} need fixing")
    if bad:
        print("\nFix these in ticker_map.py (search NSE symbol on google:")
        print("  '<company name> NSE symbol'):")
        for name, symbol, _ in bad:
            print(f"   - {name}  (current guess: {symbol})")


if __name__ == "__main__":
    validate()
