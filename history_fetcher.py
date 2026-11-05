"""
PULSE Day 2 - History Downloader
Downloads 2 years of daily OHLCV for every holding into the database.
Run once (takes ~3-5 min), then re-run weekly to top up.

Usage:
    python history_fetcher.py
"""
import time

import yfinance as yf

from db import all_holdings, get_conn
from ticker_map import to_yf

BATCH = 25
PERIOD = "2y"


def fetch_history():
    symbols = sorted({h["nse_symbol"] for h in all_holdings() if h["nse_symbol"]})
    yf_syms = [to_yf(s) for s in symbols]
    saved, failed = 0, []

    for i in range(0, len(yf_syms), BATCH):
        chunk = yf_syms[i:i + BATCH]
        print(f"Batch {i//BATCH + 1}: {len(chunk)} symbols...")
        try:
            data = yf.download(tickers=" ".join(chunk), period=PERIOD, interval="1d",
                               group_by="ticker", progress=False, threads=True)
        except Exception as e:
            failed.extend(chunk)
            print(f"   batch failed: {e}")
            continue

        with get_conn() as c:
            for ysym in chunk:
                base = ysym.replace(".NS", "")
                try:
                    df = data[ysym] if len(chunk) > 1 else data
                    df = df.dropna(subset=["Close"])
                    if len(df) == 0:
                        failed.append(base)
                        continue
                    rows = [
                        (base, idx.strftime("%Y-%m-%d"),
                         float(r["Open"]), float(r["High"]), float(r["Low"]),
                         float(r["Close"]), int(r["Volume"]))
                        for idx, r in df.iterrows()
                    ]
                    c.executemany(
                        """INSERT OR REPLACE INTO history
                           (nse_symbol, date, open, high, low, close, volume)
                           VALUES (?,?,?,?,?,?,?)""", rows)
                    saved += 1
                except Exception:
                    failed.append(base)
        time.sleep(1)  # be polite to Yahoo

    print(f"\nHistory saved for {saved}/{len(symbols)} symbols")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    with get_conn() as c:
        n = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    print(f"Total candles in DB: {n:,}")


if __name__ == "__main__":
    fetch_history()
