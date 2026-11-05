"""
PULSE 2.0 - Pattern Engine v2
CHART patterns : Head & Shoulders, Inverse H&S, Double Top/Bottom,
                 Rising / Falling Wedge, 20-day Breakout/Breakdown,
                 Golden / Death Cross
CANDLE patterns: 1-candle  (Hammer, Shooting Star, Doji)
                 2-candle  (Bullish/Bearish Engulfing, Piercing Line,
                            Dark Cloud Cover)
                 3-candle  (Morning Star, Evening Star,
                            Three White Soldiers, Three Black Crows)

Every CANDLE pattern carries a measured per-stock success rate:
"after this pattern, was the close higher/lower 5 days later?" —
computed on THIS stock's own history. No textbook faith, only evidence.
"""
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from db import get_conn


# ---------------- data ----------------

def load_history(symbol: str) -> pd.DataFrame:
    with get_conn() as c:
        rows = c.execute(
            "SELECT date, open, high, low, close, volume FROM history "
            "WHERE nse_symbol=? ORDER BY date", (symbol,)).fetchall()
    return pd.DataFrame(rows, columns=["date", "open", "high", "low",
                                       "close", "volume"])


def pivots(close: pd.Series, order: int = 5):
    smooth = close.rolling(3, center=True).mean().bfill().ffill()
    hi = argrelextrema(smooth.values, np.greater_equal, order=order)[0]
    lo = argrelextrema(smooth.values, np.less_equal, order=order)[0]
    hi = [int(i) for i in hi if i == 0 or i - 1 not in hi]
    lo = [int(i) for i in lo if i == 0 or i - 1 not in lo]
    return hi, lo


def near(a, b, tol=0.03):
    return abs(a - b) / max(abs(b), 1e-9) <= tol


# ============ CHART PATTERNS (return: name, bias, status, level, target) ====

def detect_double_top(df, hi, lo):
    c = df["close"].values
    rh = [i for i in hi if i > len(c) - 120]
    if len(rh) < 2:
        return None
    p2, p1 = rh[-1], rh[-2]
    if p2 - p1 < 10 or not near(c[p1], c[p2], .04):
        return None
    neck = c[p1:p2].min()
    tgt = neck - (c[p1] - neck)
    if c[-1] < neck:
        return ("Double Top", "BEARISH", "CONFIRMED", neck, tgt)
    if c[-1] < c[p2] * .99:
        return ("Double Top", "BEARISH", "FORMING", neck, tgt)
    return None


def detect_double_bottom(df, hi, lo):
    c = df["close"].values
    rl = [i for i in lo if i > len(c) - 120]
    if len(rl) < 2:
        return None
    p2, p1 = rl[-1], rl[-2]
    if p2 - p1 < 10 or not near(c[p1], c[p2], .04):
        return None
    neck = c[p1:p2].max()
    tgt = neck + (neck - c[p1])
    if c[-1] > neck:
        return ("Double Bottom", "BULLISH", "CONFIRMED", neck, tgt)
    if c[-1] > c[p2] * 1.01:
        return ("Double Bottom", "BULLISH", "FORMING", neck, tgt)
    return None


def detect_hs(df, hi, lo, inverse=False):
    c = df["close"].values
    piv = [i for i in (lo if inverse else hi) if i > len(c) - 150]
    if len(piv) < 3:
        return None
    a, b, d = piv[-3], piv[-2], piv[-1]
    la, lb, ld = c[a], c[b], c[d]
    ok = (lb < la and lb < ld) if inverse else (lb > la and lb > ld)
    if not ok or not near(la, ld, .05):
        return None
    seg = c[a:d + 1]
    neck = seg.max() if inverse else seg.min()
    h = abs(lb - neck)
    name = "Inverse Head & Shoulders" if inverse else "Head & Shoulders"
    bias = "BULLISH" if inverse else "BEARISH"
    if inverse and c[-1] > neck:
        return (name, bias, "CONFIRMED", neck, neck + h)
    if not inverse and c[-1] < neck:
        return (name, bias, "CONFIRMED", neck, neck - h)
    return (name, bias, "FORMING", neck, neck + h if inverse else neck - h)


