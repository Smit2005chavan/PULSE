# PULSE 2.0 — Stock Portfolio Intelligence System

A personal portfolio tracker and advisor built in Python with Streamlit. I built it so my father could get immediate notifications and clear, in-depth advice while keeping an eye on a large stock portfolio.

## What it does
- **Portfolio loader:** reads the broker's holdings file, maps company names to NSE symbols and stores everything in a local SQLite database.
- **Data pipeline:** fetches latest prices and daily history (Yahoo Finance via `yfinance`) and saves them for analysis.
- **Technical analysis:** RSI, MACD, 50/200-day averages, ATR, volume spikes, and ATR-based stop-loss and target levels for every holding.
- **Pattern detection:** chart patterns (head & shoulders, double top/bottom, wedges, breakouts, golden/death cross) and candlestick patterns, each with a success rate measured on that stock's own history.
- **Future view:** a 50-day Monte Carlo price range with a backtest of how often the range held.
- **Analyst consensus:** analyst ratings and price targets where Yahoo has coverage.
- **Should I Buy?:** a 0–100 score for any stock from technical and fundamental checks.
- **Sector view:** sector concentration and promoter-group risk across the portfolio.
- **Telegram alerts:** a daily digest and opportunity alerts sent to your phone.

## Setup
1. Install Python 3.10+ and the libraries: `pip install -r requirements.txt`
2. Put your broker holdings file in the project folder (do not commit it) and load it:
   `python portfolio_parser.py "PortFolioEqtSummary.xls"`
3. Fetch data: `python price_fetcher.py` then `python history_fetcher.py`
4. *(Optional)* Telegram alerts — create a bot with @BotFather, then set:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `TELEGRAM_CHAT_IDS` = your chat id(s), comma-separated (`python alerts.py --get-chat-id` helps)
5. Run the dashboard: `streamlit run app.py`

On Windows, `daily.bat` refreshes prices, sends the digest and opens the dashboard. See `SETUP_GUIDE.md` for the full walkthrough.

## Notes
- Your tokens and holdings stay on your machine. `.gitignore` keeps the database, holdings files and `.env` out of the repo.
- This is an analysis tool, not financial advice. Forecasts are ranges and probabilities, not guarantees.

## Tech
Python, Streamlit, Pandas, SciPy, Plotly, SQLite, yfinance, Telegram Bot API
