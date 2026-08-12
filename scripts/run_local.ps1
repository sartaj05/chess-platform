[CmdletBinding()]
param([switch]$Mobile, [switch]$CheckOnly, [string]$Device = "", [string]$ServerUrl = "http://10.0.2.2:8000")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvDir = if (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe")) { ".venv" } elseif (Test-Path (Join-Path $ProjectRoot "venv\Scripts\python.exe")) { "venv" } else { "" }
if (-not $VenvDir) { throw "Run scripts\setup_windows.ps1 first." }
$Python = Join-Path $ProjectRoot "$VenvDir\Scripts\python.exe"
Set-Location $ProjectRoot
& $Python manage.py migrate
& $Python manage.py check
if ($CheckOnly) { Write-Host "Project checks completed successfully." -ForegroundColor Green; exit 0 }
if ($Mobile) {
    if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) { throw "Flutter is not available in PATH." }
    $server = Start-Process -FilePath $Python -ArgumentList "manage.py","runserver","0.0.0.0:8000","--noreload" -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden
    try {
        Push-Location (Join-Path $ProjectRoot "mobile_app")
        $flutterArgs = @("run", "--dart-define=CHESS_SERVER_URL=$ServerUrl")
        if ($Device) { $flutterArgs += @("-d", $Device) }
        & flutter @flutterArgs
    } finally { Pop-Location; if (-not $server.HasExited) { Stop-Process -Id $server.Id } }
} else {
    Write-Host "Website: http://127.0.0.1:8000" -ForegroundColor Green
    & $Python manage.py runserver 0.0.0.0:8000
}
