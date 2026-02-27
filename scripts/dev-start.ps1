[CmdletBinding()]
param(
  [switch]$ProdLike,
  [switch]$WithOpenAI,
  [switch]$NoObservability
)

. "$PSScriptRoot/common.ps1"

Assert-DockerDesktop
Ensure-EnvFile
$composeArgs = Get-ComposeArgs -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI -Observability:(-not $NoObservability)
Write-Info "Starting Docker Compose stack..."
Invoke-Compose -ComposeArgs $composeArgs -TailArgs @("up", "-d", "--remove-orphans")

Wait-Http -Url "http://localhost:8000/health/live" -Name "backend"
Wait-Http -Url "http://localhost:5173" -Name "frontend"

Write-Host ""
Write-Info "URLs"
$frontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }
$backendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
Write-Host "  Frontend:  http://localhost:$frontendPort"
Write-Host "  Backend:   http://localhost:$backendPort"
if (-not $NoObservability) {
  Write-Host "  Grafana:   http://localhost:3000"
  Write-Host "  Jaeger:    http://localhost:16686"
  Write-Host "  Prometheus:http://localhost:9090"
}
