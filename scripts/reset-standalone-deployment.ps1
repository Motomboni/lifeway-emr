# Reset Postgres volume and redeploy standalone stack (DESTROYS ALL DB DATA).
# Usage (repo root, PowerShell): .\scripts\reset-standalone-deployment.ps1
# Requires: Docker, docker compose v2, .env with DB_PASSWORD and SECRET_KEY (see .env.prod.example)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root "docker-compose.standalone.yml"))) {
    Write-Error "Run this script from the repo (expected docker-compose.standalone.yml in $root)."
    exit 1
}
Set-Location $root

Write-Host "This will remove volume postgres_data and rebuild the app image." -ForegroundColor Yellow
Write-Host "ALL DATABASE DATA FOR THIS COMPOSE PROJECT WILL BE LOST." -ForegroundColor Red
$confirm = Read-Host "Type YES to continue"
if ($confirm -ne "YES") { Write-Host "Aborted."; exit 1 }

docker compose -f docker-compose.standalone.yml down -v --remove-orphans
docker compose -f docker-compose.standalone.yml build --no-cache app
docker compose -f docker-compose.standalone.yml up -d

Write-Host "Done. App: http://localhost:8080 (wait for healthcheck). Migrations run in container start.sh." -ForegroundColor Green
