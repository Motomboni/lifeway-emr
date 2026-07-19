#Requires -Version 5.1
<#
.SYNOPSIS
  Prepare local database, seed data, and verify backend before manual testing.

.EXAMPLE
  .\scripts\prepare-local.ps1
  .\scripts\prepare-local.ps1 -UseSqlite
#>
param(
    [switch]$UseSqlite,
    [switch]$ResetDb
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
    Write-Host 'Using SQLite for local prep...' -ForegroundColor Yellow
    $env:DB_ENGINE = 'django.db.backends.sqlite3'
    $env:DB_NAME = 'local_dev.sqlite3'
    Remove-Item Env:DB_USER, Env:DB_PASSWORD, Env:DB_HOST, Env:DB_PORT -ErrorAction SilentlyContinue
    $dbFile = Join-Path $backend $env:DB_NAME
    if ($ResetDb -and (Test-Path $dbFile)) {
        Write-Host "Removing existing $dbFile ..."
        Remove-Item $dbFile -Force
    }
}

function Invoke-DjangoManage {
    param([Parameter(Mandatory = $true)][string[]]$CommandArgs)
    & $python manage.py @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "manage.py $($CommandArgs -join ' ') failed (exit $LASTEXITCODE)"
    }
}

Push-Location $backend
try {
    Write-Host 'Running migrations...'
    Invoke-DjangoManage -CommandArgs @('migrate', '--noinput')

    Write-Host 'Seeding E2E / local test users...'
    Invoke-DjangoManage -CommandArgs @('seed_e2e_users')

    Write-Host 'Seeding NHIA tariff reference rows (v2.1)...'
    Invoke-DjangoManage -CommandArgs @('seed_nhia_tariffs')

    Write-Host 'Seeding lab test templates (CBC, LFT, BMP, etc.)...'
    Invoke-DjangoManage -CommandArgs @('seed_lab_templates')

    Write-Host 'Running Django system check...'
    Invoke-DjangoManage -CommandArgs @('check')

    Write-Host ''
    Write-Host 'Local backend is ready.' -ForegroundColor Green
    Write-Host '  Start API:     .\scripts\start-local-backend.ps1'
    Write-Host '  Start UI:      cd frontend; npm start'
    Write-Host ''
    Write-Host 'Test logins (seed_e2e_users):'
    Write-Host '  Doctor:        doctor@clinic.com / Doctor123!'
    Write-Host '  Receptionist:  receptionist@clinic.com / Receptionist123!'
}
finally {
    Pop-Location
}
