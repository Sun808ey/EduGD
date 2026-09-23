# Railway staging deployment failure audit

Date: 2026-09-23
Service: `edug-api-staging`
Railway project: `blissful-luck`
Environment: staging
Supabase project: `dviuaqtlbuefmfmswwqt`
Required database revision: `fa3d7e1b9c42`

## Finding

Deployment `6389c5e0-7dad-4248-bbf2-164929fd70e8` built successfully with
Railpack and Python 3.12.14 and started Gunicorn. It failed because
`/api/v1/ready` repeatedly returned HTTP 503 while the application attempted to
connect to PostgreSQL.

The latest read-only hosted verifier isolated the failure before any readiness
query was executed:

```text
stage=database_connection
reason=ca_file_unavailable
bundled_ca=absent
ca_path=different
```

The deployed image did not contain `/app/certs/supabase-ca.pem`. In addition,
the database URL's `sslrootcert` query parameter did not identify that absolute
hosted path. Because an explicit URL parameter takes precedence over the
`PGSSLROOTCERT` fallback, both the artifact and URL must agree on the same file.

## Root cause

The reviewed public Supabase CA existed in the local checkout but was ignored by
Git and remained outside the committed revision. Railway CLI uploads respect
Git ignore rules by default, so earlier workspace and diagnostic uploads omitted
the certificate even though `.dockerignore` narrowly permits it in a Docker
build context. Gunicorn could therefore start, but PostgreSQL hostname and
certificate verification could not begin.

The service was also left in a temporary diagnostic configuration after the
failed investigation: the hosted verifier was the start command, the liveness
endpoint was the healthcheck, the timeout was 60 seconds, and restart behavior
was `NEVER`. Those settings are investigation state rather than the intended web
service configuration.

## Evidence

- Supabase staging is healthy and SSL enforcement is enabled.
- The dashboard's **Download certificate** link currently serves
  `prod-ca-2021.crt`.
- The staged `backend/certs/supabase-ca.pem` is byte-for-byte identical to that
  dashboard download. Its file SHA-256 is
  `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`.
- The certificate parses as `Supabase Root 2021 CA`, is valid until April 2031,
  and contains no private-key block.
- Supabase PostgreSQL is operational and `public.alembic_version` is
  `fa3d7e1b9c42`; no migration is required for this recovery.
- The previous Railway build and application import completed successfully.
- The failure occurs at database connection setup, before migration-head,
  runtime-table permission, or Redis readiness verification.

## Recovery applied

The recovery revision includes only the individually reviewed public CA and this
audit report. The narrow `.dockerignore` exception for
`certs/supabase-ca.pem` is retained. Railway staging is configured to use
`/app/certs/supabase-ca.pem` from both `PRODUCTION_DATABASE_URL` and
`PGSSLROOTCERT`, with `sslmode=verify-full` retained.

The intended service configuration is:

- root directory `/backend`;
- Railpack with Python 3.12;
- build command `pip install --requirement requirements.txt`;
- pre-deploy command `python -m scripts.verify_hosted_environment`;
- start command `gunicorn --config gunicorn.conf.py run:app`;
- healthcheck `/api/v1/ready` with a 120-second timeout;
- restart policy `ON_FAILURE` with at most 3 retries;
- sleep disabled, one replica, database pool size 1 and overflow 0.

The current session-pooler transport and IPv6 setting remain unchanged. The
pre-deploy verifier is read-only and does not run migrations.

## Deployment boundary

This recovery permits exactly one staging deployment attempt from a clean,
commit-derived artifact. The artifact must contain the reviewed CA and exclude
environment files, operator evidence, database dumps, private keys, and local
credentials. Production and database schema are outside the operation.

Success requires the pre-deploy verifier to pass, Railway to mark the deployment
`SUCCESS`, and both `/api/v1/health` and `/api/v1/ready` to return HTTP 200 over
HTTPS. If the attempt fails, no retry or speculative configuration change is
permitted; the deployment ID, failing stage, logs, HTTP results, and final
configuration must be appended here before stopping.

## Separate hardening work

Supabase reports nine `function_search_path_mutable` advisor warnings. They are
not involved in this TLS connection failure and require a separate reviewed
database migration. They do not block this staging recovery.
