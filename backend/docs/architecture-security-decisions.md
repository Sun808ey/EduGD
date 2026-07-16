# Approved architecture and security decisions

This document records approved decisions for the backend remediation backlog.
It does not mean later remediation increments have been implemented.

## Device lifecycle and identity

- Device statuses are `active`, `suspended`, and `retired`.
- The Android DPC creates and securely persists one canonical lowercase,
  hyphenated, non-nil version-4 UUID.
- The server rejects uppercase, braced, URN, compact, nil, and non-v4 UUIDs.
- Supported devices run Android 5.0 through 10.0, API 21 through 29.
- Both Android version and API level are stored; API level is authoritative.
- An authenticated OS upgrade updates device metadata and appends an immutable
  audit event. A reported downgrade is rejected and flagged for review.
- Suspended and retired devices receive HTTP 403 with operation `blocked` and
  retain their last locally enforced policy.

## Health and enrollment

- `/api/v1/health` remains process liveness.
- `/api/v1/ready` is approved for bounded database and essential-configuration
  checks that do not expose internals.
- Future enrollment uses a short-lived, single-use, school-issued pairing token
  stored as a server-side hash.
- Successful enrollment issues a separate revocable device credential and
  includes replay protection.
- Enrollment implementation requires separate approval of its detailed design
  and migration plan.

## Policies, assignments, and synchronization

- Policy statuses are `draft`, `active`, `inactive`, and `revoked`.
- `Policy` is stable identity and lifecycle; immutable `PolicyRevision` rows
  contain versioned content.
- Assignments reference an exact revision and record administrator, reason,
  event UUID, assignment time, and supersession time.
- Removing a policy produces operation `clear`.
- Intentionally assigning an older revision produces operation `rollback`.
- Numeric greater-than comparison alone must not determine synchronization.
- Synchronization may append a separate immutable audit event while policy and
  assignment state remain read-only.

## Request limits, rate limits, and monitoring

- Global maximum request size is 1 MiB.
- Registration and normal control-plane requests are limited to 16 KiB.
- Future forensic-log batches receive a separate explicit bound.
- Registration begins at 10 requests per minute per source IP.
- Policy pull begins at 60 requests per minute per authenticated device.
- An untrusted request `device_uuid` must not become the authenticated rate key.
- Sentry stays inactive without `SENTRY_DSN`, distinguishes environments,
  excludes secrets, credentials, and request bodies, and uses conservative
  sampling.

## Quality and database isolation

- Approved tools are Ruff, mypy, pytest-cov, pip-audit, and Bandit.
- Black is not approved because Ruff is the selected formatter.
- Development, PostgreSQL integration testing, and production use separate Neon
  branches.
- Application traffic uses pooled Neon URLs through
  `DEVELOPMENT_DATABASE_URL` or `PRODUCTION_DATABASE_URL`.
- PostgreSQL tests use `POSTGRES_TEST_DATABASE_URL`.
- Flask-Migrate and Alembic use the direct `MIGRATION_DATABASE_URL`, never a
  pooled application connection.
