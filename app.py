"""
PULSE 2.0 - Plain-Language Portfolio Intelligence
Sections (everyday words, no jargon):
  🏠 Today          - what needs your attention right now
  💼 My Stocks      - every holding with a clear one-word advice
  🩺 Stock Doctor   - full check-up of any stock you own
  🔮 Future View    - 50-day probability forecast (weather-style fan chart)
  🛒 Should I Buy?  - complete report card for ANY stock, 0-100 score
  💡 Best To Add    - strongest stocks you already own
  🔔 Alerts         - everything the system has flagged

THE STANDOUT FEATURE — "Honesty Engine":
Every signal shows its own measured track record ON THAT STOCK:
candle patterns show their real success rate, forecasts show how often
their ranges actually contained the price. No textbook faith — evidence.

Run:  streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from db import all_holdings, get_conn, get_prices, init_db
from analyze import analyze_symbol, rsi, macd, atr, load_history
from patterns2 import scan_chart, scan_candles
from forecast2 import simulate, backtest_accuracy, HORIZONS
from sectors import sector_of, group_of
from analysts import get_analyst_view

st.set_page_config(page_title="PULSE 2.0", page_icon="⚡", layout="wide")
init_db()

st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}
.block-container {padding-top:1.2rem; padding-bottom:2rem; max-width:1300px;}
.hero {background:linear-gradient(120deg,#1e1b4b 0%,#0f172a 55%,#052e2b 100%);
 border:1px solid rgba(139,92,246,.35); border-radius:18px;
 padding:22px 28px; margin-bottom:18px;}
.hero h1 {margin:0;font-size:30px;letter-spacing:-.5px;
 background:linear-gradient(90deg,#a78bfa,#34d399);
 -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.hero p {margin:4px 0 0;color:#94a3b8;font-size:13px;}
.kpi {background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);
 border-radius:14px;padding:14px 18px;}
.kpi .lab {font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:#64748b;}
.kpi .val {font-size:24px;font-weight:800;margin-top:2px;color:#e2e8f0;}
.kpi .sub {font-size:12px;margin-top:2px;}
.pos {color:#34d399;} .neg {color:#f87171;}
.badge {padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;}
.b-exit{background:rgba(239,68,68,.15);color:#fca5a5;border:1px solid #ef4444;}
.b-red{background:rgba(245,158,11,.15);color:#fcd34d;border:1px solid #f59e0b;}
.b-watch{background:rgba(234,179,8,.12);color:#fde68a;border:1px solid #eab308;}
.b-hold{background:rgba(59,130,246,.15);color:#93c5fd;border:1px solid #3b82f6;}
.b-add{background:rgba(16,185,129,.15);color:#6ee7b7;border:1px solid #10b981;}
.action{background:rgba(255,255,255,.03);border-left:4px solid #8b5cf6;
 border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:14px;}
.action.red{border-left-color:#ef4444;} .action.amber{border-left-color:#f59e0b;}
.action.green{border-left-color:#10b981;}
.score-ring{font-size:42px;font-weight:900;}
section[data-testid="stSidebar"]{background:#0d1526;
 border-right:1px solid rgba(139,92,246,.25);}
</style>""", unsafe_allow_html=True)

PLOT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"), margin=dict(l=10, r=10, t=30, b=10))

# plain-language advice words
ADVICE = {"EXIT": "Sell", "REDUCE": "Sell Some", "WATCH": "Be Careful",
          "HOLD": "Keep", "HOLD/ADD": "Keep / Buy More"}
ADVICE_BADGE = {"Sell": "b-exit", "Sell Some": "b-red", "Be Careful": "b-watch",
                "Keep": "b-hold", "Keep / Buy More": "b-add"}


def badge(v):
    return f"<span class='badge {ADVICE_BADGE.get(v,'b-hold')}'>{v}</span>"


def kpi(label, value, sub="", cls=""):
    return (f"<div class='kpi'><div class='lab'>{label}</div>"
            f"<div class='val'>{value}</div><div class='sub {cls}'>{sub}</div></div>")


@st.cache_data(ttl=300)
def cached_prices():
    return get_prices()


