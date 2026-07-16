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
- `SENTRY_DSN` enables Sentry only after its approved remediation increment.

All three variables must remain unset in committed files.

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

The following declared integrations are intentionally retained but currently
unused:

- `Flask-Limiter`, pending application-startup and route-limit remediation.
- `sentry-sdk`, pending approved Sentry initialization.

They must not be removed merely because they are not yet initialized.
