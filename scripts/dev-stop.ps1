[CmdletBinding()]
param(
  [switch]$ProdLike,
  [switch]$WithOpenAI,
  [switch]$NoObservability,
  [switch]$RemoveOrphans
)

. "$PSScriptRoot/common.ps1"

Assert-DockerDesktop
$composeArgs = Get-ComposeArgs -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI -Observability:(-not $NoObservability)
$args = @("down")
if ($RemoveOrphans) { $args += "--remove-orphans" }
Write-Info "Stopping Docker Compose stack..."
Invoke-Compose -ComposeArgs $composeArgs @args
Write-Info "Stopped."

