# PowerShell Script to Install Rlog Uploader as Windows Scheduled Task
# Run as Administrator
# Alternative to NSSM - uses Windows Task Scheduler

param(
    [Parameter(Mandatory=$false)]
    [string]$Port = "3445"
)

$TaskName = "RlogUploaderAutoStart"
$Description = "Automatically monitors Comma 3X and uploads rlogs to FileBrowser server"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VBSFile = Join-Path $ScriptDir "start_rlog_uploader_hidden.vbs"

Write-Host "================================================" -ForegroundColor Green
Write-Host "Rlog Uploader - Task Scheduler Installer" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Task Name: $TaskName" -ForegroundColor White
Write-Host "  Port: $Port" -ForegroundColor White
Write-Host "  VBS Launcher: $VBSFile" -ForegroundColor White

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host ""
    Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Start-Sleep -Seconds 2
}

# Create the action
Write-Host ""
Write-Host "Creating scheduled task..." -ForegroundColor Cyan

$Action = New-ScheduledTaskAction -Execute "wscript.exe" `
    -Argument "`"$VBSFile`"" `
    -WorkingDirectory $ScriptDir

# Create the trigger (at startup)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Get current user
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description | Out-Null

Write-Host ""
Write-Host "Starting task..." -ForegroundColor Cyan

# Start the task immediately
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 3

# Check task status
$task = Get-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "SUCCESS! Task installed!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Web Interface: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Task Status: $($task.State)" -ForegroundColor Green
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  View Status:  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor White
Write-Host "  Stop Task: Stop-ScheduledTask -TaskName $TaskName" -ForegroundColor White
Write-Host "  Start Task: Start-ScheduledTask -TaskName $TaskName" -ForegroundColor White
Write-Host "  Remove Task: Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor White
Write-Host ""
Write-Host "NOTE: Task will auto-start on Windows boot" -ForegroundColor Cyan
Write-Host "NOTE: Set PORT environment variable before running to change port" -ForegroundColor Cyan
Write-Host ""
pause
