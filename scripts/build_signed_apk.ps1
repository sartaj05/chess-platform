[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][SecureString]$StorePassword,
    [Parameter(Mandatory = $true)][SecureString]$KeyPassword,
    [string]$Alias = "chessplatform",
    [string]$ServerUrl = "https://chess.example.com"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Android = Join-Path $Root "mobile_app\android"
$Keystore = Join-Path $Android "app\release-keystore.jks"
$Properties = Join-Path $Android "key.properties"
$StorePlain = [Net.NetworkCredential]::new("", $StorePassword).Password
$KeyPlain = [Net.NetworkCredential]::new("", $KeyPassword).Password
$StorePassword | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $Android "store-password.dpapi")
$KeyPassword | ConvertFrom-SecureString | Set-Content -LiteralPath (Join-Path $Android "key-password.dpapi")
$Keytool = (Get-Command keytool -ErrorAction SilentlyContinue).Source
if (-not $Keytool -and $env:JAVA_HOME) { $Keytool = Join-Path $env:JAVA_HOME "bin\keytool.exe" }
if (-not $Keytool -or -not (Test-Path $Keytool)) { $Keytool = "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" }
if (-not (Test-Path $Keytool)) { throw "keytool is missing. Install Android Studio/JDK or set JAVA_HOME." }
if (-not (Test-Path $Keystore)) {
    & $Keytool -genkeypair -v -storetype JKS -keystore $Keystore -alias $Alias -keyalg RSA -keysize 4096 -validity 10000 -storepass $StorePlain -keypass $KeyPlain -dname "CN=Chess Platform, OU=Mobile, O=Chess Platform, L=Unknown, ST=Unknown, C=IN"
    if ($LASTEXITCODE -ne 0) { throw "keytool failed to create the release keystore." }
}
@("storePassword=$StorePlain", "keyPassword=$KeyPlain", "keyAlias=$Alias", "storeFile=release-keystore.jks") | Set-Content -LiteralPath $Properties
Push-Location (Join-Path $Root "mobile_app")
try {
    flutter pub get
    if ($LASTEXITCODE -ne 0) { throw "flutter pub get failed." }
    flutter build appbundle --release --dart-define="CHESS_SERVER_URL=$ServerUrl"
    if ($LASTEXITCODE -ne 0) { throw "Signed App Bundle build failed." }
    flutter build apk --release --dart-define="CHESS_SERVER_URL=$ServerUrl"
    if ($LASTEXITCODE -ne 0) { throw "Signed APK build failed." }
} finally { Pop-Location; $StorePlain = $null; $KeyPlain = $null }
Write-Host "Signed outputs created under mobile_app\build\app\outputs." -ForegroundColor Green
