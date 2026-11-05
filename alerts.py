"""
PULSE v2 - Alert Engine (Telegram)
NEW IN v2:
  --digest    ONE combined message instead of many (recommended daily mode)
  --summary   morning portfolio summary (value, P&L, top movers)
  OPPORTUNITY alerts: confirmed BULLISH patterns with reliability >= 50%

USAGE:
    python alerts.py --get-chat-id
    python alerts.py --dry            # preview individual alerts
    python alerts.py                  # send individual alerts
    python alerts.py --digest         # send ONE bundled digest  (recommended daily mode)
    python alerts.py --digest --dry   # preview digest
    python alerts.py --summary        # send portfolio summary only
"""
import os
import sys
from datetime import datetime

import requests

from db import all_holdings, get_conn, get_prices
from analyze import analyze_symbol
from patterns import scan_symbol

# ============ SET THESE AS ENVIRONMENT VARIABLES ============
# TELEGRAM_BOT_TOKEN : token from @BotFather
# TELEGRAM_CHAT_IDS  : one or more chat ids, separated by commas
# Never put the real values in the code or commit them to GitHub.
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_IDS = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]
# ============================================================

if not BOT_TOKEN:
    raise SystemExit("Set the TELEGRAM_BOT_TOKEN environment variable first (see README).")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def get_chat_id():
    r = requests.get(f"{API}/getUpdates", timeout=10).json()
    ids = {str(u["message"]["chat"]["id"]) for u in r.get("result", []) if "message" in u}
    if ids:
        print("Chat IDs found:")
        for i in ids:
            print("  ", i)
    else:
        print("No chats found. Send 'hi' to your bot on Telegram, run again.")


def send(msg: str, dry=False):
    if dry:
        print("\n--- MESSAGE (dry run) ---\n" + msg)
        return
    # Telegram max 4096 chars: split if needed
    chunks = [msg[i:i + 3900] for i in range(0, len(msg), 3900)]
    for cid in CHAT_IDS:
        for ch in chunks:
            try:
                requests.post(f"{API}/sendMessage",
                              json={"chat_id": cid, "text": ch, "parse_mode": "HTML"},
                              timeout=10)
            except Exception as e:
                print("send failed:", e)


def already_sent_today(symbol, alert_type):
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as c:
        r = c.execute("SELECT 1 FROM alerts WHERE nse_symbol=? AND alert_type=? "
                      "AND date(created_at)=?", (symbol, alert_type, today)).fetchone()
    return r is not None


def log_alert(symbol, alert_type, message):
    with get_conn() as c:
        c.execute("INSERT INTO alerts (nse_symbol, alert_type, message) VALUES (?,?,?)",
                  (symbol, alert_type, message))


def peak_60d(symbol):
    with get_conn() as c:
        r = c.execute("SELECT MAX(close) FROM history WHERE nse_symbol=? "
                      "AND date >= date('now','-60 day')", (symbol,)).fetchone()
    return r[0] or 0


def five_day_change(symbol):
    with get_conn() as c:
        rows = c.execute("SELECT close FROM history WHERE nse_symbol=? "
                         "ORDER BY date DESC LIMIT 6", (symbol,)).fetchall()
    if len(rows) < 6:
        return 0
    return (rows[0][0] - rows[5][0]) / rows[5][0] * 100


