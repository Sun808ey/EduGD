# EduG production integration implementation report

Verified locally on 10 September 2026. External platform configuration and
production state have not been inspected or changed.

## A. Executive summary

Implemented reversible configuration, deployment, verification and frontend
foundation changes for React/Vite → HTTPS → Railway → Flask/Gunicorn →
SQLAlchemy → Supabase PostgreSQL. Existing Neon compatibility remains available.
Flask remains the business/authentication layer. No schema migration, business
route, model or authentication/policy service was rewritten.

**FINAL VERDICT: FAIL — NOT READY.** Local checks do not establish production
readiness. Live PostgreSQL migration/concurrency tests, restore rehearsal,
runtime grants/TLS, Railway/Redis/proxy validation, historical-secret remediation
and Android offline evidence remain prerequisites. This is not a deployment or
cutover approval. No production database was contacted.

## B. Audit findings and target architecture

| Area | Verified repository facts and implications |
| --- | --- |
| Factory/entry | `app.create_app` is exported through `run.py`; Gunicorn can use `run:app` without restructuring. |
| Database | Flask-SQLAlchemy with psycopg2; runtime and migration URLs already separate. Provider assumptions were Neon-specific. |
| Migrations | Sixteen linear revisions, current head `e4a1b7c9d2f6`; retained verbatim. SQLite tests do not prove PostgreSQL trigger/concurrency behavior. |
| Authentication | Existing 15-minute JWT Bearer sessions, database-authoritative administrator permissions/RBAC, enrollment controls and device signature/nonce checks remain. |
| Policy/sync | Existing immutable policy revisions, assignments and synchronization contracts retained. No queued event-upload endpoint was found. |
| Forensics | Revision hashes, assignment/synchronization hash chains, chain heads and database triggers exist. Other audit tables do not all provide identical immutability guarantees. No evidence was rewritten. |
| Rate limits | Existing Redis-backed production limiting is required and fails closed; login/registration limits and configured policy-sync limits remain. Redis is an existing required dependency, not new infrastructure added for this migration. |
| Logging | Existing Flask logging, error handling and Sentry remain. Gunicorn access logs omit request targets/headers/addresses; optional frontend Sentry drops request/user context and exception text. |
| Security | Strong secret validation, body limits, replay defenses and one trusted proxy hop already exist. Production CORS now requires exact HTTPS origins. Historical-secret remediation remains externally unverified. |
| Render/Neon | `render.yaml` is retained; its existing migration-in-build behavior is documented accurately. Railway uses a separate pre-deploy migration command. |
| Frontend | React/Vite/TypeScript/Axios foundation exists; starter UI and empty feature pages are not an implemented administrator application. A missing button-variant module blocked the baseline build. |
| Android | No Android sources in this checkout. DevicePolicyManager → local deterministic engine → Room/queue → synchronization is the required external architecture, not a verified implementation here. Cloud connectivity must never become a prerequisite for cached enforcement. |

The relevant backend, migrations, tests, configuration, dependencies, CI,
deployment documentation and frontend foundation were reviewed. The source
database contents, deployed source revision, Android build and external service
settings are unknown and must not be inferred from this checkout.

## C. Changes, justification, risk and verification

The smallest safe approach is to keep application behavior and schema intact,
extend existing provider configuration, add a normal Gunicorn deployment, and
make migration/integration prerequisites testable. All changes below are local.

