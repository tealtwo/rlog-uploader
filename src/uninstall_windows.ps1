# PowerShell Script to Uninstall Rlog Uploader from Windows
# Run as Administrator

$ServiceName = "RlogUploader"
$TaskName = "RlogUploaderAutoStart"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WinSWExe = Join-Path $ScriptDir "RlogUploader.exe"

Write-Host "================================================" -ForegroundColor Yellow
Write-Host "Rlog Uploader - Uninstaller" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    pause
    exit 1
}

$found = $false

# Check for WinSW service
if (Test-Path $WinSWExe) {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host ""
        Write-Host "Found WinSW service. Removing..." -ForegroundColor Yellow
        & $WinSWExe stop
        & $WinSWExe uninstall
        Write-Host "WinSW service removed!" -ForegroundColor Green
        $found = $true
    }
}

# Check for NSSM service
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    Write-Host ""
    Write-Host "Found NSSM service. Removing..." -ForegroundColor Yellow
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
    if ($nssmPath) {
        nssm stop $ServiceName
        nssm remove $ServiceName confirm
        Write-Host "NSSM service removed!" -ForegroundColor Green
        $found = $true
    } else {
        Write-Host "NSSM not found. Please uninstall manually via Services" -ForegroundColor Yellow
    }
}

# Check for Scheduled Task
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host ""
    Write-Host "Found scheduled task. Removing..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Task removed!" -ForegroundColor Green
    $found = $true
}

if (-not $found) {
    Write-Host ""
    Write-Host "No service or task found. Nothing to uninstall." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Uninstall complete!" -ForegroundColor Green
pause
