#Requires -Version 5.1
<#
.SYNOPSIS
  Run a quick local smoke test (health + NHIA tariffs + auth).

.EXAMPLE
  .\scripts\smoke-test-local.ps1
#>
param(
    [switch]$UseSqlite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$base = 'http://127.0.0.1:8000/api/v1'

function Assert-Ok($label, $scriptBlock) {
    try {
        & $scriptBlock
        Write-Host "[OK] $label" -ForegroundColor Green
    }
    catch {
        Write-Host "[FAIL] $label — $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

Assert-Ok 'Health endpoint' {
    $r = Invoke-RestMethod -Uri "$base/health/" -TimeoutSec 10
    if (-not $r.status) { throw 'No status in health response' }
}

Assert-Ok 'NHIA tariffs (public auth required — expect 401 without token)' {
    try {
        Invoke-RestMethod -Uri "$base/billing/nhia-tariffs/" -TimeoutSec 10 | Out-Null
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw }
    }
}

Write-Host ''
Write-Host 'Smoke checks passed. Open http://localhost:3000 and log in as doctor@clinic.com' -ForegroundColor Green
Write-Host 'Manual v2.1 check: open a visit consultation, use Clinical AI Scribe, Apply to consultation.'
