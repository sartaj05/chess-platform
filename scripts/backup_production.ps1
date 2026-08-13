param([string]$Destination = ".\backups")
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$target = [IO.Path]::GetFullPath((Join-Path $root $Destination))
if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw "Backup destination must be inside the project." }
New-Item -ItemType Directory -Force -Path $target | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$database = Join-Path $target "database-$stamp.dump"
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" -f /tmp/chess-backup.dump'
if ($LASTEXITCODE -ne 0) { throw "Database backup failed." }
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml cp db:/tmp/chess-backup.dump $database
if ($LASTEXITCODE -ne 0) { throw "Copying database backup failed." }
docker run --rm -v chess_platform_repo_media_volume:/source:ro -v "${target}:/backup" alpine tar czf "/backup/media-$stamp.tar.gz" -C /source .
if ($LASTEXITCODE -ne 0) { throw "Media backup failed." }
Get-FileHash -Algorithm SHA256 $database, (Join-Path $target "media-$stamp.tar.gz") | Format-Table
