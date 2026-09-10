# Backend environment baseline

This document records non-secret environment variable names only. Never put
connection strings, credentials, tokens, secret keys, or Sentry DSNs in this
file or in Git.

## Runtime selection

- `APP_ENV` selects `development`, `testing`, `postgres-testing`, or
  `production`.
- `FLASK_APP` identifies the Flask application entry point.
- `FLASK_DEBUG` enables development debugging only when explicitly set.

## Secrets and monitoring

- `SECRET_KEY` is the Flask application secret.
- `JWT_SECRET_KEY` signs short-lived administrator access JWTs.
- `ADMIN_AUDIT_PSEUDONYM_KEY` creates keyed source-address pseudonyms for
  administrator authentication events.
- `POLICY_SYNC_AUDIT_KEY` creates keyed device-identity pseudonyms for policy
  synchronization events and must be distinct from every other secret.
- `SENTRY_DSN` enables the approved Sentry integration outside test
  environments.
- `REDIS_URL` identifies the existing shared Redis service used for
  production rate-limit state. Production startup and readiness fail closed
  when it is missing or unreachable.

All secret variables must remain unset in committed files. Production requires
distinct `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_AUDIT_PSEUDONYM_KEY`, and
`POLICY_SYNC_AUDIT_KEY` values of at least 32 characters. Development and test
startup generate distinct process-local random values when any is absent;
generated values are never logged.

Sentry remains inactive without `SENTRY_DSN` and is always inactive in the
`testing` and `postgres-testing` environments. When enabled, it labels events
as development or production, excludes request bodies and default PII, removes
request and breadcrumb data before sending, redacts configured secrets, and
uses a 25 percent error-event sample rate with a 1 percent trace sample rate.

Application logs use one-line JSON records with timestamp, severity, logger,
environment, message, and optional event name. Configured secrets, bearer
tokens, and URL credentials are redacted. Exception logs include the exception
type without rendering the potentially sensitive exception message.

## Database variables

Use separate Neon branches or Supabase projects for each environment. Neon
compatibility remains available for rollback. Supabase is the new production
target; provisioning is manual, not implied by this configuration.

- `DEVELOPMENT_DATABASE_URL` identifies the separate development connection.
- `POSTGRES_TEST_DATABASE_URL` identifies the isolated PostgreSQL integration
  and migration test branch.
- `POSTGRES_TEST_ENDPOINT_ID` is the non-secret `ep-*` identifier from that
  branch's pooled/direct connection hostname and must match both URLs.
- `POSTGRES_TEST_PROJECT_REF` is the non-secret approved Supabase test project
  reference, required instead of the Neon endpoint marker for Supabase tests.
- `PRODUCTION_DATABASE_URL` identifies the production runtime connection.
- `MIGRATION_DATABASE_URL` identifies the matching database using the migration
  owner: direct for Neon; direct or session-pooler for Supabase as described below.
- `PAIRING_TOKEN_PEPPER` is a deployment-secret HMAC pepper of at least 32
  characters. It is required whenever enrollment administration or an
  enforcing device-enrollment mode is enabled.
- `PAIRING_TOKEN_PEPPER_VERSION` identifies the current token-verifier pepper.
  Keep older versions available until every token issued with them has expired
  or been revoked.
- `DEVICE_ENROLLMENT_MODE` is one of `legacy`, `new_devices_required`, or
  `all_required`. Roll out in that order only after the corresponding
  migration and client-readiness gates pass.
- `ENROLLMENT_ADMIN_ENABLED` independently gates token administration routes.

Application startup selects its database variable from the active environment.
Development and production require pooled URLs when using Neon. Supabase uses
direct or session-pooler connections on port 5432 for runtime and migrations,
with `sslmode=verify-full` and a trusted certificate chain. Direct connections
are preferred for this persistent deployment; verify outbound IPv6 or use the
session pooler for IPv4-only environments. Transaction port 6543 is rejected.
PostgreSQL integration testing accepts its isolated approved provider target.
All PostgreSQL URLs require TLS.
Configured development, test, and production URLs are rejected if they resolve
to the same Neon branch or Supabase project, even through different poolers.

Migration commands require `MIGRATION_DATABASE_URL` and reject pooled Neon
endpoints. The direct migration endpoint must identify the same branch as the
active application URL and database. Supabase direct/session migration URLs
must likewise match the runtime project and database. Parameters overriding
host, database, user, service or connection options are rejected. Normal
application startup does not require the
migration variable.

SQLite in memory remains limited to fast unit tests that do not depend on
PostgreSQL behavior.

## Liveness and readiness

- `GET /api/v1/health` reports process liveness without checking dependencies.
- `GET /api/v1/ready` reports readiness only when essential configuration is
  present, the database responds, and its Alembic revision matches the current
  application migration head.

PostgreSQL connection acquisition and establishment use three-second bounds.
Readiness statements use a two-second PostgreSQL statement timeout. A failed
check returns only a generic `503 not_ready` response; database errors,
connection information, configuration names, and migration details are not
returned to clients.

## Request and device-compatibility limits

Flask applies a 1 MiB global request ceiling. Device registration and
administrator login apply smaller 16 KiB ceilings before JSON parsing.
Registration requires canonical lowercase hyphenated UUIDv4 text and a
matching Android/API pair from Android 5.0/API 21 through Android 10/API 29;
API level is the authoritative compatibility value.

## Python and dependency baseline

- The backend targets Python 3.12 compatibility.
- The verified local project virtual environment uses Python 3.12.10.
- `requirements.txt` remains the authoritative pinned dependency set until an
  approved dependency-management change.

`Flask-Limiter` is initialized during application startup with no global
limits. Administrator login is limited to 10 attempts per minute per source
address. Policy synchronization defaults to 60 requests per minute and uses an
authenticated credential identity when available, falling back to source
address only for an approved legacy client. `POLICY_SYNC_RATE_LIMIT` can tune
that deployment limit. The limiter remains disabled by default in test
configurations; focused tests explicitly enable it to verify the route policy.
Production never uses `memory://`; all Gunicorn workers share `REDIS_URL`.

Production defaults to `SQLALCHEMY_POOL_SIZE=3` and
`SQLALCHEMY_MAX_OVERFLOW=2`. Both values are validated at application creation:
pool size must be 1–10, overflow must be 0–10, and their sum must not exceed 10
per worker. The retained Render configuration and new Railway configuration
both use one worker, making the default per-instance ceiling `1 × (3 + 2) = 5`.
Budget additionally for overlapping deployments, migrations and platform
services. This is an application budget, not an assumed provider limit. Confirm
it against the actual database allocation
before changing worker or pool settings.

Railway is the target runtime; Render files are retained for the existing
deployment. `ProxyFix` trusts exactly one proxy hop in production and is
disabled elsewhere. Verify Railway forwarded headers and signed raw request
targets in staging. Do not add another proxy without reviewing this boundary,
because forwarded
addresses feed rate limits and audit pseudonyms.

Production `ADMIN_FRONTEND_ORIGINS` must contain exact HTTPS origins without
paths, credentials, queries or fragments. Local HTTP origins remain supported
in development. The frontend receives only a public `VITE_API_BASE_URL` ending
in `/api/v1` and optional public `VITE_SENTRY_DSN`. No database or server secrets
belong in any `VITE_*` variable.

See [database migration runbook](database-migration-runbook.md) for the complete
operator procedure, TLS trust, restricted runtime grants and approval gates.
