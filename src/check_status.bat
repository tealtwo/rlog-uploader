@echo off
echo ================================================
echo Rlog Uploader - Status Check
echo ================================================
echo.

echo [Task Scheduler Status]
schtasks /Query /TN "RlogUploaderAutoStart" /FO LIST 2>nul
if %errorlevel% neq 0 (
    echo Task not found! Run install_windows_task.ps1 first.
)

echo.
echo [Running Process]
tasklist | findstr /i "python.*extract_web_server_rlogs"
if %errorlevel% neq 0 (
    echo No Python process found for extract_web_server_rlogs.py
    echo Service is NOT running.
) else (
    echo Service is RUNNING!
)

echo.
echo [Web Interface]
echo Try opening: http://localhost:3445
echo.

pause