@st.cache_data(ttl=300)
def full_table():
    prices = cached_prices()
    rows = []
    for h in all_holdings():
        sym = h["nse_symbol"]
        p = prices.get(sym) if sym else None
        if not p or not p["ltp"]:
            continue
        ltp = p["ltp"]
        a = analyze_symbol(sym, h["qty"], h["avg_cost"], ltp)
        rows.append({
            "Company": h["company_name"][:26], "Symbol": sym,
            "Sector": sector_of(sym), "Group": group_of(sym),
            "Qty": h["qty"], "Bought At": round(h["avg_cost"], 1),
            "Price Now": round(ltp, 1), "Value": round(ltp * h["qty"]),
            "Profit ₹": round((ltp - h["avg_cost"]) * h["qty"]),
            "Profit %": round((ltp - h["avg_cost"]) / h["avg_cost"] * 100, 1),
            "Today %": round(p["day_change_pct"] or 0, 2),
            "Direction": {"STRONG UP": "Rising strongly", "UP": "Rising",
                          "WEAK": "Losing steam", "DOWN": "Falling"}.get(
                              a["trend"], "-") if a else "-",
            "Momentum": round(a["rsi"]) if a else None,
            "Safety Exit": round(a["stop"], 1) if a else None,
            "Advice": ADVICE.get(a["verdict"], "-") if a else "-",
            "_rr": a["rr"] if a else 0, "_trend": a["trend"] if a else "-",
        })
    return pd.DataFrame(rows)


def fan_chart(close_hist, sim, title=""):
    """History tail + Monte Carlo probability fan."""
    hist = close_hist.tail(120)
    hx = list(range(-len(hist) + 1, 1))
    fx = list(range(1, 51))
    b = sim["bands"]
    fig = go.Figure()
    fig.add_scatter(x=hx, y=hist.values, name="Past price",
                    line=dict(color="#e2e8f0", width=2))
    fig.add_scatter(x=fx, y=b[90], line=dict(width=0), showlegend=False)
    fig.add_scatter(x=fx, y=b[10], fill="tonexty", name="Wide range (80% of outcomes)",
                    line=dict(width=0), fillcolor="rgba(139,92,246,.15)")
    fig.add_scatter(x=fx, y=b[75], line=dict(width=0), showlegend=False)
    fig.add_scatter(x=fx, y=b[25], fill="tonexty", name="Likely range (50% of outcomes)",
                    line=dict(width=0), fillcolor="rgba(52,211,153,.22)")
    fig.add_scatter(x=fx, y=b[50], name="Middle path",
                    line=dict(color="#34d399", width=2, dash="dot"))
    fig.update_layout(height=420, title=title,
                      xaxis_title="Days (0 = today)", **PLOT)
    return fig


def candle_fig(dfx, sym, n=200):
    dfx = dfx.tail(n)
    fig = go.Figure([
        go.Candlestick(x=dfx.index, open=dfx["open"], high=dfx["high"],
                       low=dfx["low"], close=dfx["close"], name=sym,
                       increasing_line_color="#34d399",
                       decreasing_line_color="#f87171"),
        go.Scatter(x=dfx.index, y=dfx["close"].rolling(50).mean(),
                   name="50-day average", line=dict(color="#a78bfa", width=1.6))])
    fig.update_layout(height=400, xaxis_rangeslider_visible=False, **PLOT)
    return fig


