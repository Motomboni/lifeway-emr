#Requires -Version 5.1
<#
.SYNOPSIS
  Create backend/.venv with Python 3.11 (via uv) and install requirements.

.DESCRIPTION
  MSYS/Git Bash python often lacks pip and is not CI-compatible. This script
  uses uv to install CPython 3.11 and a Windows venv under backend/.venv.

.EXAMPLE
  .\scripts\setup-backend-venv.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'backend'
$uvLocal = Join-Path $env:USERPROFILE '.local\bin\uv.exe'

if (-not (Test-Path $uvLocal)) {
    Write-Host 'Installing uv...'
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}

$env:Path = "$(Split-Path $uvLocal -Parent);$env:Path"

Push-Location $backend
try {
    Write-Host 'Installing Python 3.11 (if needed)...'
    & uv python install 3.11

    if (Test-Path '.venv') {
        Write-Host 'Removing existing .venv...'
        Remove-Item -Recurse -Force '.venv'
    }

    Write-Host 'Creating virtual environment...'
    & uv venv --python 3.11 .venv

    Write-Host 'Installing requirements...'
    & uv pip install -r requirements.txt

    Write-Host ''
    Write-Host 'Backend venv ready.' -ForegroundColor Green
    Write-Host "  Activate:  .\.venv\Scripts\Activate.ps1"
    Write-Host "  Tests:     ..\scripts\run-backend-tests.ps1"
}
finally {
    Pop-Location
}
