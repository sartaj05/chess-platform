[CmdletBinding()]
param([switch]$SkipMobile)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Install Python 3.11 or newer and add it to PATH." }
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env; review its settings." -ForegroundColor Yellow }
$VenvDir = if (Test-Path ".venv\Scripts\python.exe") { ".venv" } elseif (Test-Path "venv\Scripts\python.exe") { "venv" } else { ".venv" }
if (-not (Test-Path "$VenvDir\Scripts\python.exe")) { python -m venv $VenvDir }
$Python = "$VenvDir\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python manage.py migrate
& $Python manage.py check
if (-not $SkipMobile) {
    if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) { throw "Install Flutter and Android Studio, or rerun with -SkipMobile." }
    Push-Location mobile_app
    try { flutter pub get; flutter doctor } finally { Pop-Location }
}
Write-Host "Setup complete. Run scripts\run_local.ps1 next." -ForegroundColor Green