def show_patterns(chart_pats, candle_pats):
    if chart_pats:
        st.markdown("#### 📐 Shapes on the chart")
        for name, bias, status, level, target in chart_pats:
            cls = "green" if bias == "BULLISH" else \
                  "red" if bias == "BEARISH" else "amber"
            word = {"BULLISH": "points UP", "BEARISH": "points DOWN",
                    "NEUTRAL": "undecided"}[bias]
            stat = "already triggered" if status == "CONFIRMED" else "still forming"
            st.markdown(f"<div class='action {cls}'><b>{name}</b> — {word}, {stat}. "
                        f"Key level ₹{level:.0f} → possible move to ₹{target:.0f}"
                        f"</div>", unsafe_allow_html=True)
    if candle_pats:
        st.markdown("#### 🕯️ Candle signals (last 3 sessions)")
        for p in candle_pats:
            cls = "green" if p["bias"] == "BULLISH" else \
                  "red" if p["bias"] == "BEARISH" else "amber"
            word = {"BULLISH": "points UP", "BEARISH": "points DOWN",
                    "NEUTRAL": "undecided"}[p["bias"]]
            when = "today" if p["days_ago"] == 0 else f"{p['days_ago']} day(s) ago"
            trust = (f"worked {p['success']}% of the time on this stock "
                     f"({p['samples']} past cases)"
                     if p["success"] is not None else
                     f"too few past cases to judge ({p['samples']})")
            st.markdown(f"<div class='action {cls}'><b>{p['name']}</b> — {word}, "
                        f"seen {when}. Track record here: {trust}.</div>",
                        unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def cached_analysts(sym):
    return get_analyst_view(sym)


def show_analysts(sym, price_now=None):
    st.markdown("#### 🧑‍💼 What the experts say")
    av = cached_analysts(sym)
    if not av:
        st.markdown("<div class='action'>No professional analyst coverage found "
                    "for this stock on Yahoo — common for smaller companies. "
                    "Rely on the report card above.</div>", unsafe_allow_html=True)
        return
    n = av["n_analysts"] or 0
    word = av["rating_word"] or "n/a"
    wcls = {"Strong Buy": "b-add", "Buy": "b-add", "Hold": "b-watch",
            "Sell": "b-exit", "Strong Sell": "b-exit"}.get(word, "b-hold")
    px = price_now or av["price"]
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='kpi'><div class='lab'>Experts Tracking</div>"
                f"<div class='val'>{n}</div>"
                f"<div class='sub'>analysts cover this stock</div></div>",
                unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'><div class='lab'>Their Average View</div>"
                f"<div class='val'><span class='badge {wcls}'>{word}</span></div>"
                f"<div class='sub'>score {av['rating_mean']:.1f} "
                f"(1 = best, 5 = worst)</div></div>" if av["rating_mean"] else
                f"<div class='kpi'><div class='lab'>Their Average View</div>"
                f"<div class='val'>n/a</div></div>", unsafe_allow_html=True)
    if av["target_avg"] and px:
        up = (av["target_avg"] - px) / px * 100
        c3.markdown(kpi("Their Average Price Goal",
                        f"₹{av['target_avg']:.0f}",
                        f"{up:+.0f}% vs today · range ₹{av['target_low']:.0f}"
                        f"–₹{av['target_high']:.0f}",
                        "pos" if up >= 0 else "neg"), unsafe_allow_html=True)
    if av["split"]:
        s = av["split"]
        total = sum(s.values()) or 1
        fig = go.Figure()
        colors = {"Strong Buy": "#10b981", "Buy": "#34d399", "Hold": "#fbbf24",
                  "Sell": "#f87171", "Strong Sell": "#ef4444"}
        for k in ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]:
            if s[k]:
                fig.add_bar(y=["Analysts"], x=[s[k]], name=f"{k} ({s[k]})",
                            orientation="h", marker_color=colors[k],
                            text=f"{k}: {s[k]}", textposition="inside")
        fig.update_layout(barmode="stack", height=110, showlegend=False,
                          xaxis=dict(visible=False), yaxis=dict(visible=False),
                          **PLOT)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"How the {total} experts split their opinions right now.")


# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("## ⚡ PULSE 2.0")
    st.caption("Your portfolio, explained in plain words")
    page = st.radio("", ["🏠 Today", "💼 My Stocks", "🩺 Stock Doctor",
                         "🔮 Future View", "🛒 Should I Buy?", "💡 Best To Add",
                         "🔔 Alerts"], label_visibility="collapsed")
    st.divider()
    with st.expander("📖 What do the words mean?"):
        st.markdown("""
- **Momentum (0-100):** how hot the stock is. Under 30 = beaten down,
  over 70 = maybe too hot.
- **Safety Exit:** if price falls to this level, think about selling to
  protect yourself.
- **Likely range:** where the price lands in half of our 2,000 simulations.
- **Track record:** how often this same signal actually worked on this
  stock in the past.""")
    st.caption("⚠️ Educational tool. Not SEBI-registered advice.")

df = full_table()

