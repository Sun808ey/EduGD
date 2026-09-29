# Production migration-readiness audit - 23 September 2026

## Verdict: PASS

The DPC v3 release was validated, migrated, and deployed once to the existing
Railway production service. Production data and administrator records were
preserved. No credentials, private keys, database rows, or credential-bearing
URLs are recorded in this report.

## Release and history evidence

- Release commit deployed: `0be17d06f4e4f393deaf989e0930f72a96ad7dea0`.
- Current release evidence is kept under ignored `backend/operator-evidence/`;
  no credentials, private keys, database rows, or credential-bearing URLs are
  recorded here.
- Fresh production backup/restore rehearsal passed verified TLS, reviewed
  restore-list filtering, PostgreSQL 17 restore/comparison, and final DPC v3
  checks. Archive SHA-256:
  `BA0C7F6D52F0B6242B4885168FBDC6791A8ECE376D4C50C48A9F017F4A0AAA54`.

## Validation gates

| Check | Result |
| --- | --- |
| Ruff and Mypy | PASS |
| Backend ordinary tests | PASS - 680 tests |
| Isolated PostgreSQL 17 migration/concurrency suite | PASS - 39 tests |
| Frontend quality and production HTTPS build | PASS |
| Backup/restore rehearsal | PASS - verified TLS, reviewed TOC, AES-256 archive, PostgreSQL 17 restore and comparison |
| Migration chain | PASS - production `ab4e6f2c9d71` -> `c2f8a1b4d630`; linear rehearsal covered the earlier heads |
| Supabase security advisor | PASS - zero relevant lints after hardening |

## Production database

Production project `hszskxrgkptbytuquyfu` remained healthy throughout the
change. The live additive runner accepted only the approved project, database,
owner, verified TLS, starting head, exact schema, backup attestation, and
advisory lock. It applied the single forward migration and completed its
post-migration checks.

- Final Alembic head: `c2f8a1b4d630`.
- All DPC v3 tables are present with RLS enabled.
- Runtime grants, Data API-role denial, immutable triggers, and the nine
  hardened function ACLs/search paths passed verification.
- Existing administrator and authentication-audit records were preserved.

## Railway production deployment

- Existing service: `edug-api-production`.
- Deployment ID: `0cfebf18-925f-43c2-9cd2-77235ba44749`.
- Deployment status: `SUCCESS`.
- Source artifact: clean archive derived from commit `0be17d06...`; reviewed
  public Supabase CA included; operator evidence and secret material excluded.
- Root directory `/backend`; Railpack Python `3.12`; build command
  `pip install --requirement requirements.txt`; Gunicorn start command;
  hosted verifier pre-deploy; `/api/v1/ready` healthcheck with 120-second
  timeout; `ON_FAILURE` with three retries; one `ams` replica; sleep disabled.
- Runtime database URL uses `sslmode=verify-full` and
  `/app/certs/supabase-ca.pem`; `PGSSLROOTCERT` is set to the same path;
  pool size is `1` and overflow is `0`.
- Hosted verifier: `PASS`; DPC v3 signing variables are present; Redis and
  restricted runtime checks passed.
- HTTPS `/api/v1/health`: HTTP `200`.
- HTTPS `/api/v1/ready`: HTTP `200`.

No second Railway production deployment was attempted. Production remains on
the single verified DPC v3 release.
