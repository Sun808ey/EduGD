# Production migration-readiness audit - 23 September 2026

## Verdict: FAIL - production migration and Railway release not yet executed

Production remains unchanged. No production migration, Railway production
configuration change, credential rotation, history rewrite, or deployment has
been performed. The current production service remains the compatible release
at deployment `af777ef6-e8b3-467b-8f74-8be79435105e`.

## Current hosted state

| Area | Evidence | Result |
| --- | --- | --- |
| Production Supabase | Project `hszskxrgkptbytuquyfu` is healthy and currently reports Alembic `d8f1a3c6e9b2`. | Healthy, migration pending |
| Production Railway | Existing deployment is healthy; `/api/v1/health` and `/api/v1/ready` previously returned HTTP 200. | Healthy, old contract |
| Staging Supabase | Project `dviuaqtlbuefmfmswwqt` is healthy and remains at Alembic `fa3d7e1b9c42`. | Ready for application verification |
| Staging hardening | Additive `ab4e6f2c9d71` SQL applied; the security advisor now returns zero lints. | PASS |

## Release-preparation changes

- Added the ninth hardened function, `edug_reject_device_control_event_mutation`,
  to `ab4e6f2c9d71`; the migration now fixes all nine mutable search paths,
  qualifies the validator call, and restricts execution to `edug_runtime`.
- Replaced security-critical verifier assertions with explicit fail-closed
  checks and made the hosted verifier require `ab4e6f2c9d71`.
- Added the live-schema-safe runner. It accepts only the observed production
  project, database, owner, TLS contract, starting head, exact schema, backup
  attestation, advisory lock, and forward migration path.
- Updated migration tests and the DPC v3 compatibility code without changing
  the public v2 or v3 HTTP contracts.

## Validation completed

| Check | Result |
| --- | --- |
| Ruff | PASS |
| Mypy | PASS - no issues in 56 source files |
| Backend ordinary tests | PASS - 680 tests |
| Isolated PostgreSQL 17 suite | PASS - 39 migration/schema/concurrency tests; no hosted database used |
| Frontend quality/build | PASS - quality suite, 31 tests, and production HTTPS build |
| Function-hardening unit tests | PASS - 2 tests |
| Backup/restore rehearsal | PASS - PostgreSQL 18 custom dump, reviewed TOC, AES-256 7-Zip archive, verified TLS PostgreSQL 17 restore, and local `d8f1a3c6e9b2 -> fa3d7e1b9c42 -> ab4e6f2c9d71` rehearsal |
| Restore comparison | PASS - all source rows preserved; only the three additive v3 tables were added |
| Rehearsal evidence | Ignored attestation at `backend/operator-evidence/production-rehearsal-20260923/fresh-20260923/backup-restore-attestation.json`; archive SHA-256 is recorded only in ignored evidence |

The rehearsal used only disposable Docker resources and was cleaned up. No
production write occurred. The reviewed restore list excludes only the
provider-owned `auth`, `storage`, `realtime`, `graphql`, and `vault` schemas
and the unavailable `supabase_vault` extension.

## Secret-history gate

Gitleaks 8.30.1 and git-filter-repo 2.47.0 are installed and checksummed in
ignored operator evidence. Redacted scans cover the working tree, all refs and
reflogs, the 15,103 unreachable blobs, and historical environment-path blobs.
The only current-tree matches are eight `generic-api-key` false positives in
test-vector or code-validation text; no live credential value was confirmed.
The unreachable-blob and historical-candidate scans returned zero findings.

The encrypted pre-rewrite recovery archive remains preserved at
`E:\\EduG-recovery\\EduGD-pre-rewrite.7z` with its supplied SHA-256 recorded
privately. The required mirror verification, repository-owner-approved rewrite,
post-rewrite scan, credential rotation, and force-update have not yet run, so
this gate remains open.

## Remaining production gates

1. Create and verify the full encrypted Git mirror, rotate or revoke any
   provider-confirmed credentials, rewrite every published branch and the
   `integration-backup-20260918` tag, and obtain a zero-finding scan of the
   rewritten repository and a fresh clone.
2. Stage and commit the reviewed candidate after a staged-diff and staged-secret
   scan. Do not include operator evidence, certificates except the reviewed
   public Supabase CA, dumps, private keys, or credentials.
3. Deploy that clean candidate to the existing staging Railway service and run
   the hosted verifier, DPC v3 signing check, Redis check, and both HTTP checks.
4. During the approved maintenance window, stage production variables and
   service settings, run `run_live_production_upgrade.ps1` separately, and
   verify the final head, grants, RLS, immutable triggers, and advisor state.
5. Create one clean commit-derived production archive and invoke exactly one
   Railway production deployment. If it fails, retain this FAIL verdict and
   append redacted deployment evidence without retrying.

Until those gates pass, the production verdict must remain FAIL.
