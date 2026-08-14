$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$assets = @(
    @{ Url = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css'; Path = 'static/vendor/bootstrap/bootstrap.min.css' },
    @{ Url = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js'; Path = 'static/vendor/bootstrap/bootstrap.bundle.min.js' },
    @{ Url = 'https://unpkg.com/htmx.org@2.0.7/dist/htmx.min.js'; Path = 'static/vendor/htmx/htmx.min.js' },
    @{ Url = 'https://unpkg.com/alpinejs@3.14.9/dist/cdn.min.js'; Path = 'static/vendor/alpine/alpine.min.js' }
)
foreach ($asset in $assets) {
    $destination = Join-Path $repoRoot $asset.Path
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    if (-not (Test-Path $destination) -or (Get-Item $destination).Length -eq 0) {
        Invoke-WebRequest -Uri $asset.Url -OutFile $destination
    }
}
Write-Host 'Frontend vendor assets are ready.'
