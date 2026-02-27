# Secrets Management

## Scope

This project currently manages external provider credentials, primarily:

- OpenAI API key (admin-managed)

## Security Design

- Frontend submits secrets only to backend admin endpoints
- Browser never stores secrets in localStorage/sessionStorage
- Backend encrypts secrets at rest before database persistence
- Backend returns masked previews only
- External provider calls are made server-side only

## Encryption

- Mechanism: `cryptography.Fernet`
- Master key source: `APP_SECRETS_MASTER_KEY`
- Storage:
  - encrypted payload in `secrets_store.ciphertext`
  - masked preview and rotation metadata in DB

## Rotation

The admin workflow supports explicit key rotation by replacing the stored OpenAI key via:

- `POST /api/v1/admin/providers/openai/key/rotate`

This updates rotation metadata and should emit an audit log event.

## Logging Safety

Avoid logging:

- raw API keys
- passwords
- JWTs
- refresh tokens

Current code uses structured logging and should be extended with centralized redaction as the project hardens.