# ================ TODAY ================
if page == "🏠 Today":
    st.markdown("<div class='hero'><h1>🏠 Today</h1>"
                "<p>What needs your attention right now.</p></div>",
                unsafe_allow_html=True)
    if df.empty:
        st.warning("Run price_fetcher.py first.")
        st.stop()
    cost = (df["Bought At"] * df["Qty"]).sum()
    val = df["Value"].sum()
    pnl = val - cost
    w = {"Keep / Buy More": 1.0, "Keep": .75, "Be Careful": .5,
         "Sell Some": .25, "Sell": 0}
    health = round(df["Advice"].map(w).fillna(.5).mean() * 100)
    rising = round(df["Direction"].str.contains("Rising").mean() * 100)

    c = st.columns(5)
    c[0].markdown(kpi("Money Invested", f"₹{cost/1e5:.1f} L"), unsafe_allow_html=True)
    c[1].markdown(kpi("Worth Today", f"₹{val/1e5:.1f} L"), unsafe_allow_html=True)
    c[2].markdown(kpi("Profit", f"₹{pnl/1e3:+.0f} K", f"{pnl/cost*100:+.2f}%",
                      "pos" if pnl >= 0 else "neg"), unsafe_allow_html=True)
    c[3].markdown(kpi("Portfolio Health", f"{health}/100",
                      "based on every stock's advice",
                      "pos" if health >= 60 else "neg"), unsafe_allow_html=True)
    c[4].markdown(kpi("Stocks Rising", f"{rising}%", f"of {len(df)} stocks"),
                  unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### 🚨 Do these first")
        for _, r in df[df["Advice"] == "Sell"].nsmallest(4, "Profit ₹").iterrows():
            st.markdown(f"<div class='action red'>🔴 <b>Sell {r['Company']}</b> — "
                        f"losing {abs(r['Profit %'])}% and still falling. "
                        f"₹{abs(r['Profit ₹']):,} stuck here.</div>",
                        unsafe_allow_html=True)
        for _, r in df[df["Advice"] == "Sell Some"].nsmallest(2, "Profit ₹").iterrows():
            st.markdown(f"<div class='action amber'>🟠 <b>Sell some {r['Company']}"
                        f"</b> — {r['Profit %']}%, {r['Direction'].lower()}.</div>",
                        unsafe_allow_html=True)
        for _, r in df[df["Profit %"] > 60].nlargest(3, "Profit ₹").iterrows():
            st.markdown(f"<div class='action green'>💰 <b>Protect {r['Company']}"
                        f"</b> — up {r['Profit %']}% (₹{r['Profit ₹']:,}). "
                        f"Consider selling a quarter to lock gains.</div>",
                        unsafe_allow_html=True)
        st.markdown("#### 🧩 Eggs in the same basket")
        grp = df[df["Group"] != ""].groupby("Group")["Value"].sum() \
                                   .sort_values(ascending=False).head(5)
        for g, v in grp.items():
            n = (df["Group"] == g).sum()
            st.markdown(f"<div class='action'>{g}: <b>{n} stocks worth "
                        f"₹{v/1e5:.2f} L ({v/val*100:.0f}%)</b> — these tend to "
                        f"rise and fall together.</div>", unsafe_allow_html=True)
    with right:
        sec = df.groupby("Sector")["Value"].sum().sort_values(ascending=False)
        top = sec.head(9)
        top["Others"] = sec.iloc[9:].sum()
        fig = go.Figure(go.Pie(labels=top.index, values=top.values, hole=.55,
                               textinfo="label+percent",
                               marker=dict(line=dict(color="#0b1120", width=2))))
        fig.update_layout(height=380, title="Where your money sits",
                          showlegend=False, **PLOT)
        st.plotly_chart(fig, use_container_width=True)

# ================ MY STOCKS ================
elif page == "💼 My Stocks":
    st.markdown("<div class='hero'><h1>💼 My Stocks</h1>"
                "<p>Every holding with one clear advice word.</p></div>",
                unsafe_allow_html=True)
    if df.empty:
        st.warning("Run price_fetcher.py first.")
        st.stop()
    f1, f2, f3 = st.columns(3)
    vf = f1.multiselect("Advice", sorted(df["Advice"].unique()))
    sf = f2.multiselect("Sector", sorted(df["Sector"].unique()))
    q = f3.text_input("Search a stock")
    view = df.copy()
    if vf: view = view[view["Advice"].isin(vf)]
    if sf: view = view[view["Sector"].isin(sf)]
    if q:
        view = view[view["Company"].str.contains(q, case=False) |
                    view["Symbol"].str.contains(q, case=False)]
    view = view.sort_values("Profit ₹", ascending=False) \
               .drop(columns=["Value", "Group", "_rr", "_trend"])
    st.dataframe(view, use_container_width=True, height=620, hide_index=True,
                 column_config={
                     "Profit %": st.column_config.NumberColumn(format="%.1f%%"),
                     "Today %": st.column_config.NumberColumn(format="%.2f%%"),
                     "Profit ₹": st.column_config.NumberColumn(format="₹%d")})

# ================ STOCK DOCTOR ================
elif page == "🩺 Stock Doctor":
    st.markdown("<div class='hero'><h1>🩺 Stock Doctor</h1>"
                "<p>Full check-up of a stock you own.</p></div>",
                unsafe_allow_html=True)
    holdings = [h for h in all_holdings() if h["nse_symbol"]]
    names = {f'{h["company_name"][:30]} ({h["nse_symbol"]})': h for h in holdings}
    pick = st.selectbox("Choose your stock", sorted(names))
    h = names[pick]
    sym = h["nse_symbol"]
    ltp = cached_prices().get(sym, {}).get("ltp")
    a = analyze_symbol(sym, h["qty"], h["avg_cost"], ltp)
    if not a:
        st.error("Run history_fetcher.py first.")
        st.stop()
    adv = ADVICE.get(a["verdict"], "Keep")
    pnl = (a["price"] - h["avg_cost"]) * h["qty"]
    st.markdown(f"<div class='hero'><h1>{h['company_name'][:34]}</h1>"
                f"<p>{sym} · {sector_of(sym)} &nbsp; {badge(adv)}</p></div>",
                unsafe_allow_html=True)
    c = st.columns(5)
    c[0].markdown(kpi("Price Now", f"₹{a['price']:.1f}"), unsafe_allow_html=True)
    c[1].markdown(kpi("Your Profit", f"₹{pnl:,.0f}", f"{a['pnl_pct']:+.1f}%",
                      "pos" if pnl >= 0 else "neg"), unsafe_allow_html=True)
    c[2].markdown(kpi("Safety Exit", f"₹{a['stop']:.1f}",
                      "sell if it falls here", "neg"), unsafe_allow_html=True)
    c[3].markdown(kpi("Upside Marks", f"₹{a['t1']:.0f} / ₹{a['t2']:.0f}",
                      "sell a portion at each", "pos"), unsafe_allow_html=True)
    c[4].markdown(kpi("Direction", {"STRONG UP": "Rising strongly",
                                    "UP": "Rising", "WEAK": "Losing steam",
                                    "DOWN": "Falling"}[a["trend"]],
                      f"Momentum {a['rsi']:.0f}/100"), unsafe_allow_html=True)
    st.write("")
    hist = load_history(sym)
    hist["date"] = pd.to_datetime(hist["date"])
    hist = hist.set_index("date")
    st.plotly_chart(candle_fig(hist, sym), use_container_width=True)
    show_patterns(scan_chart(sym), scan_candles(sym))
    show_analysts(sym, price_now=a["price"])

# ================ FUTURE VIEW ================
elif page == "🔮 Future View":
    st.markdown("<div class='hero'><h1>🔮 Future View</h1>"
                "<p>The next 50 days as a weather forecast — 2,000 simulated "
                "paths, shown as ranges and chances. Never a promise.</p></div>",
                unsafe_allow_html=True)
    holdings = sorted({h["nse_symbol"] for h in all_holdings() if h["nse_symbol"]})
    mode = st.radio("Pick from", ["My stocks", "Type any stock"],
                    horizontal=True)
    if mode == "My stocks":
        sym = st.selectbox("Stock", holdings)
        close = None
    else:
        sym = st.text_input("NSE symbol", placeholder="TATAPOWER...").strip().upper()
        close = None
        if sym:
            dfy = yf.Ticker(f"{sym}.NS").history(period="2y")
            if dfy is None or len(dfy) < 120:
                st.error("Not enough data for this symbol.")
                st.stop()
            close = dfy["Close"]
    if sym:
        with st.spinner("Simulating 2,000 possible futures..."):
            sim = simulate(sym if close is None else None, close=close)
        if not sim:
            st.error("Not enough history. Run history_fetcher.py")
            st.stop()
        if close is None:
            from forecast2 import load_close
            close = load_close(sym)["close"]
        st.plotly_chart(fan_chart(close, sim, f"{sym} — next 50 days"),
                        use_container_width=True)
        st.markdown("#### The numbers")
        cols = st.columns(len(HORIZONS))
        for i, hz in enumerate(HORIZONS):
            t = sim["table"][hz]
            cols[i].markdown(kpi(
                f"In {hz} days",
                f"₹{t['likely_lo']:.0f}–{t['likely_hi']:.0f}",
                f"{t['p_up']:.0f}% chance higher than today",
                "pos" if t["p_up"] >= 50 else "neg"), unsafe_allow_html=True)
        acc, n = backtest_accuracy(sym if close is None else None,
                                   close=close, horizon=15)
        if acc is not None:
            st.markdown(f"<div class='action'>✅ <b>Honesty check:</b> when we "
                        f"tested this same method on this stock's own past "
                        f"({n} tests), the real price stayed inside our wide "
                        f"range <b>{acc}%</b> of the time at 15 days.</div>",
                        unsafe_allow_html=True)

# ================ SHOULD I BUY ================
elif page == "🛒 Should I Buy?":
    st.markdown("<div class='hero'><h1>🛒 Should I Buy?</h1>"
                "<p>Type any NSE stock — get a full report card with one "
                "score out of 100.</p></div>", unsafe_allow_html=True)
    sym = st.text_input("NSE symbol", placeholder="TATAPOWER, IRFC, ZOMATO...")\
            .strip().upper()
    if sym:
        with st.spinner(f"Preparing {sym}'s report card..."):
            t = yf.Ticker(f"{sym}.NS")
            dfx = t.history(period="2y")
            try:
                info = t.info
            except Exception:
                info = {}
        if dfx is None or len(dfx) < 60:
            st.error("No data — check the symbol.")
            st.stop()
        dfx = dfx.rename(columns=str.lower)[["open", "high", "low", "close",
                                             "volume"]]
        close = dfx["close"]
        price = float(close.iloc[-1])
        r = rsi(close)
        _, _, mh = macd(close)
        a_ = atr(dfx.reset_index(drop=True))
        s50 = float(close.rolling(50).mean().iloc[-1])
        s200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
        up50, up200 = price > s50, bool(s200 and price > s200)
        stop = min(max(price - 2.5 * a_,
                       float(dfx["low"].tail(20).min()) * .99), price * .97)
        t1, t2 = price + 2 * a_, price + 4 * a_

        tech, tn = 0, []
        if up50: tech += 15; tn.append("✅ Price above its 50-day average (+15)")
        else: tn.append("❌ Price below its 50-day average (0)")
        if up200: tech += 15; tn.append("✅ Above its 200-day average — long uptrend (+15)")
        else: tn.append("❌ Below its 200-day average (0)")
        if mh > 0: tech += 15; tn.append("✅ Momentum turning up (+15)")
        else: tn.append("❌ Momentum turning down (0)")
        if 40 <= r <= 65: tech += 15; tn.append(f"✅ Momentum meter healthy at {r:.0f} (+15)")
        elif r < 30: tech += 8; tn.append(f"🟡 Beaten down ({r:.0f}) — could bounce (+8)")
        else: tn.append(f"❌ Running hot ({r:.0f}) — risky entry (0)")

        fund, fn = 0, []
        pe = info.get("trailingPE")
        if pe and 0 < pe < 35: fund += 10; fn.append(f"✅ Price vs earnings fair ({pe:.0f}) (+10)")
        elif pe: fn.append(f"❌ Expensive vs earnings ({pe:.0f}) (0)")
        else: fn.append("· Earnings ratio not available")
        de = info.get("debtToEquity")
        if de is not None and de < 100: fund += 10; fn.append(f"✅ Low borrowing ({de:.0f}%) (+10)")
        elif de is not None: fn.append(f"❌ Heavy borrowing ({de:.0f}%) (0)")
        else: fn.append("· Debt level not available")
        roe = info.get("returnOnEquity")
        if roe and roe > .12: fund += 10; fn.append(f"✅ Company earns well on its money ({roe*100:.0f}%) (+10)")
        elif roe is not None: fn.append(f"❌ Weak earning power ({roe*100:.0f}%) (0)")
        else: fn.append("· Earning power not available")
        hi52, lo52 = info.get("fiftyTwoWeekHigh"), info.get("fiftyTwoWeekLow")
        if hi52 and lo52:
            pos = (price - lo52) / (hi52 - lo52 + 1e-9)
            if pos < .8: fund += 10; fn.append(f"✅ Room left before its yearly high (+10)")
            else: fn.append("❌ Already near its yearly high (0)")

        score = tech + fund
        verdict = ("Strong Buy" if score >= 75 else "Good Buy Zone" if score >= 55
                   else "Wait For Better Price" if score >= 35 else "Avoid For Now")
        vcls = {"Strong Buy": "b-add", "Good Buy Zone": "b-add",
                "Wait For Better Price": "b-watch", "Avoid For Now": "b-exit"}[verdict]
        scol = "#34d399" if score >= 55 else "#fbbf24" if score >= 35 else "#f87171"
        name = info.get("longName") or sym

        st.markdown(f"<div class='hero'><h1>{name[:40]}</h1>"
                    f"<p>{sym} &nbsp; <span class='badge {vcls}'>{verdict}</span>"
                    f"</p></div>", unsafe_allow_html=True)
        c = st.columns(5)
        c[0].markdown(f"<div class='kpi'><div class='lab'>Report Card</div>"
                      f"<div class='score-ring' style='color:{scol}'>{score}"
                      f"<span style='font-size:16px;color:#64748b'>/100</span>"
                      f"</div></div>", unsafe_allow_html=True)
        c[1].markdown(kpi("Price Now", f"₹{price:.1f}"), unsafe_allow_html=True)
        c[2].markdown(kpi("If You Buy Today", f"Exit below ₹{stop:.0f}",
                          f"aim for ₹{t1:.0f}, then ₹{t2:.0f}"),
                      unsafe_allow_html=True)
        mc = info.get("marketCap")
        c[3].markdown(kpi("Company Size", f"₹{mc/1e7:,.0f} Cr" if mc else "n/a"),
                      unsafe_allow_html=True)
        c[4].markdown(kpi("Year Range", f"₹{lo52:.0f}–₹{hi52:.0f}"
                          if hi52 else "n/a"), unsafe_allow_html=True)
        st.write("")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f"#### 📊 Price behaviour — {tech}/60")
            for x in tn:
                st.markdown(f"<div class='action'>{x}</div>", unsafe_allow_html=True)
        with g2:
            st.markdown(f"#### 🏛️ Company strength — {fund}/40")
            for x in fn:
                st.markdown(f"<div class='action'>{x}</div>", unsafe_allow_html=True)
        show_analysts(sym, price_now=price)
        show_patterns(scan_chart(dfx.reset_index(drop=True)),
                      scan_candles(dfx.reset_index(drop=True)))
        st.plotly_chart(candle_fig(dfx, sym), use_container_width=True)

