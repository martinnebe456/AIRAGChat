[CmdletBinding()]
param(
  [switch]$ProdLike,
  [switch]$WithOpenAI,
  [switch]$NoObservability,
  [string]$Service,
  [string]$Since = "10m"
)

. "$PSScriptRoot/common.ps1"

$composeArgs = Get-ComposeArgs -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI -Observability:(-not $NoObservability)
$tailArgs = @("logs", "-f", "--since", $Since)
if ($Service) { $tailArgs += $Service }
Invoke-Compose -ComposeArgs $composeArgs @tailArgs

