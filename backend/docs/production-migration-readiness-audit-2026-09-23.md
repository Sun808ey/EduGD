# Production migration-readiness audit - 23 September 2026

## Verdict: PASS

The DPC v3 release was validated, migrated, and deployed once to the existing
Railway production service. Production data and administrator records were
preserved. No credentials, private keys, database rows, or credential-bearing
URLs are recorded in this report.

## Release and history evidence

- Rewritten release commit: `bedd4881e5d1821d67de9b8f9fdb31fe87db2eb6`.
- All published branches and the `integration-backup-20260918` tag were
  rewritten and force-updated after removing confirmed secret-bearing paths.
- Gitleaks `8.30.1` and git-filter-repo `2.47.0` were verified. Redacted scans
  of the working tree, refs, reflogs, rewritten mirror, unreachable objects,
  and a fresh clone found no live credential values. Eight remaining generic
  matches are documented false positives in tests or validation text.
- The encrypted pre-rewrite mirror recovery archive was verified by the
  operator; SHA-256: `610CFCF210DB4CCCB75262FD44D0A04F155372F0CA3DFE6E5AC2E638E9D06604`.
- The production backup/restore rehearsal archive was verified and its redacted
  attestation passed. Archive SHA-256:
  `CD247303189E51058BBE25864EC6E7C0E50229BB7B2CC860C746DDAB6FB92CDA`.

## Validation gates

| Check | Result |
| --- | --- |
| Ruff and Mypy | PASS |
| Backend ordinary tests | PASS - 680 tests |
| Isolated PostgreSQL 17 migration/concurrency suite | PASS - 39 tests |
| Frontend quality and production HTTPS build | PASS |
| Backup/restore rehearsal | PASS - verified TLS, reviewed TOC, AES-256 archive, PostgreSQL 17 restore and comparison |
| Migration chain | PASS - `d8f1a3c6e9b2` -> `fa3d7e1b9c42` -> `ab4e6f2c9d71` |
| Supabase security advisor | PASS - zero relevant lints after hardening |

## Production database

Production project `hszskxrgkptbytuquyfu` remained healthy throughout the
change. The live additive runner accepted only the approved project, database,
owner, verified TLS, starting head, exact schema, backup attestation, and
advisory lock. It applied only the two forward migrations and completed its
post-migration checks.

- Final Alembic head: `ab4e6f2c9d71`.
- All DPC v3 tables are present with RLS enabled.
- Runtime grants, Data API-role denial, immutable triggers, and the nine
  hardened function ACLs/search paths passed verification.
- Existing administrator and authentication-audit records were preserved.

## Railway production deployment

- Existing service: `edug-api-production`.
- Deployment ID: `5fda3e10-12b7-4021-9177-5526902c5117`.
- Deployment status: `SUCCESS`.
- Source artifact: clean archive derived from commit `bedd4881...`; reviewed
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

No second production deployment was attempted. Production remains on the
single verified DPC v3 release, and the prior compatible deployment was
retained only as Railway history.
