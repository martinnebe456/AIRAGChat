[CmdletBinding()]
param(
  [switch]$ProdLike,
  [switch]$WithOpenAI
)

. "$PSScriptRoot/common.ps1"

Assert-DockerDesktop
Ensure-EnvFile
$composeArgs = Get-ComposeArgs -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI
Write-Info "Building Docker images..."
Invoke-Compose -ComposeArgs $composeArgs -TailArgs @("build")
Write-Info "Build completed."
Write-Host ""
Write-Info "Next steps:"
Write-Host "  ./scripts/dev-start.ps1"
Write-Host "  ./scripts/dev-health.ps1"
