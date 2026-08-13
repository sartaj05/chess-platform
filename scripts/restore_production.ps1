param([Parameter(Mandatory=$true)][string]$DatabaseDump)
$ErrorActionPreference = "Stop"
$dump = (Resolve-Path $DatabaseDump).Path
Write-Host "Restoring $dump into the production database..."
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml cp $dump db:/tmp/chess-restore.dump
if ($LASTEXITCODE -ne 0) { throw "Copying database backup failed." }
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml exec -T db sh -c 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/chess-restore.dump'
if ($LASTEXITCODE -ne 0) { throw "Database restore failed." }
