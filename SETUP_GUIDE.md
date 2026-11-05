# PULSE 2.0 — Setup on a New Laptop

## ONE-TIME SETUP (about 15 minutes)

### Step 1 — Install Python
Go to https://www.python.org/downloads/
Download, run installer.
**IMPORTANT: tick the box "Add Python to PATH" on the first screen.**
Restart the computer after installing.

Check it worked — open Command Prompt and type:
```
python --version
```

### Step 2 — Put the folder in place
Extract this zip to:  `C:\PULSE`
(So you have `C:\PULSE\app.py`, `C:\PULSE\db.py`, etc.)

### Step 3 — Add the portfolio file
Download the holdings file from the broker (the `PortFolioEqtSummary` .xls file)
and place it inside `C:\PULSE`.

### Step 4 — Install the libraries
Open Command Prompt and run these two lines:
```
cd C:\PULSE
pip install pandas yfinance scipy streamlit plotly requests
```
(Takes 3-5 minutes.)

### Step 5 — Build the database
Run these three, one after another:
```
python portfolio_parser.py "PortFolioEqtSummary.xls"
python price_fetcher.py
python history_fetcher.py
```
Replace the file name in the first command with the actual file name if different.
Expected: 152 holdings loaded → 152/152 prices → about 72,000 candles saved.

### Step 6 — Telegram alerts (optional, 5 minutes)
1. In Telegram, search for **@BotFather**, send `/newbot`, follow prompts, copy the token.
2. Set the token as an environment variable: `setx TELEGRAM_BOT_TOKEN "your-token"` (then reopen Command Prompt).
3. Open your new bot in Telegram, press START, send "hi".
4. Run: `python alerts.py --get-chat-id` → copy the number.
5. Set it too: `setx TELEGRAM_CHAT_IDS "your-chat-id"` (comma-separate several ids).

### Step 7 — Start the app
```
streamlit run app.py
```
The browser opens at http://localhost:8501

---

## DAILY USE (after this, only this)

Double-click **daily.bat** in the folder.
It refreshes prices, sends the Telegram digest, and opens the dashboard.

Or type manually:
```
cd C:\PULSE
python price_fetcher.py
python alerts.py --digest
streamlit run app.py
```

To stop the app: press Ctrl + C in the black window.

---

## WEEKLY
```
python history_fetcher.py
```

## AFTER BUYING OR SELLING SHARES
Download the new holdings file from the broker into `C:\PULSE`, then:
```
python portfolio_parser.py "NEW_FILE_NAME.xls"
python price_fetcher.py
```

---

## VIEW ON A PHONE (same wifi)
```
streamlit run app.py --server.address 0.0.0.0
```
Find the laptop's IP: type `ipconfig` and look for IPv4 Address.
On the phone's browser open: `http://THAT-IP:8501`

---

## THE SEVEN SECTIONS IN THE APP
| Section | What it does |
|---|---|
| Today | What needs attention right now |
| My Stocks | Every holding with one advice word |
| Stock Doctor | Full check-up of a stock you own |
| Future View | Next 50 days as a range forecast |
| Should I Buy? | Report card out of 100 for any stock |
| Best To Add | Strongest stocks you already own |
| Alerts | History of everything flagged |

---

## IF SOMETHING BREAKS
| Problem | Fix |
|---|---|
| `python` not recognised | Reinstall Python, tick "Add to PATH" |
| `No module named X` | Run the pip install line from Step 4 again |
| `No module named db` | You are in the wrong folder — `cd C:\PULSE` first |
| App shows no data | Run `python price_fetcher.py` |
| Some stock shows no price | Its ticker changed — run `python fix_tickers.py` |
| Sidebar not visible | Click the » arrow at the top-left of the page |

Not SEBI-registered advice. Educational tool only.