def collect_alerts():
    """Returns list of (symbol, type, short_line, full_msg)."""
    prices = get_prices()
    out = []

    print("Scanning patterns...")
    bearish, bullish = {}, {}
    for h in all_holdings():
        sym = h["nse_symbol"]
        if not sym:
            continue
        for row in scan_symbol(sym):
            _, pname, bias, status, neck, target, rel, cnt = row
            if status != "CONFIRMED":
                continue
            if bias == "BEARISH" and (rel is None or rel >= 40):
                bearish[sym] = (pname, target, rel)
            if bias == "BULLISH" and rel is not None and rel >= 50:
                bullish[sym] = (pname, target, rel)

    print("Checking triggers...")
    for h in all_holdings():
        sym = h["nse_symbol"]
        if not sym or sym not in prices:
            continue
        p = prices[sym]
        ltp, day_chg = p["ltp"], p["day_change_pct"] or 0
        qty, avg = h["qty"], h["avg_cost"]
        pnl = (ltp - avg) / avg * 100
        nm = h["company_name"][:24]
        a = analyze_symbol(sym, qty, avg, ltp)
        if not a:
            continue

        if ltp <= a["stop"] and pnl < 0:
            out.append((sym, "STOPLOSS",
                f"🛑 {nm}: ₹{ltp:.0f} ≤ stop ₹{a['stop']:.0f} ({pnl:+.0f}%) — consider EXIT",
                f"🛑 <b>STOP-LOSS HIT — {nm}</b>\nLTP ₹{ltp:.1f} ≤ stop ₹{a['stop']:.1f}\n"
                f"Position {qty:.0f} @ ₹{avg:.1f} ({pnl:+.1f}%). Trend {a['trend']}."))

        f5 = five_day_change(sym)
        if day_chg <= -3 or f5 <= -7:
            out.append((sym, "DECLINE",
                f"📉 {nm}: today {day_chg:+.1f}%, 5d {f5:+.1f}% ({pnl:+.0f}%)",
                f"📉 <b>FAST DECLINE — {nm}</b>\nToday {day_chg:+.1f}% | 5-day {f5:+.1f}%\n"
                f"Your P&L {pnl:+.1f}%. Review position."))

        if sym in bearish:
            pat, tgt, rel = bearish[sym]
            rl = f"{rel:.0f}%" if rel is not None else "n/a"
            out.append((sym, "PATTERN",
                f"📐 {nm}: {pat} confirmed ({rl}), target ₹{tgt:.0f}",
                f"📐 <b>BEARISH PATTERN — {nm}</b>\n{pat} CONFIRMED (reliability {rl})\n"
                f"Target ₹{tgt:.1f} vs LTP ₹{ltp:.1f}. P&L {pnl:+.1f}%."))

        if sym in bullish:
            pat, tgt, rel = bullish[sym]
            out.append((sym, "OPPORTUNITY",
                f"🟢 {nm}: {pat} confirmed ({rel:.0f}%), target ₹{tgt:.0f} — possible ADD",
                f"🟢 <b>OPPORTUNITY — {nm}</b>\n{pat} CONFIRMED (reliability {rel:.0f}%)\n"
                f"Target ₹{tgt:.1f} vs LTP ₹{ltp:.1f}. Consider adding on strength."))

        pk = peak_60d(sym)
        if pnl > 20 and pk > 0:
            pkg = (pk - avg) / avg * 100
            if pkg > 25 and (pkg - pnl) >= pkg / 3:
                out.append((sym, "PROFITPROT",
                    f"💰 {nm}: was +{pkg:.0f}%, now +{pnl:.0f}% — book partial?",
                    f"💰 <b>PROFIT SLIPPING — {nm}</b>\nWas +{pkg:.0f}% at 60d peak, "
                    f"now +{pnl:.0f}%. Gave back a third. Book partial?"))

        if ltp >= a["t1"] and pnl > 10:
            out.append((sym, "TARGET",
                f"🎯 {nm}: ₹{ltp:.0f} ≥ T1 ₹{a['t1']:.0f} ({pnl:+.0f}%) — book 25%",
                f"🎯 <b>TARGET REACHED — {nm}</b>\n₹{ltp:.1f} ≥ T1 ₹{a['t1']:.1f} "
                f"({pnl:+.1f}%). Book 25%, next target ₹{a['t2']:.1f}."))

        if pnl <= -25 and a["trend"] == "DOWN":
            out.append((sym, "DEEPLOSS",
                f"⚠️ {nm}: {pnl:+.0f}%, downtrend — dead money",
                f"⚠️ <b>DEEP LOSS + DOWNTREND — {nm}</b>\nP&L {pnl:+.1f}% | RSI "
                f"{a['rsi']:.0f} | below both DMAs. Verdict {a['verdict']}."))
    return out


def run_individual(dry=False):
    n = 0
    for sym, typ, short, full in collect_alerts():
        if not already_sent_today(sym, typ):
            send(full, dry=dry)
            if not dry:
                log_alert(sym, typ, full)
            n += 1
    print(f"\nDone. Alerts {'printed' if dry else 'sent'}: {n}")


def run_digest(dry=False):
    alerts = [a for a in collect_alerts() if not already_sent_today(a[0], a[1])]
    if not alerts:
        print("Nothing new to report.")
        return
    order = {"STOPLOSS": 0, "DEEPLOSS": 1, "PATTERN": 2, "DECLINE": 3,
             "PROFITPROT": 4, "TARGET": 5, "OPPORTUNITY": 6}
    alerts.sort(key=lambda a: order.get(a[1], 9))
    head = (f"📊 <b>PULSE DIGEST</b> — {datetime.now().strftime('%d %b, %I:%M %p')}\n"
            f"{len(alerts)} signals\n" + "─" * 22)
    body = "\n\n".join(a[2] for a in alerts)
    send(head + "\n" + body, dry=dry)
    if not dry:
        for sym, typ, _, full in alerts:
            log_alert(sym, typ, full)
    print(f"Digest with {len(alerts)} signals {'printed' if dry else 'sent'}.")


def run_summary(dry=False):
    prices = get_prices()
    rows = []
    cost = val = 0.0
    for h in all_holdings():
        sym = h["nse_symbol"]
        p = prices.get(sym) if sym else None
        if not p or not p["ltp"]:
            continue
        c0 = h["qty"] * h["avg_cost"]
        v0 = h["qty"] * p["ltp"]
        cost += c0
        val += v0
        rows.append((h["company_name"][:20], p["day_change_pct"] or 0,
                     (p["ltp"] - h["avg_cost"]) * h["qty"]))
    rows.sort(key=lambda r: r[1])
    losers = rows[:3]
    gainers = rows[-3:][::-1]
    pnl = val - cost
    msg = (f"☀️ <b>PULSE SUMMARY</b> — {datetime.now().strftime('%d %b %Y')}\n"
           f"Portfolio: ₹{val/1e5:.2f}L  (P&L ₹{pnl/1e3:+.0f}K, {pnl/cost*100:+.2f}%)\n"
           f"\n🔺 Top movers today:\n" +
           "\n".join(f"  {n}: {d:+.1f}%" for n, d, _ in gainers) +
           f"\n🔻 Weakest today:\n" +
           "\n".join(f"  {n}: {d:+.1f}%" for n, d, _ in losers))
    send(msg, dry=dry)
    print("Summary", "printed" if dry else "sent")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    if "--get-chat-id" in sys.argv:
        get_chat_id()
    elif "--summary" in sys.argv:
        run_summary(dry)
    elif "--digest" in sys.argv:
        run_digest(dry)
    else:
        run_individual(dry)
