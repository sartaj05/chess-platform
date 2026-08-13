[CmdletBinding()]
param([switch]$Build)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker Desktop is not installed or docker is not available in PATH." }
if (-not (Test-Path ".env.production")) { throw "Copy .env.production.example to .env.production and replace every REPLACE value first." }
$Unsafe = Select-String -Path ".env.production" -Pattern "REPLACE|example.com"
if ($Unsafe) { throw "Production environment still contains placeholder values." }
$Files = @("-f", "docker-compose.yml", "-f", "docker-compose.prod.yml")
docker compose --env-file .env.production @Files config --quiet
$UpArgs = @("compose", "--env-file", ".env.production") + $Files + @("up", "-d")
if ($Build) { $UpArgs += "--build" }
& docker @UpArgs
docker compose --env-file .env.production @Files exec -T web python manage.py migrate --noinput
docker compose --env-file .env.production @Files exec -T web python manage.py collectstatic --noinput
docker compose --env-file .env.production @Files exec -T web python manage.py check --deploy
Write-Host "Production deployment checks passed." -ForegroundColor Green
