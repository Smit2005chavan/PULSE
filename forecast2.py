"""
PULSE 2.0 - Future View Engine (up to 50 days ahead)
METHOD (honest and explainable):
  1. Trend: blend of 20-day average slope + damped 60-day drift
  2. Uncertainty: this stock's own recent daily volatility
  3. Monte Carlo: simulate 2,000 possible price paths for 50 days
  4. Report: likely range (middle 50% of paths), wide range (80%),
     and chance-of-being-higher for day 3, 8, 15, 30, 50
  5. Honesty check: backtested on this stock's own history —
     "how often did the real price stay inside our predicted wide range?"

This produces a probability FAN, not a single fake number. That is the
correct, defensible way to talk about the future of a stock price.
"""
import numpy as np
import pandas as pd

from db import get_conn

HORIZONS = [3, 8, 15, 30, 50]
N_PATHS = 2000
N_DAYS = 50


def load_close(symbol):
    with get_conn() as c:
        rows = c.execute("SELECT date, close FROM history WHERE nse_symbol=? "
                         "ORDER BY date", (symbol,)).fetchall()
    return pd.DataFrame(rows, columns=["date", "close"])


def _drift_sigma(close: pd.Series):
    """Daily drift (damped) and volatility from recent history."""
    rets = np.log(close / close.shift()).dropna()
    if len(rets) < 60:
        return 0.0, float(rets.std() or 0.02)
    sigma = float(rets.tail(60).std())
    # trend piece 1: 20-DMA slope as % per day
    dma = close.rolling(20).mean()
    slope_pct = float((dma.iloc[-1] - dma.iloc[-11]) / 10 / dma.iloc[-1])
    # trend piece 2: mean of last 60 daily returns
    mean60 = float(rets.tail(60).mean())
    # blend + damp (trends fade; full extrapolation overshoots)
    drift = 0.5 * slope_pct + 0.5 * mean60
    drift *= 0.6                      # damping factor
    drift = float(np.clip(drift, -0.004, 0.004))   # sanity cap ±0.4%/day
    return drift, max(sigma, 0.005)


def simulate(symbol=None, close=None, seed=42):
    """Monte Carlo fan. Returns dict with percentile bands per day."""
    if close is None:
        df = load_close(symbol)
        if len(df) < 120:
            return None
        close = df["close"]
    price = float(close.iloc[-1])
    drift, sigma = _drift_sigma(close)

    rng = np.random.default_rng(seed)
    shocks = rng.normal(drift - sigma ** 2 / 2, sigma, size=(N_PATHS, N_DAYS))
    paths = price * np.exp(np.cumsum(shocks, axis=1))

    pct = {p: np.percentile(paths, p, axis=0) for p in (10, 25, 50, 75, 90)}
    table = {}
    for h in HORIZONS:
        i = h - 1
        table[h] = {
            "median": float(pct[50][i]),
            "likely_lo": float(pct[25][i]), "likely_hi": float(pct[75][i]),
            "wide_lo": float(pct[10][i]),  "wide_hi": float(pct[90][i]),
            "p_up": float((paths[:, i] > price).mean() * 100),
        }
    return {"price": price, "drift": drift, "sigma": sigma,
            "bands": pct, "table": table}


def backtest_accuracy(symbol=None, close=None, horizon=15, n_anchors=40):
    """Walk history: at n anchor dates, run the same model on data up to that
    date; check if the REAL price `horizon` days later fell inside the
    predicted wide range (10th-90th percentile). Returns hit-rate %."""
    if close is None:
        df = load_close(symbol)
        if len(df) < 300:
            return None, 0
        close = df["close"]
    n = len(close)
    anchors = np.linspace(150, n - horizon - 1, n_anchors).astype(int)
    hits = total = 0
    for a in anchors:
        hist = close.iloc[:a + 1]
        price = float(hist.iloc[-1])
        drift, sigma = _drift_sigma(hist)
        # analytic lognormal band (fast, same distribution as the MC)
        mu = (drift - sigma ** 2 / 2) * horizon
        sd = sigma * np.sqrt(horizon)
        lo = price * np.exp(mu - 1.2816 * sd)     # 10th pct
        hi = price * np.exp(mu + 1.2816 * sd)     # 90th pct
        real = float(close.iloc[a + horizon])
        total += 1
        if lo <= real <= hi:
            hits += 1
    return (round(hits / total * 100) if total else None), total


def report(symbol):
    res = simulate(symbol)
    if not res:
        print("Not enough history (need 120+ days).")
        return
    acc15, n15 = backtest_accuracy(symbol, horizon=15)
    acc50, n50 = backtest_accuracy(symbol, horizon=50, n_anchors=25)
    p = res["price"]
    print(f"\n=== {symbol} — Future View (Monte Carlo, 2000 paths) ===")
    print(f"Today ₹{p:.1f} | daily trend {res['drift']*100:+.3f}% | "
          f"daily wobble {res['sigma']*100:.2f}%\n")
    print(f"{'DAY':>4} {'MOST LIKELY':>12} {'LIKELY RANGE (50%)':>22} "
          f"{'WIDE RANGE (80%)':>22} {'CHANCE HIGHER':>14}")
    print("-" * 80)
    for h in HORIZONS:
        t = res["table"][h]
        print(f"+{h:>3} {f'₹{t['median']:.0f}':>12} "
              f"{f'₹{t['likely_lo']:.0f} – ₹{t['likely_hi']:.0f}':>22} "
              f"{f'₹{t['wide_lo']:.0f} – ₹{t['wide_hi']:.0f}':>22} "
              f"{t['p_up']:>13.0f}%")
    print("-" * 80)
    if acc15 is not None:
        print(f"HONESTY CHECK on this stock's own past: real price stayed inside "
              f"our wide range\n  {acc15}% of the time at 15 days ({n15} tests), "
              f"{acc50}% at 50 days ({n50} tests).")
    print("Read it as a weather forecast: ranges and chances, never a promise.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        report(sys.argv[1].upper())
    else:
        print("Usage: python forecast2.py SYMBOL")
