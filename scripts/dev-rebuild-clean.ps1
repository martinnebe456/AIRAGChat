[CmdletBinding()]
param(
  [switch]$ProdLike,
  [switch]$WithOpenAI,
  [switch]$NoObservability,
  [switch]$PruneVolumes,
  [switch]$StartAfter
)

. "$PSScriptRoot/common.ps1"

Assert-DockerDesktop
Ensure-EnvFile
$composeArgs = Get-ComposeArgs -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI -Observability:(-not $NoObservability)

Write-Info "Stopping stack..."
$downArgs = @("down", "--remove-orphans")
if ($PruneVolumes) {
  $confirm = Read-Host "This will remove Docker volumes (data loss). Type YES to continue"
  if ($confirm -ne "YES") {
    throw "Volume prune cancelled."
  }
  $downArgs += "-v"
}
Invoke-Compose -ComposeArgs $composeArgs @downArgs

Write-Info "Rebuilding images without cache..."
Invoke-Compose -ComposeArgs $composeArgs -TailArgs @("build", "--no-cache")

if ($StartAfter) {
  Write-Info "Starting stack..."
  Invoke-Compose -ComposeArgs $composeArgs -TailArgs @("up", "-d")
}

Write-Info "Rebuild complete."
