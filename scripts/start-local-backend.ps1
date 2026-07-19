#Requires -Version 5.1
<#
.SYNOPSIS
  Start Django dev server on http://127.0.0.1:8000

.EXAMPLE
  .\scripts\start-local-backend.ps1
  .\scripts\start-local-backend.ps1 -UseSqlite
#>
param(
    [switch]$UseSqlite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "Missing backend/.venv — run scripts/setup-backend-venv.ps1 first."
}

if (-not $env:SECRET_KEY) { $env:SECRET_KEY = 'local-dev-secret-key' }
if (-not $env:DEBUG) { $env:DEBUG = 'True' }
$env:ENFORCE_PLAN_LIMITS = 'false'
$env:REQUIRE_ORGANIZATION_CONTEXT = 'false'
$env:E2E_OTP_EXPOSE = 'true'

if ($UseSqlite) {
    $env:DB_ENGINE = 'django.db.backends.sqlite3'
    $env:DB_NAME = 'local_dev.sqlite3'
    Remove-Item Env:DB_USER, Env:DB_PASSWORD, Env:DB_HOST, Env:DB_PORT -ErrorAction SilentlyContinue
} else {
    # Ensure .env postgres/sqlite settings apply; do not inherit stale test overrides.
    Remove-Item Env:DB_ENGINE, Env:DB_NAME, Env:DB_USER, Env:DB_PASSWORD, Env:DB_HOST, Env:DB_PORT -ErrorAction SilentlyContinue
}

Push-Location $backend
try {
    Write-Host 'Starting Django at http://127.0.0.1:8000 ...' -ForegroundColor Cyan
    & $python manage.py runserver 127.0.0.1:8000
}
finally {
    Pop-Location
}
