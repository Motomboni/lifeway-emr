# Start self-hosted LiveKit for EMR telemedicine
Set-Location $PSScriptRoot\..

Write-Host "Starting LiveKit (dev config: infra/livekit/livekit.dev.yaml)..." -ForegroundColor Cyan
docker compose -f docker-compose.livekit.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "LiveKit WebSocket: ws://localhost:7880" -ForegroundColor Green
    Write-Host "Dev API key:       devkey" -ForegroundColor Green
    Write-Host "Dev API secret:    secret" -ForegroundColor Green
    Write-Host ""
    Write-Host "Set in .env:" -ForegroundColor Yellow
    Write-Host "  TELEMEDICINE_VIDEO_PROVIDER=livekit"
    Write-Host "  LIVEKIT_URL=ws://localhost:7880"
    Write-Host "  LIVEKIT_API_KEY=devkey"
    Write-Host "  LIVEKIT_API_SECRET=secret"
}
