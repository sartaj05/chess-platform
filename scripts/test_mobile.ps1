[CmdletBinding()]
param(
    [string]$DeviceId,
    [switch]$Integration
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$mobileRoot = Join-Path $repoRoot 'mobile_app'
Push-Location $mobileRoot
try {
    flutter pub get
    if ($LASTEXITCODE -ne 0) { throw 'flutter pub get failed.' }
    flutter analyze
    if ($LASTEXITCODE -ne 0) { throw 'flutter analyze failed.' }
    flutter test --concurrency=1 --reporter expanded
    if ($LASTEXITCODE -ne 0) { throw 'Flutter unit tests failed.' }
    if ($Integration) {
        if (-not $DeviceId) {
            throw 'Pass -DeviceId with an emulator or physical Android device.'
        }
        flutter test integration_test/app_test.dart -d $DeviceId
        if ($LASTEXITCODE -ne 0) { throw 'Android integration tests failed.' }
    }
} finally {
    Pop-Location
}
Write-Host 'Mobile validation passed.' -ForegroundColor Green
