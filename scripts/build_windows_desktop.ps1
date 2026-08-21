param(
    [string]$ServerUrl = "",
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FlutterProject = Join-Path $RepoRoot "mobile_app"
$BundleSource = Join-Path $FlutterProject "build\windows\x64\runner\Release"
$DistRoot = Join-Path $RepoRoot "dist\windows"
$BundleTarget = Join-Path $DistRoot "ChessPlatform-$Version"
$Archive = Join-Path $DistRoot "ChessPlatform-Windows-$Version.zip"

if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    throw "Flutter is not available in PATH. Install Flutter with Windows desktop support first."
}

Push-Location $FlutterProject
try {
    flutter config --enable-windows-desktop
    if ($LASTEXITCODE -ne 0) { throw "Unable to enable Flutter Windows desktop support." }
    flutter pub get
    if ($LASTEXITCODE -ne 0) { throw "Flutter dependency resolution failed." }
    $BuildArguments = @("build", "windows", "--release")
    if ($ServerUrl) {
        if (-not $ServerUrl.StartsWith("https://")) {
            throw "ServerUrl must use HTTPS when supplied for a distributable build."
        }
        $BuildArguments += "--dart-define=CHESS_SERVER_URL=$ServerUrl"
    }
    flutter @BuildArguments
    if ($LASTEXITCODE -ne 0) { throw "Flutter Windows release build failed." }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $BundleSource)) {
    throw "Flutter did not produce the expected Windows release bundle."
}

New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null
if (Test-Path -LiteralPath $BundleTarget) {
    Remove-Item -LiteralPath $BundleTarget -Recurse -Force
}
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
New-Item -ItemType Directory -Path $BundleTarget -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $BundleSource "data") -Destination $BundleTarget -Recurse
Copy-Item -Path (Join-Path $BundleSource "*.dll") -Destination $BundleTarget
Copy-Item -Path (Join-Path $BundleSource "*.exe") -Destination $BundleTarget
Copy-Item -LiteralPath (Join-Path $RepoRoot "desktop\README.txt") -Destination $BundleTarget
Compress-Archive -Path (Join-Path $BundleTarget "*") -DestinationPath $Archive -CompressionLevel Optimal

Write-Host "Windows desktop package created: $Archive"
Write-Host "Users can extract the ZIP and run chess_platform_mobile.exe without internet for bot and same-device games."
