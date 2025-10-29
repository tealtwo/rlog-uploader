# Modern Windows Service installer using WinSW
# WinSW is actively maintained and used by Jenkins
# Run as Administrator

param(
    [Parameter(Mandatory=$false)]
    [string]$Port = "3445"
)

$ServiceName = "RlogUploader"
$DisplayName = "Comma 3X Rlog Auto-Uploader"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python).Source
$ScriptPath = Join-Path $ScriptDir "extract_web_server_rlogs.py"

Write-Host "================================================" -ForegroundColor Green
Write-Host "Rlog Uploader - Modern Windows Service Installer" -ForegroundColor Green
Write-Host "Using WinSW (Windows Service Wrapper)" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Service Name: $ServiceName" -ForegroundColor White
Write-Host "  Port: $Port" -ForegroundColor White
Write-Host "  Python: $PythonExe" -ForegroundColor White
Write-Host "  Script: $ScriptPath" -ForegroundColor White

$WinSWVersion = "3.0.0-alpha.11"
$WinSWUrl = "https://github.com/winsw/winsw/releases/download/v$WinSWVersion/WinSW-x64.exe"
$WinSWPath = Join-Path $ScriptDir "RlogUploader.exe"
$WinSWConfig = Join-Path $ScriptDir "RlogUploader.xml"

if (-not (Test-Path $WinSWPath)) {
    Write-Host ""
    Write-Host "Downloading WinSW..." -ForegroundColor Cyan

    try {
        Invoke-WebRequest -Uri $WinSWUrl -OutFile $WinSWPath -UseBasicParsing
        Write-Host "✓ WinSW downloaded successfully" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to download WinSW: $_" -ForegroundColor Red
        Write-Host "Please download manually from: $WinSWUrl" -ForegroundColor Yellow
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "Creating service configuration..." -ForegroundColor Cyan

$ConfigXml = @"
<service>
  <id>$ServiceName</id>
  <name>$DisplayName</name>
  <description>Automatically monitors Comma 3X and uploads rlogs to FileBrowser server</description>
  <executable>$PythonExe</executable>
  <arguments>"$ScriptPath"</arguments>
  <workingdirectory>$ScriptDir</workingdirectory>
  <env name="PORT" value="$Port"/>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>8</keepFiles>
  </log>
  <onfailure action="restart" delay="10 sec"/>
  <onfailure action="restart" delay="20 sec"/>
  <onfailure action="restart" delay="30 sec"/>
  <resetfailure>1 hour</resetfailure>
</service>
"@

$ConfigXml | Out-File -FilePath $WinSWConfig -Encoding UTF8

$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host ""
    Write-Host "Service already exists. Removing old service..." -ForegroundColor Yellow
    & $WinSWPath stop
    Start-Sleep -Seconds 2
    & $WinSWPath uninstall
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "Installing service..." -ForegroundColor Cyan
& $WinSWPath install

Write-Host ""
Write-Host "Starting service..." -ForegroundColor Cyan
& $WinSWPath start

Start-Sleep -Seconds 3

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($service -and $service.Status -eq 'Running') {
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
    Write-Host "  Stop Service: .\RlogUploader.exe stop" -ForegroundColor White
    Write-Host "  Start Service: .\RlogUploader.exe start" -ForegroundColor White
    Write-Host "  View Logs: Get-Content RlogUploader.out.log -Tail 50 -Wait" -ForegroundColor White
    Write-Host "  Uninstall: .\RlogUploader.exe uninstall" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "WARNING: Service installed but not running!" -ForegroundColor Yellow
    if ($service) {
        Write-Host "Status: $($service.Status)" -ForegroundColor Red
    }
    Write-Host "Check logs: Get-Content RlogUploader.out.log" -ForegroundColor Yellow
}

Write-Host ""
pause
