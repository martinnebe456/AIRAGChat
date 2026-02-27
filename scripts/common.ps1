Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info {
  param([string]$Message)
  Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-WarnMsg {
  param([string]$Message)
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrMsg {
  param([string]$Message)
  Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Get-RepoRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-ComposeArgs {
  param(
    [switch]$ProdLike,
    [switch]$WithOpenAI,
    [switch]$Observability = $true
  )

  $repo = Get-RepoRoot
  $composeFile = Join-Path $repo "infra/compose/compose.yaml"
  $args = @("compose", "-f", $composeFile)
  if ($ProdLike) {
    $prodFile = Join-Path $repo "infra/compose/compose.prod-like.yaml"
    $args += @("-f", $prodFile)
  }
  if ($Observability) {
    $args += @("--profile", "observability")
  }
  # `with-openai` is implemented as env/runtime config, not a separate service profile.
  if ($WithOpenAI) {
    $env:OPENAI_ENABLED = "true"
  }
  return $args
}

function Assert-DockerDesktop {
  Write-Info "Checking Docker availability..."
  docker version | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Docker CLI is not available or Docker Desktop is not running." }
  docker info | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Docker daemon is not reachable. Start Docker Desktop and try again." }
}

function Ensure-EnvFile {
  $repo = Get-RepoRoot
  $envPath = Join-Path $repo ".env"
  $envExample = Join-Path $repo ".env.example"
  if (-not (Test-Path $envPath)) {
    Write-WarnMsg ".env not found. Creating it from .env.example"
    Copy-Item $envExample $envPath
  }

  $envContent = Get-Content $envPath -Raw
  $updated = $false
  if ($envContent -match "PROVIDER_ACTIVE=llama_stack_local") {
    $envContent = $envContent -replace "PROVIDER_ACTIVE=llama_stack_local", "PROVIDER_ACTIVE=openai_api"
    $updated = $true
  }
  if ($envContent -notmatch "(?m)^OPENAI_ENABLED=") {
    $envContent = $envContent.TrimEnd() + "`r`nOPENAI_ENABLED=true`r`n"
    $updated = $true
  }
  if ($updated) {
    Write-WarnMsg "Updating .env for OpenAI-only runtime defaults."
    Set-Content -Path $envPath -Value $envContent
  }
}

function Invoke-Compose {
  param(
    [string[]]$ComposeArgs,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TailArgs
  )
  docker @ComposeArgs @TailArgs
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed with exit code $LASTEXITCODE"
  }
}

function Wait-Http {
  param(
    [string]$Url,
    [int]$Retries = 30,
    [int]$DelaySeconds = 2,
    [string]$Name = "service"
  )
  for ($i = 0; $i -lt $Retries; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        Write-Info "$Name is reachable at $Url"
        return
      }
    } catch {
      Start-Sleep -Seconds $DelaySeconds
    }
  }
  throw "$Name did not become reachable: $Url"
}
