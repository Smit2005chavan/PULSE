"""
PULSE Day 3 - Chart Pattern Detection Engine
Detects on stored history, for every holding:
  - Double Top / Double Bottom
  - Head & Shoulders / Inverse Head & Shoulders
  - 20-day Breakout / Breakdown (Donchian)
  - Golden Cross / Death Cross (50/200 DMA)
Each pattern comes with a per-stock historical reliability check:
how often did this pattern actually work on THIS stock in the past.

Usage:
    python patterns.py           # scan all holdings
    python patterns.py BEL       # deep-dive one symbol
"""
import sys

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from db import all_holdings, get_conn


# ---------------- pivots ----------------

def load_history(symbol: str) -> pd.DataFrame:
    with get_conn() as c:
        rows = c.execute(
            "SELECT date, open, high, low, close, volume FROM history "
            "WHERE nse_symbol=? ORDER BY date", (symbol,)).fetchall()
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def pivots(close: pd.Series, order: int = 5):
    """Indices of local maxima/minima on smoothed close."""
    smooth = close.rolling(3, center=True).mean().bfill().ffill()
    hi = argrelextrema(smooth.values, np.greater_equal, order=order)[0]
    lo = argrelextrema(smooth.values, np.less_equal, order=order)[0]
    # dedupe plateaus
    hi = [int(i) for i in hi if i == 0 or i - 1 not in hi]
    lo = [int(i) for i in lo if i == 0 or i - 1 not in lo]
    return hi, lo


def near(a, b, tol=0.03):
    return abs(a - b) / b <= tol


# ---------------- pattern detectors (look at last ~120 bars) ----------------

def detect_double_top(df, hi, lo):
    c = df["close"].values
    recent_hi = [i for i in hi if i > len(c) - 120]
    if len(recent_hi) < 2:
        return None
    p2, p1 = recent_hi[-1], recent_hi[-2]
    if p2 - p1 < 10:
        return None
    if not near(c[p1], c[p2], 0.04):
        return None
    valley = c[p1:p2].min()
    neckline = valley
    if c[-1] < neckline:                      # confirmed breakdown
        target = neckline - (c[p1] - neckline)
        return ("DOUBLE TOP", "BEARISH", "CONFIRMED", neckline, target)
    if c[-1] < c[p2] * 0.99:
        return ("DOUBLE TOP", "BEARISH", "FORMING", neckline,
                neckline - (c[p1] - neckline))
    return None


def detect_double_bottom(df, hi, lo):
    c = df["close"].values
    recent_lo = [i for i in lo if i > len(c) - 120]
    if len(recent_lo) < 2:
        return None
    p2, p1 = recent_lo[-1], recent_lo[-2]
    if p2 - p1 < 10:
        return None
    if not near(c[p1], c[p2], 0.04):
        return None
    peak = c[p1:p2].max()
    neckline = peak
    if c[-1] > neckline:
        target = neckline + (neckline - c[p1])
        return ("DOUBLE BOTTOM", "BULLISH", "CONFIRMED", neckline, target)
    if c[-1] > c[p2] * 1.01:
        return ("DOUBLE BOTTOM", "BULLISH", "FORMING", neckline,
                neckline + (neckline - c[p1]))
    return None


def detect_hs(df, hi, lo, inverse=False):
    c = df["close"].values
    piv = [i for i in (lo if inverse else hi) if i > len(c) - 150]
    if len(piv) < 3:
        return None
    a, b, d = piv[-3], piv[-2], piv[-1]
    la, lb, ld = c[a], c[b], c[d]
    if inverse:
        head_ok = lb < la and lb < ld and near(la, ld, 0.05)
    else:
        head_ok = lb > la and lb > ld and near(la, ld, 0.05)
    if not head_ok:
        return None
    seg = c[a:d + 1]
    neckline = seg.max() if inverse else seg.min()
    name = "INV HEAD&SHOULDERS" if inverse else "HEAD&SHOULDERS"
    bias = "BULLISH" if inverse else "BEARISH"
    height = abs(lb - neckline)
    if inverse and c[-1] > neckline:
        return (name, bias, "CONFIRMED", neckline, neckline + height)
    if not inverse and c[-1] < neckline:
        return (name, bias, "CONFIRMED", neckline, neckline - height)
    return (name, bias, "FORMING", neckline,
            neckline + height if inverse else neckline - height)


