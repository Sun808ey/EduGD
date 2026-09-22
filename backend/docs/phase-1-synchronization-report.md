# Phase 1 GitHub synchronization

## Scope and evidence

This review covers the prepared Flask backend and React/Vite administrator
portal as of 12 September 2026. It verifies repository synchronization and
local quality gates. It does not certify a production database, a deployed
Railway service, or Android offline behavior.

The baseline was read from GitHub before changing tracked application files:
`main` at `ea07afa713909c3c628b09a394e39059f74a7070` ("Updated README").
The prepared branch was `feature/frontend-production` at `b60c211`.
The initial cached `origin/main` reference was stale; fetching current main
established the baseline above. Main and the prepared branch had diverged, so
a merge preserves both histories rather than replacing main with an unrelated
branch tip. No force push or history rewrite is required.

## Confirmed mismatch

| Required item | GitHub main before synchronization | Prepared result |
| --- | --- | --- |
| Root README | Names Neon and Render; lists Android and root docs directories absent from this checkout | Supabase, Railway, actual directory layout, reproducible install/build and release-gate links |
| Railway configuration | `backend/railway.json` absent | Railpack build, pre-deploy migration, Gunicorn startup, dependency readiness |
| Gunicorn configuration | `backend/gunicorn.conf.py` absent | Platform port, one worker/four threads, timeouts and privacy-conscious access logs |
| Migration runbook and report | Both absent under `backend/docs` | Reviewed migration/rollback runbook and integration report, with current frontend status corrected |
| Workflows | Only `opencode.yml` present | Backend quality, frontend quality and Supabase PostgreSQL integration workflows retained |
| Backend entry point | Standalone Flask app with only `/`, fixed port and `debug=True` | Application factory exported as `run:app`, environment port and no hard-coded debug mode |
| Vite frontend and lockfile | Present | Prepared portal and its committed lockfile retained; clean install and build checked locally |

The merge retains the prepared ignore rules and trusted-author restriction on
write-capable OpenCode comment automation. Three obsolete editor-history copies
introduced by main are excluded. The current source tree excludes local secrets
and generated artifacts; existing historical-secret remediation remains a
separate requirement described in the production runbook.

## Configuration review

Railway's configuration reference supports the prepared JSON build command,
start command, pre-deploy command and readiness path. Pre-deploy commands run
before application startup; failure stops the deployment. The backend service
must use root `/backend` and config path `/backend/railway.json`.[1][2]

Supabase documents direct connections for persistent backends and session
pooling for IPv4-only networks. The prepared application accepts these modes
on port 5432 and rejects transaction pooling. Its `verify-full` TLS requirement
is consistent with Supabase's certificate-verifying psql example. Actual CA
availability, role privileges and target connectivity still require live
verification.[3][4]

The migration runbook was reviewed for separate runtime/migration credentials,
backup and restore rehearsal, forensic comparison, staging, and rollback. Its
production release gates remain in force. No database migration or production
cutover was executed as part of Phase 1.

## Verification results

The frontend build uses reserved `https://api.example.invalid/api/v1` solely to
validate bundling; this is not a deployable production endpoint.

| Gate | Observed result on 12 September 2026 |
| --- | --- |
| `npm ci` | Passed; 323 packages installed from the existing lockfile |
| Frontend TypeScript and ESLint | Passed via `npm run quality` |
| Frontend Vitest coverage | 26 tests passed; 98.63% statements, 92.98% branches, 98.11% functions, 99.47% lines |
| `npm run build` | Passed via `npm run quality`; Vite production bundle generated |
| Frontend dependency audits | Full and production-only audits reported zero vulnerabilities |
| `npm ls --depth=0` | Passed; locked top-level dependency tree is consistent |
| Playwright desktop/mobile Chromium | 10 tests passed; mocked API flows, accessibility, rate limiting, revoked sessions and read-only permissions |
| Backend Ruff lint | Passed |
| Backend Ruff formatting | Corrected a missing final newline in `tests/test_error_handlers.py`; full recheck passed, 102 files formatted |
| Backend mypy | Passed across 43 source files |
| Backend `pip check` | No broken requirements |
| Backend Bandit (`-ll`) | No medium/high severity findings; one low severity finding below the configured gate |
| Backend `pip-audit -r requirements.txt --strict --timeout 30` | Passed with network/cache access: no known vulnerabilities; direct pinned-list audit also passed |
| Backend coverage suite | 468 passed, 38 live PostgreSQL cases deselected, three filesystem setup errors; 90.69% coverage exceeds the unchanged 90% gate |
| Focused SQLite migration rerun | All three previously blocked cases passed; 471 default-suite cases therefore passed across the two runs |

