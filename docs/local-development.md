# Local Development

## Prerequisites

- Docker Desktop
- PowerShell

## Start the Stack

```powershell
./scripts/dev-build.ps1
./scripts/dev-start.ps1
./scripts/dev-health.ps1
```

## Stop / Restart

```powershell
./scripts/dev-stop.ps1
./scripts/dev-restart.ps1
```

## Logs

```powershell
./scripts/dev-logs.ps1
./scripts/dev-logs.ps1 -Service backend
```

## OpenAI Setup

Configure the OpenAI key in `Admin -> System Settings` after startup.
`./scripts/dev-setup-models.ps1` is retained only as a compatibility stub and no longer installs local models.

## Local URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`

## Default Login

- Username: `admin`
- Password: `ChangeMe123!`

Configured from `.env` bootstrap variables.

## Notes

- The app is designed for local orchestration with OpenAI as the inference/embedding runtime.
- Promtail host log collection may require Windows-specific mount/profile tuning.
