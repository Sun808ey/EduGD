# Codebase Audit Report

Date: 2026-09-22
Branch: `feature/security-module`
Commit audited: `9f1a6eb`

## Executive Result

**PASS: local and approved hosted readiness checks pass.** The two backend registration regressions identified in the original audit were repaired, frontend coverage exceeds the configured thresholds, Docker-backed PostgreSQL checks pass, both approved hosted databases are migrated to the current head, and hosted verification plus Redis readiness checks pass.

## Verified Passing Checks

- Focused backend device-policy, registration, certification, and hosted-verification tests: 191 passed across the remediation runs.
- Backend safe suite: 643 passed, 38 excluded by repository markers.
- Docker-backed PostgreSQL, migration, and concurrency checks: 38 passed; 645 unrelated tests were deselected.
- OpenAPI contract tests passed.
- Migration revision tests passed when run with a writable local pytest temp directory.
- Python compilation passed.
- Ruff formatting and lint passed.
- mypy passed for `app`, `test_support`, and `scripts`.
- `pip check` passed.
- Frontend typecheck and lint passed.
- Frontend coverage: 98.32% statements, 94.44% branches, 96.61% functions, and 99.51% lines.
- Frontend production build passed with a valid non-secret `VITE_API_BASE_URL` placeholder.
- Frontend Playwright suite: 10 passed across desktop and mobile Chromium.
- Frontend npm audit checks: 0 vulnerabilities.
- Both approved hosted database migrations completed through `d8f1a3c6e9b2`.
- Hosted runtime security checks passed: 182 permission checks, 26 RLS tables and policies, and zero violations or unexpected Data API grants.
- Staging and production hosted verifiers passed, both public readiness endpoints returned HTTP 200, and Redis connectivity passed with `PING`.
- Final Railway deployment verification passed for staging deployment `5ea09ade-a2f5-48c3-a024-901410c5621d` and production deployment `af777ef6-e8b3-467b-8f74-8be79435105e`.

## Resolved Findings

### 1. Android downgrade response changed and was restored

Test: `backend/tests/test_device_registration.py::test_reported_android_downgrade_is_rejected_and_audited`

The original audit received HTTP `400` instead of the expected `409`. The request boundary now accepts known historical Android metadata, and the regression test passes with HTTP `409` and the `downgrade_rejected` audit event.

### 2. Android upgrade authentication contract changed and was restored

Test: `backend/tests/test_device_registration.py::test_reported_android_upgrade_requires_authentication_and_is_audited`

The original audit received HTTP `201` instead of the expected `409`. Historical API 28 registrations are now represented as suspended, while active-device admission remains API 29-36. The regression test passes with HTTP `409` and the `upgrade_requires_authentication` audit event.

The backend compatibility boundary and focused tests now preserve the established behavior without allowing new legacy devices to become active.

### 3. Frontend coverage thresholds were restored

The original audit reported 88.13% functions and 84.12% branches. Focused tests now cover public health, authentication cleanup, optional service parameters, and related error paths. The configured thresholds pass at 96.61% functions and 94.44% branches.

### 4. Hosted operational consistency was aligned

- Hosted verification now uses the bundled `supabase-ca.pem` path.
- Production migration table expectations are derived from current SQLAlchemy metadata instead of a stale 18-table list.
- Historical hosted documentation is explicitly labeled as the `e4a1b7c9d2f6` snapshot; current repository guidance uses head `d8f1a3c6e9b2`.

## Environment Notes

- Docker Desktop responded successfully and the disposable PostgreSQL, migration, and concurrency checks completed before cleanup.
- Hosted migrations and verification used only the approved staging and production projects. No destructive hosted tests were run.
- The frontend coverage command executed 31 tests and passed all configured thresholds.
- The frontend build passed with a valid non-secret HTTPS `VITE_API_BASE_URL` placeholder; production configuration still requires its deployment-specific value.
- Git still reports the intentionally excluded untracked `.vercel/README.txt` and `.vercel/project.json` files.
- Git reports a permission warning while traversing `.pytest-quality-temp/`; this did not affect the successful rerun using a writable audit temp directory.

## Remaining Verification Limits

1. The `.vercel` metadata and generated audit/build artifacts remain intentionally outside the commit until separately reviewed.
2. Deployment promotion and branch merges remain separate approval-gated operations.

## Disposition

The remediation is **ready for release-readiness sign-off**. Local Docker-backed checks, approved hosted migrations, hosted verification, Redis connectivity, and readiness endpoints all pass with no known code or test failures. Deployment promotion and branch merges remain separately approval-gated.
