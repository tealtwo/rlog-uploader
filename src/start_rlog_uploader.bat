@echo off
REM Rlog Uploader - Windows Batch Launcher
REM This script activates the venv and starts the web server

cd /d "%~dp0"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Set port
set PORT=3445

REM Run the application
python extract_web_server_rlogs.py

pause
