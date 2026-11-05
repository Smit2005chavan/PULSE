@echo off
cd /d "%~dp0"
echo ========================================
echo   PULSE 2.0 - Daily Run
echo ========================================
echo.
echo [1/3] Getting latest prices...
python price_fetcher.py
echo.
echo [2/3] Sending Telegram digest...
python alerts.py --digest
echo.
echo [3/3] Opening dashboard in browser...
echo (Close this window or press Ctrl+C to stop)
streamlit run app.py
pause
