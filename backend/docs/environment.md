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
- `JWT_SECRET_KEY` is reserved for the separately approved authentication
  design.
- `SENTRY_DSN` enables the approved Sentry integration outside test
  environments.

All three variables must remain unset in committed files. Production requires
distinct `SECRET_KEY` and `JWT_SECRET_KEY` values of at least 32 characters.
Development and test startup generate distinct process-local random values
when either secret is absent; generated values are never logged.

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
- `PRODUCTION_DATABASE_URL` uses the pooled production connection.
- `MIGRATION_DATABASE_URL` uses a direct Neon connection for migrations.

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

## Python and dependency baseline

- The backend targets Python 3.12 compatibility.
- The existing local project virtual environment was created with Python 3.14.
- Python 3.12.10 is installed separately for compatibility verification.
- `requirements.txt` remains the authoritative pinned dependency set until an
  approved dependency-management change.

`Flask-Limiter` is initialized during application startup with no global or
route limits. It is disabled in test configurations. Approved endpoint rate
policies remain deferred to their own implementation scope.
