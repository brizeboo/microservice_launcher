@echo off
cd /d "%~dp0\.."
:: Check for Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit
)

echo Stopping service...
python src\main.py stop

echo Removing service...
python src\main.py remove

echo Service removed.
pause
