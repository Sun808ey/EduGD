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

The approved target configuration uses separate Neon branches and variables:

- `DEVELOPMENT_DATABASE_URL` uses the pooled development connection.
- `POSTGRES_TEST_DATABASE_URL` identifies the isolated PostgreSQL integration
  and migration test branch.
- `POSTGRES_TEST_ENDPOINT_ID` is the non-secret `ep-*` identifier from that
  branch's pooled/direct connection hostname and must match both URLs.
- `PRODUCTION_DATABASE_URL` uses the pooled production connection.
- `MIGRATION_DATABASE_URL` uses a direct Neon connection for migrations.
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
Development and production require pooled Neon URLs. PostgreSQL integration
testing accepts its isolated test-branch URL. All PostgreSQL URLs require TLS.
Configured development, test, and production URLs are rejected if they resolve
to the same Neon branch.

Migration commands require `MIGRATION_DATABASE_URL` and reject pooled Neon
endpoints. The direct migration endpoint must identify the same branch as the
active application URL. Normal application startup does not require the
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
- The existing local project virtual environment was created with Python 3.14.
- Python 3.12.10 is installed separately for compatibility verification.
- `requirements.txt` remains the authoritative pinned dependency set until an
  approved dependency-management change.

`Flask-Limiter` is initialized during application startup with no global
limits. Administrator login is limited to 10 attempts per minute per source
address. Policy synchronization defaults to 60 requests per minute and uses an
authenticated credential identity when available, falling back to source
address only for an approved legacy client. `POLICY_SYNC_RATE_LIMIT` can tune
that deployment limit. The limiter remains disabled by default in test
configurations; focused tests explicitly enable it to verify the route policy.
