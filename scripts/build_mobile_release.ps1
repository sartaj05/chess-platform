param(
    [ValidateSet('apk', 'appbundle')][string]$Format = 'appbundle',
    [Parameter(Mandatory = $true)][string]$ServerUrl,
    [string]$VersionName,
    [int]$VersionCode = 0
)
$ErrorActionPreference = 'Stop'
if ($ServerUrl -match 'example\.com|REPLACE' -or -not $ServerUrl.StartsWith('https://')) {
    throw 'ServerUrl must be the real production HTTPS address.'
}
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
    if ($LASTEXITCODE -ne 0) { throw "Flutter $Format build failed." }
} finally {
    Pop-Location
}
Write-Host "Built Chess Platform $VersionName ($VersionCode) for $Format."