# ================ BEST TO ADD ================
elif page == "💡 Best To Add":
    st.markdown("<div class='hero'><h1>💡 Best To Add</h1>"
                "<p>The strongest stocks you already own — adding to winners "
                "usually beats rescuing losers.</p></div>", unsafe_allow_html=True)
    if df.empty:
        st.warning("Run price_fetcher.py first.")
        st.stop()
    cand = df[(df["Advice"] == "Keep / Buy More") &
              (df["Direction"].str.contains("Rising")) &
              (df["Momentum"].between(40, 68))].copy()
    cand["Score"] = (cand["_rr"].clip(0, 3) * 20 +
                     (cand["Direction"] == "Rising strongly") * 20 +
                     (68 - (cand["Momentum"] - 50).abs()).clip(0, 20))
    cand = cand.nlargest(12, "Score")
    if cand.empty:
        st.info("No strong candidates right now — patience is a position too.")
    for _, r in cand.iterrows():
        st.markdown(
            f"<div class='action green'><b>{r['Company']}</b> ({r['Symbol']}) · "
            f"{r['Sector']} · ₹{r['Price Now']} · {r['Direction']} · "
            f"momentum {r['Momentum']} · safety exit ₹{r['Safety Exit']} · "
            f"your profit {r['Profit %']:+.1f}%</div>", unsafe_allow_html=True)
    st.caption("Double-check anything here in 'Should I Buy?' before acting.")

# ================ ALERTS ================
elif page == "🔔 Alerts":
    st.markdown("<div class='hero'><h1>🔔 Alerts</h1>"
                "<p>Everything the system has flagged.</p></div>",
                unsafe_allow_html=True)
    with get_conn() as c:
        rows = c.execute("SELECT created_at, nse_symbol, alert_type, message "
                         "FROM alerts ORDER BY id DESC LIMIT 200").fetchall()
    if not rows:
        st.info("No alerts yet — run alerts.py")
    for r in rows:
        with st.expander(f"{r['created_at']} — {r['nse_symbol']} "
                         f"[{r['alert_type']}]"):
            st.write(r["message"].replace("<b>", "**").replace("</b>", "**"))