Three SQLite migration cases initially failed during fixture setup because the
sandbox could not access the existing Windows pytest temporary directory. A
focused rerun with authorized filesystem access passed all three in 5.92 seconds.
No test assertions, migration code or thresholds were weakened. Playwright's
local Vite server needed explicit shutdown after all assertions passed; the
runner subsequently exited successfully with `10 passed (5.2m)`.

The initial coverage command exited with errors from the three fixture failures;
it is not represented as a single clean full-suite run. The focused rerun resolves
those exact failures. The 38 excluded live PostgreSQL cases remain unverified.
The initial sandboxed dependency audit stalled while upgrading pip in a temporary
environment; the authorized standard audit completed successfully. Dependency
requirements were not changed to obtain the passing result.

## GitHub synchronization and remaining gates

**Phase 1 synchronization completed.** GitHub main was verified at
`c9a659812d8eafd7d36d02f9c92d99c179534e46`, matching the reviewed local merge.
This documentation follow-up records the observed hosted-CI blocker.

All three hosted workflows were created for that commit but executed zero steps.
GitHub's check annotations state: "The job was not started because your account
is locked due to a billing issue." This is an account-level execution blocker,
not a hosted test result. The account owner must resolve GitHub billing and
rerun the workflows; no billing settings were changed here.

| Hosted run | Observed result |
| --- | --- |
| [Backend quality](https://github.com/Sun808ey/EduGD/actions/runs/34693358124) | Not started: account billing lock |
| [Frontend quality](https://github.com/Sun808ey/EduGD/actions/runs/34693358169) | Not started: account billing lock |
| [PostgreSQL integration](https://github.com/Sun808ey/EduGD/actions/runs/34693358135) | Not started: account billing lock |

The GitHub environment `backend-integration-test` exists. Its read-only public
metadata exposed no protection rules. Classic main branch protection was also
reported absent; repository rulesets were not established by that endpoint.
Secret/variable metadata could not be
verified with the current GitHub CLI authentication. Existence alone does not
prove that the dedicated PostgreSQL workflow can run successfully. Git uses a
separate credential manager; its push dry run accepted the merged history as a
fast-forward update to main despite the CLI token issue. The merged tree contains
all seven requested source/configuration/documentation items. Publication uses
an ordinary fast-forward push, followed by a remote commit comparison; it does
not rewrite either branch's history.

The PostgreSQL suite is intentionally separate from the default SQLite suite.
Its configured job requires a dedicated disposable Supabase project, matching
runtime/migration URLs, project identity and destructive-test opt-in. No live
database result is inferred from local unit tests. Linux Gunicorn startup,
hosted CI, actual frontend/API origins, restore rehearsal, Redis/proxy behavior
and Android device tests remain distinct deployment gates.

## Sources

Repository evidence: GitHub `Sun808ey/EduGD`, main commit
[`ea07afa`](https://github.com/Sun808ey/EduGD/tree/ea07afa713909c3c628b09a394e39059f74a7070),
prepared commit `b60c211`, and the local configuration, tests and runbooks
named above. Provider documentation was accessed on 12 September 2026; these
are living documents, not a guarantee of platform settings in this account.

1. Railway, [Config as Code reference](https://docs.railway.com/config-as-code/reference), accessed 12 September 2026.
2. Railway, [Pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command), accessed 12 September 2026.
3. Supabase, [Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres), accessed 12 September 2026.
4. Supabase, [Connecting with PSQL](https://supabase.com/docs/guides/database/psql), accessed 12 September 2026.
