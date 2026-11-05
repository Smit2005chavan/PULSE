"""
PULSE Day 2 - Analysis Engine
Computes for every holding, from stored history:
  RSI(14), MACD(12,26,9), SMA50, SMA200, ATR(14),
  volume spike, 52w high/low distance,
  smart stop-loss (ATR-based, liquidity aware) and targets.

Usage:
    python analyze.py              # analyze all holdings, print table
    python analyze.py BEL          # deep-dive one symbol
"""
import sys

import pandas as pd

from db import all_holdings, get_conn, get_prices


# ---------- indicator math (pure pandas, no extra libs) ----------

def rsi(close: pd.Series, n: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, min_periods=n).mean()
    rs = gain / loss.replace(0, 1e-9)
    return float((100 - 100 / (1 + rs)).iloc[-1])


def macd(close: pd.Series):
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9).mean()
    return float(line.iloc[-1]), float(signal.iloc[-1]), float((line - signal).iloc[-1])


def atr(df: pd.DataFrame, n: int = 14) -> float:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return float(tr.ewm(alpha=1 / n, min_periods=n).mean().iloc[-1])


# ---------- per-stock analysis ----------

def load_history(symbol: str) -> pd.DataFrame:
    with get_conn() as c:
        rows = c.execute(
            "SELECT date, open, high, low, close, volume FROM history "
            "WHERE nse_symbol=? ORDER BY date", (symbol,)).fetchall()
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    return df


def analyze_symbol(symbol: str, qty: float, avg_cost: float, ltp: float):
    df = load_history(symbol)
    if len(df) < 60:
        return None

    close = df["close"]
    price = ltp or float(close.iloc[-1])

    r = rsi(close)
    macd_line, macd_sig, macd_hist = macd(close)
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    a = atr(df)
    vol_avg20 = float(df["volume"].rolling(20).mean().iloc[-1])
    vol_today = float(df["volume"].iloc[-1])
    vol_spike = vol_today / vol_avg20 if vol_avg20 else 1.0
    hi52 = float(close.tail(252).max())
    lo52 = float(close.tail(252).min())

    # ---- smart stop-loss: 2.5 x ATR below price, snapped to recent swing low
    swing_low = float(df["low"].tail(20).min())
    atr_stop = price - 2.5 * a
    stop = max(atr_stop, swing_low * 0.99)
    stop = min(stop, price * 0.97)          # never tighter than 3%
    stop_pct = (stop - price) / price * 100

    # ---- targets from ATR multiples
    t1 = price + 2 * a
    t2 = price + 4 * a
    rr = (t1 - price) / (price - stop) if price > stop else 0

    # ---- trend state
    above50 = price > sma50
    above200 = sma200 is not None and price > sma200
    trend = ("STRONG UP" if above50 and above200 else
             "UP" if above50 else
             "WEAK" if above200 else "DOWN")

    # ---- position P&L
    pnl_pct = (price - avg_cost) / avg_cost * 100 if avg_cost else 0

    # ---- verdict logic (simple, explainable; Day 3 adds patterns)
    reasons = []
    score = 0
    if above50: score += 1; reasons.append("above 50DMA")
    else: reasons.append("below 50DMA")
    if above200: score += 1; reasons.append("above 200DMA")
    elif sma200: reasons.append("below 200DMA")
    if macd_hist > 0: score += 1; reasons.append("MACD bullish")
    else: reasons.append("MACD bearish")
    if 40 <= r <= 65: score += 1; reasons.append(f"RSI healthy {r:.0f}")
    elif r > 70: reasons.append(f"RSI overbought {r:.0f}")
    elif r < 30: reasons.append(f"RSI oversold {r:.0f}")
    else: reasons.append(f"RSI {r:.0f}")
    if vol_spike > 2: reasons.append(f"volume {vol_spike:.1f}x")

    near_52w_low = (price - lo52) / lo52 * 100 < 8

    if pnl_pct < -25 and trend == "DOWN":
        verdict = "EXIT"
        reasons.insert(0, f"deep loss {pnl_pct:.0f}% + downtrend")
    elif trend == "DOWN" and macd_hist < 0 and r < 45:
        verdict = "REDUCE"
    elif score >= 3 and r < 70:
        verdict = "HOLD/ADD"
    elif score >= 2:
        verdict = "HOLD"
    else:
        verdict = "WATCH"
    if near_52w_low and verdict in ("HOLD", "WATCH"):
        reasons.append("near 52w low")

    return {
        "symbol": symbol, "price": price, "pnl_pct": pnl_pct,
        "rsi": r, "macd_hist": macd_hist, "trend": trend,
        "stop": stop, "stop_pct": stop_pct, "t1": t1, "t2": t2, "rr": rr,
        "vol_spike": vol_spike, "hi52": hi52, "lo52": lo52,
        "verdict": verdict, "reasons": ", ".join(reasons[:4]),
    }


