param(
    [ValidateSet('apk', 'appbundle')][string]$Format = 'appbundle',
    [Parameter(Mandatory = $true)][string]$ServerUrl,
    [string]$VersionName,
    [int]$VersionCode = 0
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$mobileRoot = Join-Path $repoRoot 'mobile_app'
if (-not $VersionName) {
    $VersionName = ((git -C $repoRoot describe --tags --always) -replace '^v','' -replace '-','.')
}
if ($VersionCode -le 0) {
    $VersionCode = [int](git -C $repoRoot rev-list --count HEAD)
}
Push-Location $mobileRoot
try {
    flutter pub get
    flutter build $Format --release "--build-name=$VersionName" "--build-number=$VersionCode" "--dart-define=CHESS_SERVER_URL=$ServerUrl"
} finally {
    Pop-Location
}
Write-Host "Built Chess Platform $VersionName ($VersionCode) for $Format."
