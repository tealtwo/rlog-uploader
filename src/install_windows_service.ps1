# PowerShell Script to Install Rlog Uploader as Windows Service
# Run as Administrator

param(
    [Parameter(Mandatory=$false)]
    [string]$Port = "3445"
)

$ServiceName = "RlogUploader"
$DisplayName = "Comma 3X Rlog Auto-Uploader"
$Description = "Automatically monitors Comma 3X and uploads rlogs to FileBrowser server"

# Get the current script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Path to Python executable and script
$PythonExe = (Get-Command python).Source
$ScriptPath = Join-Path $ScriptDir "extract_web_server_rlogs.py"

Write-Host "================================================" -ForegroundColor Green
Write-Host "Rlog Uploader - Windows Service Installer" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if NSSM is installed
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue

if (-not $nssmPath) {
    Write-Host ""
    Write-Host "NSSM (Non-Sucking Service Manager) not found!" -ForegroundColor Yellow
    Write-Host "Installing NSSM via Chocolatey..." -ForegroundColor Cyan

    # Check if Chocolatey is installed
    $chocoPath = Get-Command choco -ErrorAction SilentlyContinue

    if (-not $chocoPath) {
        Write-Host "Installing Chocolatey first..." -ForegroundColor Cyan
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }

    choco install nssm -y
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue

    if (-not $nssmPath) {
        Write-Host "ERROR: Failed to install NSSM" -ForegroundColor Red
        Write-Host "Please install NSSM manually: https://nssm.cc/download" -ForegroundColor Yellow
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Service Name: $ServiceName" -ForegroundColor White
Write-Host "  Display Name: $DisplayName" -ForegroundColor White
Write-Host "  Port: $Port" -ForegroundColor White
Write-Host "  Python: $PythonExe" -ForegroundColor White
Write-Host "  Script: $ScriptPath" -ForegroundColor White

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($existingService) {
    Write-Host ""
    Write-Host "Service already exists. Removing old service..." -ForegroundColor Yellow
    nssm stop $ServiceName
    nssm remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Install the service
Write-Host ""
Write-Host "Installing service..." -ForegroundColor Cyan

nssm install $ServiceName $PythonExe $ScriptPath
nssm set $ServiceName AppDirectory $ScriptDir
nssm set $ServiceName DisplayName "$DisplayName"
nssm set $ServiceName Description "$Description"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout "$ScriptDir\service.log"
nssm set $ServiceName AppStderr "$ScriptDir\service.log"

# Set environment variable for port
nssm set $ServiceName AppEnvironmentExtra "PORT=$Port"

# Configure restart behavior
nssm set $ServiceName AppExit Default Restart
nssm set $ServiceName AppRestartDelay 5000

Write-Host ""
Write-Host "Starting service..." -ForegroundColor Cyan
nssm start $ServiceName

Start-Sleep -Seconds 3

# Check service status
$service = Get-Service -Name $ServiceName

if ($service.Status -eq 'Running') {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "SUCCESS! Service installed and running!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Web Interface: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host "Service Status: $($service.Status)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Yellow
    Write-Host "  View Status:  Get-Service $ServiceName" -ForegroundColor White
    Write-Host "  Stop Service: nssm stop $ServiceName" -ForegroundColor White
    Write-Host "  Start Service: nssm start $ServiceName" -ForegroundColor White
    Write-Host "  Remove Service: nssm remove $ServiceName confirm" -ForegroundColor White
    Write-Host "  View Logs: Get-Content '$ScriptDir\service.log' -Tail 50 -Wait" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "WARNING: Service installed but not running!" -ForegroundColor Yellow
    Write-Host "Status: $($service.Status)" -ForegroundColor Red
    Write-Host "Check logs at: $ScriptDir\service.log" -ForegroundColor Yellow
}

Write-Host ""
pause
