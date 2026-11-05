"""
PULSE - Live Price Fetcher
Fetches current prices for all holdings via yfinance (batched, free)
and prints a live P&L table. Run once, or loop with --watch.

Usage:
    python price_fetcher.py            # fetch once + show P&L
    python price_fetcher.py --watch    # refresh every 5 minutes
"""
import sys
import time

import yfinance as yf

from db import all_holdings, save_price, get_prices
from ticker_map import to_yf

BATCH = 40          # symbols per yfinance batch call
REFRESH_SEC = 300   # 5 minutes in --watch mode


def fetch_prices():
    holdings = [h for h in all_holdings() if h["nse_symbol"]]
    symbols = sorted({h["nse_symbol"] for h in holdings})
    yf_syms = [to_yf(s) for s in symbols]

    fetched, failed = 0, []
    for i in range(0, len(yf_syms), BATCH):
        chunk = yf_syms[i:i + BATCH]
        try:
            data = yf.download(
                tickers=" ".join(chunk), period="2d", interval="1d",
                group_by="ticker", progress=False, threads=True,
            )
        except Exception as e:
            failed.extend(chunk)
            print(f"  batch failed: {e}")
            continue

        for ysym in chunk:
            base = ysym.replace(".NS", "")
            try:
                closes = data[ysym]["Close"].dropna() if len(chunk) > 1 else data["Close"].dropna()
                if len(closes) == 0:
                    failed.append(ysym); continue
                ltp = float(closes.iloc[-1])
                prev = float(closes.iloc[-2]) if len(closes) > 1 else ltp
                save_price(base, ltp, prev)
                fetched += 1
            except Exception:
                failed.append(ysym)

    print(f"Prices fetched: {fetched}/{len(symbols)}")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(f.replace('.NS','') for f in failed)}")
        print("   -> These are likely wrong ticker symbols. Fix them in ticker_map.py")
    return fetched, failed


def show_pnl():
    holdings = all_holdings()
    prices = get_prices()

    rows, tot_cost, tot_val = [], 0.0, 0.0
    for h in holdings:
        sym = h["nse_symbol"]
        p = prices.get(sym) if sym else None
        cost = h["qty"] * h["avg_cost"]
        if p and p["ltp"]:
            val = h["qty"] * p["ltp"]
            rows.append((h["company_name"][:28], sym, h["qty"], h["avg_cost"],
                         p["ltp"], val - cost, (val - cost) / cost * 100, p["day_change_pct"]))
            tot_cost += cost
            tot_val += val
        else:
            rows.append((h["company_name"][:28], sym or "?", h["qty"], h["avg_cost"],
                         None, None, None, None))

    rows.sort(key=lambda r: (r[5] is None, -(r[5] or 0)))

    print("\n" + "=" * 108)
    print(f"{'COMPANY':<28} {'SYMBOL':<12} {'QTY':>6} {'AVG':>9} {'LTP':>9} "
          f"{'P&L Rs':>12} {'P&L %':>8} {'DAY %':>7}")
    print("-" * 108)
    for r in rows:
        name, sym, qty, avg, ltp, pnl, pct, day = r
        if ltp is None:
            print(f"{name:<28} {sym:<12} {qty:>6.0f} {avg:>9.2f} {'--':>9} {'--':>12} {'--':>8} {'--':>7}")
        else:
            print(f"{name:<28} {sym:<12} {qty:>6.0f} {avg:>9.2f} {ltp:>9.2f} "
                  f"{pnl:>12,.0f} {pct:>7.1f}% {day if day is not None else 0:>6.2f}%")
    print("-" * 108)
    pnl_total = tot_val - tot_cost
    pct_total = pnl_total / tot_cost * 100 if tot_cost else 0
    print(f"{'PORTFOLIO TOTAL':<48} cost Rs {tot_cost:>12,.0f}   value Rs {tot_val:>12,.0f}   "
          f"P&L Rs {pnl_total:>+12,.0f} ({pct_total:+.2f}%)")
    print("=" * 108)


if __name__ == "__main__":
    watch = "--watch" in sys.argv
    while True:
        print("\nFetching live prices...")
        fetch_prices()
        show_pnl()
        if not watch:
            break
        print(f"\nNext refresh in {REFRESH_SEC // 60} min (Ctrl+C to stop)")
        time.sleep(REFRESH_SEC)
