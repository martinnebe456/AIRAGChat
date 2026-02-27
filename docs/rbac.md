# RBAC

## Roles

### User

- Login
- Ask questions over processed documents
- View chat sessions/messages (when enabled)
- Read-only document list (current UI implementation)

### Contributor

Includes `User` permissions plus:

- Upload documents
- Reprocess documents
- Delete/manage own documents (subject to backend authorization)
- View ingestion job status/logs

### Admin

Includes `Contributor` permissions plus:

- User management (create/update/activate/deactivate/reset password)
- Manage provider switching and model category mappings
- Manage OpenAI API key (set/test/rotate/remove)
- Configure RAG/prompt/eval/telemetry settings
- Run evaluations and compare runs

## Enforcement

RBAC is enforced in two places:

- Backend route dependencies (`require_roles`) are authoritative
- Frontend route guards improve UX but do not replace backend checks

## Auth Model

- Access token: JWT (short-lived), stored in frontend memory only
- Refresh token: opaque token in HttpOnly cookie
- Deactivated users cannot authenticate or refresh

## Audit Expectations

Admin actions should generate audit logs, especially:

- user creation/role changes/password reset
- provider switch and model mapping changes
- secret management operations
- document deletion
- eval run execution