| Files/paths | Reason and modification | Risk | Verification |
| --- | --- | --- | --- |
| `app/config.py` | Accept Supabase direct/session connections with full TLS verification; reject transaction pooler and libpq authority overrides; compare tenant/database identity. Preserve Neon rules. | Medium: stricter configuration rejects unsafe URLs. | Existing database configuration and new Supabase regression tests. |
| `app/__init__.py` | Validate exact HTTPS administrator origins in production. | Low: invalid origin settings now fail startup. | Existing CORS and new production-origin tests. |
| `test_support/postgres_safety.py`, `tests/test_supabase_configuration.py` | Extend isolated destructive-test guards to exact Supabase project identity and connected TLS/identity. | Medium: live database semantics remain unverified. | Guard tests; actual PostgreSQL CI still required. |
| `railway.json`, `gunicorn.conf.py`, `tests/test_railway_configuration.py` | Existing entry point, bounded worker/thread count, PORT binding, pre-deploy migration, dependency readiness and private access-log format. | Medium: real proxy/network/platform behavior needs staging. | Configuration tests; Linux Gunicorn CI check added. |
| `scripts/__init__.py`, `scripts/database_inventory.py`, `scripts/compare_database_inventories.py`, `tests/test_database_inventory.py` | Add read-only inventories, typed row fingerprints, sequence/schema/trigger comparison and existing forensic verifiers; reject incomplete evidence. Never modify source or overwrite a report. | Medium: source version/permissions/extra schemas may require expanded verification. | Canonicalization, orphan-chain, incomplete/malformed evidence and comparison tests; real restore rehearsal required. |
| `docs/openapi.json`, `tests/test_openapi_contract.py` | Document existing credential-revocation route, correct response references/path parameters, check actual methods. | Low: outline remains incomplete for generated clients. | Route/parameter/error contract tests. |
| `../frontend/school-policy-admin/src/lib/environment.ts`, `src/services/api.ts`, `vite.config.ts`, `.env.example` | Public API configuration, explicit HTTPS production URL, development proxy, existing alias and Tailwind build support. | Low: deployment builds require a real API URL. | Node configuration tests, lint, TypeScript/Vite build. |
| Frontend `src/main.tsx`, `src/lib/observability.ts` | Optional public Sentry DSN validation and privacy-filtered error reporting. | Low: reduced diagnostic detail is intentional; delivery needs staging. | Privacy/DSN tests and build. |
| Frontend `src/components/ui/button-variants.ts` | Restore missing module consumed by existing button component. | Low: visual review of future screens remains. | TypeScript and bundle build. |
| Frontend `package.json`, `package-lock.json`, `tests/integration-configuration.test.mjs` | Compatible advisory fixes, build-time dependency classification, built-in Node configuration tests. | Medium: package changes need browser smoke testing. | npm audit, tests, lint and production build. |
| `../.github/workflows/backend-postgres.yml`, `backend-quality.yml`, `frontend-quality.yml` | Supabase project marker, helper lint/type/security scans, Linux entry-point check and frontend CI. | Low: CI secrets/platform results still external. | Local equivalent checks; hosted jobs not observed. |
| `../.github/workflows/opencode.yml` | Restrict write-capable comment automation to trusted repository associations. | Low: untrusted commenters no longer trigger it. | Workflow review; hosted execution unverified. |
| `.env.example`, `docs/environment.md`, `production-runbook.md`, `database-migration-runbook.md`, `architecture-security-decisions.md`, `testing.md`, `quality-baseline.md`, this report; frontend `README.md`; `../.gitignore` | Provider setup, operator migration/rollback gates, actual frontend scope and ignored local evidence. | Low: operators must substitute verified environment facts. | Cross-check against code and primary provider documentation. |

Paths are relative to `backend` unless noted. Frontend file names grouped in a
row share the `frontend/school-policy-admin` directory. No tests were removed or
security thresholds reduced. Review-driven additions were the read-only evidence
tools, frontend CI/privacy checks and OpenAPI structural corrections; these make
the approved migration and frontend integration verifiable without altering core
behavior. A scanner finding in sequence inventory was resolved with SQLAlchemy
expressions rather than suppression.

## D. Files intentionally unchanged

`app/models.py`, business route/service modules, cryptography, authentication and
RBAC implementations, forensic verifiers, all existing migration files,
`migrations/env.py`, `run.py`, backend dependency requirements and `../render.yaml`
remain unchanged. Existing tests remain, with additions to the OpenAPI test.
No Docker, microservices, Supabase Auth, Edge Functions or Realtime were added.
No Android code, production secrets or deployed resources were modified.

## E. Supabase configuration

Use direct port 5432 for the persistent Flask process and migration/backup tools
when IPv6 is reachable. Use the session pooler on port 5432 for IPv4-only runners;
transaction port 6543 is rejected. This follows [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).

