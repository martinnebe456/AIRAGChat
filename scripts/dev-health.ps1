[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

function Test-HttpUrl {
  param(
    [string]$Url,
    [int]$Retries = 5,
    [int]$DelaySeconds = 2
  )

  for ($i = 0; $i -lt $Retries; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) {
        return $true
      }
    } catch {
      # Retry transient startup failures.
    }
    Start-Sleep -Seconds $DelaySeconds
  }

  return $false
}

$checks = @(
  @{ Name = "Backend live"; Url = "http://localhost:8000/health/live"; Retries = 3 },
  @{ Name = "Backend ready"; Url = "http://localhost:8000/health/ready"; Retries = 3 },
  @{ Name = "Frontend"; Url = "http://localhost:5173"; Retries = 3 },
  @{ Name = "Qdrant"; Url = "http://localhost:6333/healthz"; Retries = 3 },
  @{ Name = "Grafana"; Url = "http://localhost:3000/api/health"; Retries = 5 },
  @{ Name = "Jaeger"; Url = "http://localhost:16686"; Retries = 5 },
  @{ Name = "Prometheus"; Url = "http://localhost:9090/-/healthy"; Retries = 5 },
  # /ready can be briefly unavailable while single-binary Loki rings settle.
  @{ Name = "Loki"; Url = "http://localhost:3100/ready"; Retries = 10; DelaySeconds = 2 }
)

$failed = @()
foreach ($c in $checks) {
  $retries = if ($c.ContainsKey("Retries")) { [int]$c.Retries } else { 5 }
  $delay = if ($c.ContainsKey("DelaySeconds")) { [int]$c.DelaySeconds } else { 2 }
  $ok = Test-HttpUrl -Url $c.Url -Retries $retries -DelaySeconds $delay

  if ($ok) {
    Write-Host ("[OK]   {0,-14} {1}" -f $c.Name, $c.Url) -ForegroundColor Green
    continue
  }

  Write-Host ("[FAIL] {0,-14} {1}" -f $c.Name, $c.Url) -ForegroundColor Red
  $failed += $c.Name
}

if ($failed.Count -gt 0) {
  throw "Health checks failed: $($failed -join ', ')"
}

Write-Info "All health checks passed."
