@echo off
REM View Rlog Uploader logs
echo Viewing logs from data directory...
echo Press Ctrl+C to stop watching
echo.

if exist "data\rlog_monitor.log" (
    powershell -Command "Get-Content data\rlog_monitor.log -Tail 50 -Wait"
) else (
    echo No log file found yet. Service may not have started.
    echo Log location: data\rlog_monitor.log
)

pause
