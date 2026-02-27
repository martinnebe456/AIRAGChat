[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

Write-WarnMsg "This project is now OpenAI-only. Local model setup via Ollama was removed."
Write-Info "Use Admin -> System Settings to configure OpenAI key, chat model, and embedding model."
