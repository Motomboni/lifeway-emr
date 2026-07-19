#Requires -Version 5.1
<#
.SYNOPSIS
  Run backend pytest with SQLite (CI-compatible settings).

.EXAMPLE
  .\scripts\run-backend-tests.ps1
  .\scripts\run-backend-tests.ps1 tests/test_nhia_scribe_validation.py -q
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "Missing $python — run scripts/setup-backend-venv.ps1 first."
}

# Set before Django loads so load_env.py does not override (see load_env.py).
$env:DEBUG = 'True'
$env:SECRET_KEY = 'local-test-secret-key-not-for-production'
$env:ENFORCE_PLAN_LIMITS = 'false'
$env:REQUIRE_ORGANIZATION_CONTEXT = 'false'
$env:DB_ENGINE = 'django.db.backends.sqlite3'
$env:DB_NAME = 'local_pytest.sqlite3'

Push-Location $backend
try {
    if ($args.Count -eq 0) {
        & $python -m pytest --tb=short --strict-markers -o addopts="--tb=short --strict-markers --create-db"
    }
    else {
        & $python -m pytest @args
    }
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