def run_all():
    prices = get_prices()
    results = []
    for h in all_holdings():
        sym = h["nse_symbol"]
        if not sym:
            continue
        ltp = prices.get(sym, {}).get("ltp")
        res = analyze_symbol(sym, h["qty"], h["avg_cost"], ltp)
        if res:
            res["name"] = h["company_name"][:24]
            results.append(res)

    order = {"EXIT": 0, "REDUCE": 1, "WATCH": 2, "HOLD": 3, "HOLD/ADD": 4}
    results.sort(key=lambda r: (order.get(r["verdict"], 9), r["pnl_pct"]))

    print("\n" + "=" * 128)
    print(f"{'COMPANY':<24} {'SYM':<11} {'LTP':>8} {'P&L%':>7} {'TREND':>9} "
          f"{'RSI':>4} {'STOP':>8} {'T1':>8} {'R:R':>4}  {'VERDICT':<9} REASONS")
    print("-" * 128)
    for r in results:
        print(f"{r['name']:<24} {r['symbol']:<11} {r['price']:>8.1f} {r['pnl_pct']:>6.1f}% "
              f"{r['trend']:>9} {r['rsi']:>4.0f} {r['stop']:>8.1f} {r['t1']:>8.1f} "
              f"{r['rr']:>4.1f}  {r['verdict']:<9} {r['reasons']}")
    print("=" * 128)

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("SUMMARY: " + "  |  ".join(f"{k}: {v}" for k, v in
          sorted(counts.items(), key=lambda kv: order.get(kv[0], 9))))


def deep_dive(symbol: str):
    h = next((x for x in all_holdings() if x["nse_symbol"] == symbol.upper()), None)
    prices = get_prices()
    ltp = prices.get(symbol.upper(), {}).get("ltp")
    qty = h["qty"] if h else 0
    avg = h["avg_cost"] if h else 0
    r = analyze_symbol(symbol.upper(), qty, avg, ltp)
    if not r:
        print("Not enough history. Run history_fetcher.py first.")
        return
    print(f"\n=== {symbol.upper()} — Deep Dive ===")
    print(f"Price      : Rs {r['price']:.2f}   (52w: {r['lo52']:.1f} – {r['hi52']:.1f})")
    if h:
        print(f"Your pos   : {qty:.0f} @ Rs {avg:.2f}  ->  P&L {r['pnl_pct']:+.1f}%")
    print(f"Trend      : {r['trend']}   RSI: {r['rsi']:.0f}   MACD hist: {r['macd_hist']:+.2f}")
    print(f"Volume     : {r['vol_spike']:.1f}x of 20d average")
    print(f"STOP-LOSS  : Rs {r['stop']:.2f}  ({r['stop_pct']:.1f}%)")
    print(f"Target 1   : Rs {r['t1']:.2f}    Target 2: Rs {r['t2']:.2f}    R:R {r['rr']:.1f}")
    print(f"VERDICT    : {r['verdict']}")
    print(f"Why        : {r['reasons']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        deep_dive(sys.argv[1])
    else:
        run_all()
