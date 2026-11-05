"""
PULSE - Database layer (SQLite for the 5-day build; swap to Postgres later).
Tables:
  holdings  - your positions (from the broker file or manual adds)
  prices    - latest fetched price per symbol
  history   - daily OHLCV (filled on Day 2 for indicators)
  alerts    - alert log (Day 4)
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "pulse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name  TEXT NOT NULL,
    nse_symbol    TEXT,
    map_status    TEXT DEFAULT 'OK',        -- OK / VERIFY / UNMAPPED / BAD
    qty           REAL NOT NULL,
    avg_cost      REAL NOT NULL,
    added_on      TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(company_name)
);

CREATE TABLE IF NOT EXISTS prices (
    nse_symbol    TEXT PRIMARY KEY,
    ltp           REAL,
    prev_close    REAL,
    day_change_pct REAL,
    fetched_at    TEXT
);

CREATE TABLE IF NOT EXISTS history (
    nse_symbol TEXT,
    date       TEXT,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
    PRIMARY KEY (nse_symbol, date)
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nse_symbol  TEXT,
    alert_type  TEXT,
    message     TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    acknowledged INTEGER DEFAULT 0
);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as c:
        c.executescript(SCHEMA)


def upsert_holding(company_name, nse_symbol, map_status, qty, avg_cost):
    with get_conn() as c:
        c.execute(
            """INSERT INTO holdings (company_name, nse_symbol, map_status, qty, avg_cost)
               VALUES (?,?,?,?,?)
               ON CONFLICT(company_name) DO UPDATE SET
                 nse_symbol=excluded.nse_symbol,
                 map_status=excluded.map_status,
                 qty=excluded.qty,
                 avg_cost=excluded.avg_cost""",
            (company_name, nse_symbol, map_status, qty, avg_cost),
        )


def all_holdings():
    with get_conn() as c:
        return c.execute("SELECT * FROM holdings ORDER BY company_name").fetchall()


def save_price(symbol, ltp, prev_close):
    chg = round((ltp - prev_close) / prev_close * 100, 2) if prev_close else None
    with get_conn() as c:
        c.execute(
            """INSERT INTO prices (nse_symbol, ltp, prev_close, day_change_pct, fetched_at)
               VALUES (?,?,?,?, datetime('now','localtime'))
               ON CONFLICT(nse_symbol) DO UPDATE SET
                 ltp=excluded.ltp, prev_close=excluded.prev_close,
                 day_change_pct=excluded.day_change_pct, fetched_at=excluded.fetched_at""",
            (symbol, ltp, prev_close, chg),
        )


def get_prices():
    with get_conn() as c:
        return {r["nse_symbol"]: dict(r) for r in c.execute("SELECT * FROM prices")}
