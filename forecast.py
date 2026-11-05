"""
PULSE - Forecast Module (20-DMA projection)
Projects the 20-day moving average trend forward and gives, for day 3 / 8 / 15:
  - expected price RANGE (projected 20DMA +/- ATR band)
  - direction probability (empirical: how often this setup went up historically
    on THIS stock)
  - measured accuracy of the band on THIS stock's own history

This is a RANGE + PROBABILITY forecast — honest math, not a crystal ball.

Usage:
    python forecast.py BEL          # forecast one symbol
    python forecast.py              # summary for all holdings (top table)
"""
import sys

import numpy as np
import pandas as pd

from db import all_holdings, get_conn, get_prices

HORIZONS = [3, 8, 15]


def load_close(symbol):
    with get_conn() as c:
        rows = c.execute("SELECT date, high, low, close FROM history "
                         "WHERE nse_symbol=? ORDER BY date", (symbol,)).fetchall()
    df = pd.DataFrame(rows, columns=["date", "high", "low", "close"])
    return df


def atr14(df):
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / 14, min_periods=14).mean()


def forecast_symbol(symbol, verbose=True):
    df = load_close(symbol)
    if len(df) < 120:
        return None
    close = df["close"]
    dma20 = close.rolling(20).mean()
    a = atr14(df)

    # slope of 20DMA over last 10 sessions (Rs/day)
    y = dma20.tail(10).values
    slope = np.polyfit(range(10), y, 1)[0]
    dma_now = float(dma20.iloc[-1])
    price = float(close.iloc[-1])
    atr_now = float(a.iloc[-1])

    # ---------- empirical stats on THIS stock ----------
    # For each history point: did price close higher after n days when
    # slope sign matched today's? And did price stay within +/-1 ATR of
    # the projected DMA?
    dma_slope_hist = dma20.diff(10) / 10
    results = {}
    for n in HORIZONS:
        proj = dma20 + dma_slope_hist * n          # projected dma n days ahead
        fut = close.shift(-n)
        valid = (~proj.isna()) & (~fut.isna()) & (~a.isna())
        same_sign = np.sign(dma_slope_hist) == np.sign(slope if slope != 0 else 1)
        sel = valid & same_sign
        if sel.sum() < 30:
            sel = valid                              # fallback: all history
        up_prob = float((fut[sel] > close[sel]).mean() * 100)
        in_band = float(((fut[sel] - proj[sel]).abs() <= a[sel]).mean() * 100)
        wide_band = float(((fut[sel] - proj[sel]).abs() <= 2 * a[sel]).mean() * 100)

        proj_now = dma_now + slope * n
        results[n] = {
            "center": proj_now,
            "lo1": proj_now - atr_now, "hi1": proj_now + atr_now,
            "lo2": proj_now - 2 * atr_now, "hi2": proj_now + 2 * atr_now,
            "up_prob": up_prob, "band_acc": in_band, "wide_acc": wide_band,
            "n_samples": int(sel.sum()),
        }

    if verbose:
        trend = "RISING" if slope > 0 else "FALLING"
        print(f"\n=== {symbol} — 20-DMA Projection ===")
        print(f"Price ₹{price:.1f} | 20DMA ₹{dma_now:.1f} ({trend} "
              f"{slope:+.2f}/day) | ATR ₹{atr_now:.1f}\n")
        print(f"{'DAY':>4} {'EXPECTED RANGE (68%)':>24} {'WIDE RANGE (95%)':>24} "
              f"{'P(UP)':>7} {'BAND ACC':>9}")
        print("-" * 75)
        for n in HORIZONS:
            r = results[n]
            print(f"+{n:>3} {f'₹{r['lo1']:.0f} – ₹{r['hi1']:.0f}':>24} "
                  f"{f'₹{r['lo2']:.0f} – ₹{r['hi2']:.0f}':>24} "
                  f"{r['up_prob']:>6.0f}% {r['band_acc']:>8.0f}%")
        print("-" * 75)
        print(f"P(UP) = how often this stock rose after {'/'.join(map(str,HORIZONS))} "
              f"days in similar 20DMA trends ({results[3]['n_samples']} samples)")
        print("BAND ACC = how often the ±1 ATR range actually contained the price "
              "(measured on this stock's own history — trust the number, not hope)")
    return price, results


def run_all():
    prices = get_prices()
    rows = []
    for h in all_holdings():
        sym = h["nse_symbol"]
        if not sym:
            continue
        try:
            out = forecast_symbol(sym, verbose=False)
        except Exception:
            out = None
        if not out:
            continue
        price, res = out
        r3, r15 = res[3], res[15]
        rows.append((sym, price, r3["center"], r3["up_prob"],
                     r15["center"], r15["up_prob"], r3["band_acc"]))
    rows.sort(key=lambda r: -r[3])
    print(f"\n{'SYMBOL':<12} {'PRICE':>8} {'D3 CENTER':>10} {'P(UP) D3':>9} "
          f"{'D15 CENTER':>11} {'P(UP) D15':>10} {'BAND ACC':>9}")
    print("-" * 75)
    for sym, p, c3, u3, c15, u15, acc in rows:
        print(f"{sym:<12} {p:>8.1f} {c3:>10.1f} {u3:>8.0f}% {c15:>11.1f} "
              f"{u15:>9.0f}% {acc:>8.0f}%")
    print("-" * 75)
    print("Sorted by 3-day up-probability. Center = projected 20DMA level.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if forecast_symbol(sys.argv[1].upper()) is None:
            print("Not enough history (need 120+ days). Run history_fetcher.py")
    else:
        run_all()