def detect_wedge(df, hi, lo):
    """Rising wedge (bearish) / Falling wedge (bullish) on last ~70 bars."""
    c = df["close"].values
    n = len(c)
    rh = [i for i in hi if i > n - 70]
    rl = [i for i in lo if i > n - 70]
    if len(rh) < 3 or len(rl) < 3:
        return None
    hx, hy = np.array(rh[-3:]), c[rh[-3:]]
    lx, ly = np.array(rl[-3:]), c[rl[-3:]]
    sh = np.polyfit(hx, hy, 1)[0]        # slope of highs
    sl = np.polyfit(lx, ly, 1)[0]        # slope of lows
    px = c[-1]
    scale = px / 100.0                   # slopes in Rs/bar -> compare per Rs100
    sh_, sl_ = sh / scale, sl / scale
    # Rising wedge: both rising, lows rising faster -> converging up
    if sh_ > 0.05 and sl_ > 0.05 and sl_ > sh_ * 1.2:
        support = ly[-1] + sl * (n - 1 - lx[-1])
        tgt = px - (hy.max() - ly.min()) * 0.6
        status = "CONFIRMED" if px < support else "FORMING"
        return ("Rising Wedge", "BEARISH", status, support, tgt)
    # Falling wedge: both falling, highs falling faster -> converging down
    if sh_ < -0.05 and sl_ < -0.05 and sh_ < sl_ * 1.2:
        resist = hy[-1] + sh * (n - 1 - hx[-1])
        tgt = px + (hy.max() - ly.min()) * 0.6
        status = "CONFIRMED" if px > resist else "FORMING"
        return ("Falling Wedge", "BULLISH", status, resist, tgt)
    return None


def detect_breakout(df):
    c = df["close"].values
    if len(c) < 25:
        return None
    hi20 = df["high"].values[-21:-1].max()
    lo20 = df["low"].values[-21:-1].min()
    vol_ok = df["volume"].iloc[-1] > 1.5 * df["volume"].tail(20).mean()
    if c[-1] > hi20 and vol_ok:
        return ("20-Day Breakout", "BULLISH", "CONFIRMED", hi20, c[-1] * 1.08)
    if c[-1] < lo20 and vol_ok:
        return ("20-Day Breakdown", "BEARISH", "CONFIRMED", lo20, c[-1] * .92)
    return None


def detect_cross(df):
    c = df["close"]
    if len(c) < 210:
        return None
    s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    now, prev = s50.iloc[-1] - s200.iloc[-1], s50.iloc[-6] - s200.iloc[-6]
    if prev < 0 <= now:
        return ("Golden Cross (50>200 avg)", "BULLISH", "CONFIRMED",
                float(s200.iloc[-1]), float(c.iloc[-1] * 1.10))
    if prev > 0 >= now:
        return ("Death Cross (50<200 avg)", "BEARISH", "CONFIRMED",
                float(s200.iloc[-1]), float(c.iloc[-1] * .90))
    return None


# ============ CANDLE PATTERNS ===============================================
# Each detector works on row index i of (o,h,l,c) arrays; returns True/False.

def _body(o, c):
    return abs(c - o)


def is_hammer(o, h, l, c, i):
    b = _body(o[i], c[i])
    rng = h[i] - l[i]
    if rng <= 0 or b == 0:
        return False
    lower = min(o[i], c[i]) - l[i]
    upper = h[i] - max(o[i], c[i])
    return lower > 2 * b and upper < b and b / rng < .35


def is_shooting_star(o, h, l, c, i):
    b = _body(o[i], c[i])
    rng = h[i] - l[i]
    if rng <= 0 or b == 0:
        return False
    upper = h[i] - max(o[i], c[i])
    lower = min(o[i], c[i]) - l[i]
    return upper > 2 * b and lower < b and b / rng < .35


def is_doji(o, h, l, c, i):
    rng = h[i] - l[i]
    return rng > 0 and _body(o[i], c[i]) / rng < .1


def is_bull_engulf(o, h, l, c, i):
    return (c[i - 1] < o[i - 1] and c[i] > o[i] and
            o[i] <= c[i - 1] and c[i] >= o[i - 1])


def is_bear_engulf(o, h, l, c, i):
    return (c[i - 1] > o[i - 1] and c[i] < o[i] and
            o[i] >= c[i - 1] and c[i] <= o[i - 1])


def is_piercing(o, h, l, c, i):
    mid = (o[i - 1] + c[i - 1]) / 2
    return (c[i - 1] < o[i - 1] and c[i] > o[i] and
            o[i] < c[i - 1] and c[i] > mid and c[i] < o[i - 1])


def is_dark_cloud(o, h, l, c, i):
    mid = (o[i - 1] + c[i - 1]) / 2
    return (c[i - 1] > o[i - 1] and c[i] < o[i] and
            o[i] > c[i - 1] and c[i] < mid and c[i] > o[i - 1])


