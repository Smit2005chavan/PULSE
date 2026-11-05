@echo off
cd /d "%~dp0"
echo Installing required libraries, please wait 3-5 minutes...
pip install pandas yfinance scipy streamlit plotly requests
echo.
echo Done. Next: run the three commands in SETUP_GUIDE.md Step 5.
pause