Require `sslmode=verify-full`, install the target CA when necessary and enable
server SSL enforcement. URL validation proves configured intent; only an actual
successful hostname-verified TLS connection proves connectivity. See [Supabase
SSL guidance](https://supabase.com/docs/guides/platform/ssl-enforcement).
Disable the Data API for this Flask-only design and verify anonymous table access
is unavailable. Use separate restricted runtime and migration-owner roles;
preserve triggers and review grants/default privileges. No external step is
assumed completed.

## F. Railway configuration

Root `/backend`, config `/backend/railway.json`, Railpack, requirements install,
pre-deploy `flask --app run.py db upgrade`, start
`gunicorn --config gunicorn.conf.py run:app`, readiness `/api/v1/ready`. Initially
one replica, one worker, four threads; default runtime pool budget is five
connections plus migration/deployment overlap. Keep the existing shared Redis
requirement. Enable and test outbound IPv6 when using direct Supabase.
These follow [Railway Flask](https://docs.railway.com/guides/flask),
[pre-deploy](https://docs.railway.com/deployments/pre-deploy-command) and
[outbound networking](https://docs.railway.com/networking/outbound-networking)
guidance. Actual Linux startup, deployment and network topology are unverified.

## G. API/frontend integration

Routes, payloads, signatures and JWT/RBAC remain unchanged. The only browser
backend address is public `VITE_API_BASE_URL=https://<api-host>/api/v1`, supplied
at build time. `VITE_SENTRY_DSN` may contain only the optional public browser DSN.
No database or signing credentials belong in any `VITE_*` variable. Configure
the exact HTTPS frontend origin server-side. See the frontend README for local
development and the remaining UI/auth/error-handling work.

## H. Security

Supabase TLS/tenant isolation, URL override rejection, strict production CORS,
private Gunicorn logging and frontend Sentry filtering are covered by local
tests. Existing fail-closed Redis, JWT/RBAC, nonce/signature defenses and audit
behavior remain. Package security checks and the unchanged security thresholds
are recorded below. The historical-secret incident described in the production
runbook still requires owner-verified revocation/rotation and history scanning;
no credentials were read or printed for this work.

## I. Tests and checks

Commands below ran from `backend` with its Python 3.12.10 virtual environment,
or from `frontend/school-policy-admin` with Node 24.19.0. The normal backend test
selection explicitly excludes PostgreSQL/migration/concurrency tests requiring
an approved disposable database; exclusion is not a pass.

| Check/command | Exact final result |
| --- | --- |
| `python -m pytest --cov=app --cov-branch --cov-report=term --cov-fail-under=90 --tb=short --junitxml=.pytest_cache_local/production-integration-results.xml` | **459 passed, 38 deselected, 525.56 seconds; 90.64% coverage**, unchanged 90% threshold. Covers backend/API, authentication/RBAC, device/policy/sync, startup/readiness and forensic tests in the normal local selection. |
| `python -m pytest tests/test_database_inventory.py tests/test_openapi_contract.py -q --tb=short` after final helper/contract changes | **20 passed in 4.65 seconds**. These overlap the full suite; do not add the counts as separate unique tests. Nine newly added cases were included in this later run. |
| `python -m ruff check .` | **All checks passed.** |
| `python -m ruff format --check .` | **100 files already formatted.** |
| `python -m mypy app test_support scripts` | **Success: no issues found in 43 source files.** |
| `python -m bandit -r app test_support scripts -c pyproject.toml -ll` | **Exit 0, zero medium/high issues; one low finding** (existing testing pepper literal). No suppression or lowered threshold added. |
| `python -m pip check` | **No broken requirements found.** |
| `python -m pip_audit -r requirements.txt --strict` | **No known vulnerabilities found.** |
| Alembic `ScriptDirectory` graph inspection | **16 revisions; single head `e4a1b7c9d2f6`.** Local test fixtures exercise the SQLite migration path. Actual PostgreSQL schema/migration verification remains blocked. |
| `create_app('testing')` and test-client `GET /api/v1/health` | **HTTP 200**, `{"service":"school-policy-api","status":"running"}`. This is testing-factory startup, not a real production Gunicorn process. |
| `npm test` after final privacy change | **3 passed, 0 failed, 0 skipped.** |
| `npm run lint` | **Exit 0, no lint errors.** |
| `npm run build` with `VITE_API_BASE_URL=https://api.example.invalid/api/v1` | **TypeScript and Vite 8.1.4 pass**, 366 modules, final JavaScript 280.00 kB (89.63 kB gzip). Placeholder build is not deployable configuration. |
| `npm audit --audit-level=moderate` | **Found 0 vulnerabilities.** |
| `git diff --check` | **Exit 0**, no whitespace errors; Git reports expected CRLF-to-LF normalization warnings for two text files. |
| `git diff --exit-code` on protected model/route/service/crypto/RBAC/observability/migration/entry/requirements/Render paths | **Exit 0**, no changes. |
| Live PostgreSQL, production connectivity/SSL, Linux Gunicorn, hosted CI, real Redis, browser-to-staging, Android devices and Sentry delivery | **NOT RUN / NOT VERIFIED.** No approved external configuration or device evidence was available. |

The first new OpenAPI method test failed because its dictionary discarded
separately registered methods for the same path. Aggregating those methods fixed
the test lookup; no application route or assertion was removed. The initial
inventory security scan flagged string SQL; replacing it with SQLAlchemy
expressions produced the final clean medium/high scan above. Baseline frontend
build failures from the missing button module and TypeScript integration errors
were fixed before the successful builds. Earlier sandbox temporary-directory
errors were resolved with authorized test execution, not by skipping tests.

## J. Remaining risks and readiness gates

| Required category | Status | Scope/evidence gap |
| --- | --- | --- |
| Architecture | PASS | Repository preserves Flask/SQLAlchemy and contains compatible deployment configuration; Android implementation is external. |
| Backend/API | PASS | Local regression/contract evidence only; deployed smoke validation remains required. |
| Database | FAIL | Live PostgreSQL suite, TLS, grants, migration/restore and schema evidence unresolved. |
| Authentication/RBAC | PASS | Local regressions preserve contracts; target runtime-role verification still required. |
| Security | FAIL | Historical-secret closure and deployed TLS/proxy/privilege verification unresolved. |
| Deployment | FAIL | Railway/Linux startup and real service prerequisites not verified. |
| Frontend integration readiness | FAIL | Browser/API staging flows and actual public endpoint/origin remain unverified; administrator UI is a scaffold. |
| Rate limiting | FAIL | Local behavior covered; shared production Redis and proxy identity require staging verification. |
| Logging/error tracking | FAIL | Local logging/privacy checks pass; live log/Sentry delivery and privacy not verified. |
| Forensic/audit integrity | FAIL | Local chain tests are insufficient to prove transferred data, PostgreSQL triggers or concurrency integrity. |

PASS entries describe the stated local scope only. Overall readiness is FAIL
until every critical external prerequisite and test is resolved. No guarantee of
flawless production behavior can be established from local tests alone.

## K. Rollback

Retain the source database, independent verified backups, source release/config
and a provider-compatible rollback release. Before target writes, stop target
writers and restore the verified source routing/release combination. After
target writes, stop writers and preserve evidence; use a compatible release on
Supabase or a separately verified reverse transfer. Never silently revert to a
stale source, downgrade forensic migrations or merge divergent audit chains.
Local code changes can be reverted by reviewed file diffs without altering the
schema; do not discard unrelated work or operator evidence.

## L. MANUAL ACTION REQUIRED

These actions require actual accounts, credentials, infrastructure or devices.
The [database migration runbook](database-migration-runbook.md) gives ordered
commands, SQL privilege setup, evidence gates and rollback instructions:

1. Record deployed revision, source version/schema, client API hostname and
   credential-remediation evidence (runbook section 1).
2. Create isolated target/rehearsal/disposable-test projects; choose direct or
   session connection, enable SSL, install CA, disable Data API, configure and
   verify restricted roles (section 2). Keep secrets server-side.
3. Capture read-only inventory, migration head, schema/counts/sequences,
   extensions/roles/grants and forensic results (section 3). Reports contain
   sensitive metadata and fingerprints; keep them under controlled access.
4. Make an independent backup and complete an actual restore rehearsal. Compare
   frozen fingerprints/schema/audit evidence, verify any historical migration
   requirements and run the guarded PostgreSQL/migration/concurrency suite only
   against disposable test data (section 4 and `testing.md`).
5. Configure Railway in staging, Redis, environment secrets, CA/IPv6 and exact
   CORS; run the hosted CI and real Gunicorn startup, signed requests, RBAC,
   rate limits, readiness, log/Sentry and frontend HTTPS tests (section 5).
6. Verify Android airplane-mode/restart/cached enforcement and reconnect behavior
   on actual devices. Identify how existing queued work reaches supported APIs.
7. Record final maintenance approval, stop ALL source writers, repeat the frozen
   transfer/evidence comparison and only then switch traffic (section 6). Keep
   the source and independent backups for the approved retention period.

No source deletion, history rewrite, external migration or production cutover
was performed by this implementation.

## M. Next frontend integration steps

Implement login/session expiry/logout and permission-aware navigation using the
existing Bearer API. Add device, policy, enrollment and audit views against
documented routes. Preserve server-authoritative RBAC, structured errors,
pagination and 429 handling. Add browser integration tests for those flows,
CORS, expired/revoked tokens and denied permissions. Validate token-storage and
content-security decisions before publishing the authenticated UI. Complete
the external gates above before claiming production readiness.