def is_morning_star(o, h, l, c, i):
    b1 = c[i - 2] < o[i - 2] and _body(o[i - 2], c[i - 2]) > 0
    small = _body(o[i - 1], c[i - 1]) < _body(o[i - 2], c[i - 2]) * .4
    b3 = c[i] > o[i] and c[i] > (o[i - 2] + c[i - 2]) / 2
    return b1 and small and b3


def is_evening_star(o, h, l, c, i):
    b1 = c[i - 2] > o[i - 2] and _body(o[i - 2], c[i - 2]) > 0
    small = _body(o[i - 1], c[i - 1]) < _body(o[i - 2], c[i - 2]) * .4
    b3 = c[i] < o[i] and c[i] < (o[i - 2] + c[i - 2]) / 2
    return b1 and small and b3


def is_three_white(o, h, l, c, i):
    return all(c[i - k] > o[i - k] for k in range(3)) and \
           c[i] > c[i - 1] > c[i - 2]


def is_three_black(o, h, l, c, i):
    return all(c[i - k] < o[i - k] for k in range(3)) and \
           c[i] < c[i - 1] < c[i - 2]


CANDLE_DEFS = [
    ("Hammer (1-candle)",            is_hammer,        "BULLISH", 1),
    ("Shooting Star (1-candle)",     is_shooting_star, "BEARISH", 1),
    ("Doji — indecision (1-candle)", is_doji,          "NEUTRAL", 1),
    ("Bullish Engulfing (2-candle)", is_bull_engulf,   "BULLISH", 2),
    ("Bearish Engulfing (2-candle)", is_bear_engulf,   "BEARISH", 2),
    ("Piercing Line (2-candle)",     is_piercing,      "BULLISH", 2),
    ("Dark Cloud Cover (2-candle)",  is_dark_cloud,    "BEARISH", 2),
    ("Morning Star (3-candle)",      is_morning_star,  "BULLISH", 3),
    ("Evening Star (3-candle)",      is_evening_star,  "BEARISH", 3),
    ("Three White Soldiers (3-candle)", is_three_white, "BULLISH", 3),
    ("Three Black Crows (3-candle)", is_three_black,   "BEARISH", 3),
]


def candle_patterns(df, lookback=3):
    """Detect candle patterns in the last `lookback` sessions, each with a
    measured success rate on this stock's own history (close higher/lower
    5 sessions after the pattern)."""
    if len(df) < 60:
        return []
    o, h, l, c = (df[k].values.astype(float) for k in
                  ("open", "high", "low", "close"))
    n = len(c)
    found = []
    for name, fn, bias, need in CANDLE_DEFS:
        # recent occurrence?
        recent_hit = None
        for i in range(max(need, n - lookback), n):
            try:
                if fn(o, h, l, c, i):
                    recent_hit = i
            except Exception:
                pass
        if recent_hit is None:
            continue
        # historical success rate
        wins = total = 0
        for i in range(need, n - 6):
            try:
                if fn(o, h, l, c, i):
                    total += 1
                    fwd_up = c[i + 5] > c[i]
                    if (bias == "BULLISH" and fwd_up) or \
                       (bias == "BEARISH" and not fwd_up):
                        wins += 1
            except Exception:
                pass
        rate = round(wins / total * 100) if total >= 5 else None
        days_ago = n - 1 - recent_hit
        found.append({"name": name, "bias": bias, "days_ago": days_ago,
                      "success": rate, "samples": total})
    return found


# ============ unified scan ==================================================

def scan_chart(symbol_or_df):
    df = (load_history(symbol_or_df) if isinstance(symbol_or_df, str)
          else symbol_or_df)
    if len(df) < 60:
        return []
    hi, lo = pivots(df["close"])
    out = []
    for det in (lambda: detect_double_top(df, hi, lo),
                lambda: detect_double_bottom(df, hi, lo),
                lambda: detect_hs(df, hi, lo, False),
                lambda: detect_hs(df, hi, lo, True),
                lambda: detect_wedge(df, hi, lo),
                lambda: detect_breakout(df),
                lambda: detect_cross(df)):
        try:
            r = det()
            if r:
                out.append(r)
        except Exception:
            pass
    return out


def scan_candles(symbol_or_df):
    df = (load_history(symbol_or_df) if isinstance(symbol_or_df, str)
          else symbol_or_df)
    return candle_patterns(df)