def detect_breakout(df):
    c = df["close"].values
    if len(c) < 25:
        return None
    hi20 = df["high"].values[-21:-1].max()
    lo20 = df["low"].values[-21:-1].min()
    vol_ok = df["volume"].iloc[-1] > 1.5 * df["volume"].tail(20).mean()
    if c[-1] > hi20 and vol_ok:
        return ("20D BREAKOUT", "BULLISH", "CONFIRMED", hi20, c[-1] * 1.08)
    if c[-1] < lo20 and vol_ok:
        return ("20D BREAKDOWN", "BEARISH", "CONFIRMED", lo20, c[-1] * 0.92)
    return None


def detect_cross(df):
    c = df["close"]
    if len(c) < 210:
        return None
    s50 = c.rolling(50).mean()
    s200 = c.rolling(200).mean()
    now, prev = s50.iloc[-1] - s200.iloc[-1], s50.iloc[-6] - s200.iloc[-6]
    if prev < 0 <= now:
        return ("GOLDEN CROSS", "BULLISH", "CONFIRMED", float(s200.iloc[-1]), float(c.iloc[-1] * 1.10))
    if prev > 0 >= now:
        return ("DEATH CROSS", "BEARISH", "CONFIRMED", float(s200.iloc[-1]), float(c.iloc[-1] * 0.90))
    return None


# ---------------- per-stock reliability backtest ----------------

def breakout_reliability(df):
    """How often did a 20d breakout on THIS stock lead to +5% before -5%?"""
    c, h, l, v = (df[k].values for k in ("close", "high", "low", "volume"))
    wins = total = 0
    i = 25
    while i < len(c) - 15:
        hi20 = h[i - 21:i - 1].max()
        volm = v[max(0, i - 20):i].mean()
        if c[i] > hi20 and v[i] > 1.5 * volm:
            total += 1
            entry = c[i]
            fwd = c[i + 1:i + 16]
            hit_t = np.any(fwd >= entry * 1.05)
            hit_s = np.any(fwd <= entry * 0.95)
            first_t = np.argmax(fwd >= entry * 1.05) if hit_t else 99
            first_s = np.argmax(fwd <= entry * 0.95) if hit_s else 99
            if hit_t and first_t <= first_s:
                wins += 1
            i += 10
        i += 1
    return (wins / total * 100, total) if total >= 3 else (None, total)


# ---------------- scan ----------------

def scan_symbol(symbol: str):
    df = load_history(symbol)
    if len(df) < 60:
        return []
    hi, lo = pivots(df["close"])
    found = []
    for det in (lambda: detect_double_top(df, hi, lo),
                lambda: detect_double_bottom(df, hi, lo),
                lambda: detect_hs(df, hi, lo, inverse=False),
                lambda: detect_hs(df, hi, lo, inverse=True),
                lambda: detect_breakout(df),
                lambda: detect_cross(df)):
        try:
            r = det()
            if r:
                found.append(r)
        except Exception:
            pass
    rel, n = breakout_reliability(df)
    return [(symbol, *f, rel, n) for f in found]


def run_all():
    rows = []
    holdings = [h for h in all_holdings() if h["nse_symbol"]]
    print(f"Scanning {len(holdings)} stocks for patterns...\n")
    for h in holdings:
        rows.extend(scan_symbol(h["nse_symbol"]))

    if not rows:
        print("No active patterns right now.")
        return
    order = {"CONFIRMED": 0, "FORMING": 1}
    rows.sort(key=lambda r: (order.get(r[3], 2), r[2] != "BEARISH"))

    print("=" * 110)
    print(f"{'SYMBOL':<12} {'PATTERN':<20} {'BIAS':<8} {'STATUS':<10} "
          f"{'NECKLINE':>9} {'TARGET':>9} {'BRKOUT REL':>11}")
    print("-" * 110)
    for sym, name, bias, status, neck, target, rel, n in rows:
        rels = f"{rel:.0f}% ({n})" if rel is not None else f"n/a ({n})"
        print(f"{sym:<12} {name:<20} {bias:<8} {status:<10} "
              f"{neck:>9.1f} {target:>9.1f} {rels:>11}")
    print("=" * 110)
    bears = sum(1 for r in rows if r[2] == "BEARISH" and r[3] == "CONFIRMED")
    bulls = sum(1 for r in rows if r[2] == "BULLISH" and r[3] == "CONFIRMED")
    print(f"CONFIRMED: {bulls} bullish, {bears} bearish   |   "
          f"'BRKOUT REL' = this stock's own historical 20d-breakout success rate")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        res = scan_symbol(sys.argv[1].upper())
        if not res:
            print("No patterns detected on", sys.argv[1].upper())
        for sym, name, bias, status, neck, target, rel, n in res:
            print(f"{sym}: {name} [{bias}] {status}  neckline={neck:.1f} target={target:.1f}")
    else:
        run_all()
