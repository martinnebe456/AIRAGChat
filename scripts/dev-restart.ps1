[CmdletBinding()]
param(
  [switch]$ProdLike,
  [switch]$WithOpenAI,
  [switch]$NoObservability
)

. "$PSScriptRoot/common.ps1"

& "$PSScriptRoot/dev-stop.ps1" -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI -NoObservability:$NoObservability
& "$PSScriptRoot/dev-start.ps1" -ProdLike:$ProdLike -WithOpenAI:$WithOpenAI -NoObservability:$NoObservability

