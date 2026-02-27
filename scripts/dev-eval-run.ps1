[CmdletBinding()]
param(
  [string]$BaseUrl = "http://localhost:8000/api/v1",
  [string]$Username = "admin",
  [string]$Password = "ChangeMe123!"
)

. "$PSScriptRoot/common.ps1"

Write-Info "Logging in as admin..."
$loginBody = @{
  username_or_email = $Username
  password = $Password
} | ConvertTo-Json

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginResp = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -WebSession $session
$token = $loginResp.access_token
if (-not $token) { throw "Login failed: no access token returned." }

$headers = @{ Authorization = "Bearer $token" }

Write-Info "Triggering sample evaluation run..."
$runBody = @{
  dataset_id = "sample-default"
  provider = "openai_api"
  model_category = "medium"
} | ConvertTo-Json

$runResp = Invoke-RestMethod -Uri "$BaseUrl/evals/runs" -Method Post -ContentType "application/json" -Body $runBody -Headers $headers
$runId = $runResp.id
if (-not $runId) { throw "Eval run creation failed." }

Write-Info "Run ID: $runId"
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 2
  $status = Invoke-RestMethod -Uri "$BaseUrl/evals/runs/$runId" -Headers $headers
  Write-Host "  status: $($status.status)"
  if ($status.status -in @("completed", "failed", "cancelled")) {
    if ($status.status -eq "completed") {
      $details = Invoke-RestMethod -Uri "$BaseUrl/evals/runs/$runId" -Headers $headers
      Write-Info "Eval completed."
      $details | ConvertTo-Json -Depth 8
      return
    }
    throw "Eval run ended with status: $($status.status)"
  }
}

throw "Eval run polling timed out."
