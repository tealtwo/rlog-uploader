@echo off
echo Stopping Rlog Uploader service...

REM Stop the scheduled task
schtasks /End /TN "RlogUploaderAutoStart" 2>nul

REM Kill any running Python processes for this script
for /f "tokens=2" %%i in ('tasklist ^| findstr /i "python"') do (
    wmic process where "ProcessId=%%i and CommandLine like '%%extract_web_server_rlogs%%'" delete 2>nul
)

echo.
echo Service stopped!
echo.
pause
