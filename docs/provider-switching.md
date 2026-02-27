# Provider Configuration

## Runtime Mode

The application runs in `openai_api` mode only.

## Models (Admin-facing)

Admins configure OpenAI model IDs for:

- chat inference
- document/query embeddings
- optional evaluation judge model

## Data Model

- active provider: `provider_settings.active_provider` (fixed to `openai_api`)
- model defaults: `system_settings` (`namespace=models`, `key=defaults`)
- OpenAI key metadata: `provider_settings.openai_config_meta_json`
- encrypted secret payload: `secrets_store`

## Configuration Rules

- OpenAI-backed features are blocked if no stored key exists
- backend resolves configured model IDs at runtime
- response metadata persists actual provider/model used

## Security Constraints

- OpenAI key is submitted to backend only
- browser never calls OpenAI directly
- key is encrypted at rest and masked in UI after save

## Audit Logging

Audit events should be recorded for:

- model settings changes
- OpenAI key set/test/rotate/delete
