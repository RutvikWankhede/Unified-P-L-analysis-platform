# start.ps1 - Unified P&L Intelligence Platform Launcher
Write-Host ""
Write-Host " ==========================================================" -ForegroundColor Cyan
Write-Host "   Unified P&L Intelligence — Starting All Services..." -ForegroundColor Cyan
Write-Host " ==========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Find Python
$Python = "python"
$VenvPython = Join-Path $ScriptDir "unified-pl-system\venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
}

Write-Host " [*] Using Python: $Python" -ForegroundColor Gray
Write-Host " [*] Starting platform from: $ScriptDir" -ForegroundColor Gray
Write-Host ""

Set-Location $ScriptDir
& $Python run.py
