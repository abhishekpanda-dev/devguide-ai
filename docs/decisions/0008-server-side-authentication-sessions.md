# 0008 — Server-side authentication sessions

## Status

Accepted.

## Decision

DevGuide AI authenticates local users with normalized email addresses and PBKDF2-HMAC-SHA256
password hashes using unique salts and 600,000 iterations. Successful registration or login
creates a cryptographically random opaque token. Only its SHA-256 digest is persisted; the raw
token is sent in an HTTP-only, SameSite=Lax cookie and is never exposed to frontend JavaScript.

Repository visibility is granted through `user_repository_access`. Repository and analysis
routes check this server-side relationship and return ordinary not-found errors across ownership
boundaries. Public health/readiness and authentication endpoints remain outside that guard.

## Consequences

- Production deployments must enable `DEVGUIDE_AUTH_COOKIE_SECURE` behind HTTPS.
- Sessions are revocable and have a bounded server-configured lifetime.
- Password reset, OAuth, teams, invitations, and persistent “remember me” behavior remain out of
  scope.
- Existing repositories are not automatically assigned to a new user; access is granted on a
  user’s authenticated submission.
