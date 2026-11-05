"""
PULSE 2.0 - Analyst Consensus Module
Pulls what professional analysts say about a stock (via Yahoo Finance):
  - how many analysts cover it
  - their average rating (translated to plain words)
  - their price targets: lowest / average / highest, with upside vs today
  - the split: how many say Strong Buy / Buy / Hold / Sell / Strong Sell

Note: analyst data exists mainly for mid & large companies. For tiny
companies Yahoo often has no coverage — we say so honestly instead of
showing nothing.
"""
import yfinance as yf


def rating_words(mean):
    """Yahoo scale: 1 = Strong Buy ... 5 = Strong Sell."""
    if mean is None:
        return None
    if mean <= 1.6:
        return "Strong Buy"
    if mean <= 2.4:
        return "Buy"
    if mean <= 3.4:
        return "Hold"
    if mean <= 4.2:
        return "Sell"
    return "Strong Sell"


def get_analyst_view(symbol: str):
    """Returns dict or None if no coverage."""
    try:
        t = yf.Ticker(f"{symbol}.NS")
        info = t.info or {}
    except Exception:
        return None

    n = info.get("numberOfAnalystOpinions")
    mean = info.get("recommendationMean")
    out = {
        "n_analysts": n,
        "rating_mean": mean,
        "rating_word": rating_words(mean),
        "target_low": info.get("targetLowPrice"),
        "target_avg": info.get("targetMeanPrice"),
        "target_high": info.get("targetHighPrice"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "split": None,
    }

    # buy/hold/sell split (most recent month)
    try:
        rs = t.recommendations_summary
        if rs is not None and len(rs) > 0:
            row = rs.iloc[0]
            out["split"] = {
                "Strong Buy": int(row.get("strongBuy", 0)),
                "Buy": int(row.get("buy", 0)),
                "Hold": int(row.get("hold", 0)),
                "Sell": int(row.get("sell", 0)),
                "Strong Sell": int(row.get("strongSell", 0)),
            }
            if not out["n_analysts"]:
                out["n_analysts"] = sum(out["split"].values())
    except Exception:
        pass

    if not out["n_analysts"] and not out["target_avg"]:
        return None
    return out
