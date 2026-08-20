[CmdletBinding()]
param(
    [string]$DeviceId,
    [switch]$Integration,
    [switch]$Physical
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
        if ($Physical) {
            $adbDevice = adb -s $DeviceId get-state 2>$null
            if ($LASTEXITCODE -ne 0 -or $adbDevice.Trim() -ne 'device') {
                throw "Physical Android device '$DeviceId' is not connected and authorized."
            }
            $isEmulator = adb -s $DeviceId shell getprop ro.kernel.qemu
            if ($isEmulator.Trim() -eq '1') {
                throw "Device '$DeviceId' is an emulator. Remove -Physical or connect a real phone."
            }
            $androidVersion = adb -s $DeviceId shell getprop ro.build.version.release
            $model = adb -s $DeviceId shell getprop ro.product.model
            Write-Host "Testing physical device: $model (Android $androidVersion)" -ForegroundColor Cyan
        }
        flutter test integration_test/app_test.dart -d $DeviceId --reporter expanded
        if ($LASTEXITCODE -ne 0) { throw 'Android integration tests failed.' }
    }
} finally {
    Pop-Location
}
Write-Host 'Mobile validation passed.' -ForegroundColor Green
