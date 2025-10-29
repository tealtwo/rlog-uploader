# PowerShell Script to Uninstall Rlog Uploader from Windows
# Run as Administrator

$ServiceName = "RlogUploader"
$TaskName = "RlogUploaderAutoStart"

Write-Host "================================================" -ForegroundColor Yellow
Write-Host "Rlog Uploader - Uninstaller" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    pause
    exit 1
}

# Check for NSSM service
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($service) {
    Write-Host ""
    Write-Host "Found NSSM service. Removing..." -ForegroundColor Yellow
    nssm stop $ServiceName
    nssm remove $ServiceName confirm
    Write-Host "Service removed!" -ForegroundColor Green
}

# Check for Scheduled Task
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($task) {
    Write-Host ""
    Write-Host "Found scheduled task. Removing..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Task removed!" -ForegroundColor Green
}

if (-not $service -and -not $task) {
    Write-Host ""
    Write-Host "No service or task found. Nothing to uninstall." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Uninstall complete!" -ForegroundColor Green
pause
