#Requires -Version 5.1
<#
.SYNOPSIS
  Verify self-hosted LiveKit configuration and server connectivity.

.EXAMPLE
  .\scripts\check-livekit.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'backend'

function Resolve-BackendPython {
    $candidates = @(
        (Join-Path $backend '.venv\Scripts\python.exe'),
        (Join-Path $repoRoot '.venv\Scripts\python.exe')
    )
    if ($env:VIRTUAL_ENV) {
        $active = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
        $candidates = @($active) + $candidates
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    $pathPython = Get-Command python -ErrorAction SilentlyContinue
    if ($pathPython) {
        return $pathPython.Source
    }
    Write-Error "No Python found. Run scripts/setup-backend-venv.ps1 or activate .venv first."
}

$python = Resolve-BackendPython
Write-Host "Using Python: $python" -ForegroundColor DarkGray

Push-Location $backend
try {
    & $python manage.py check_livekit
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
