# EduGD DPC v3 frontend readiness audit — 23 September 2026

## Verdict: FAIL — authenticated staging workflows remain unverified

The implementation adds API-backed DPC policy authoring, Block state, control
evidence, dashboard summary and a revised public landing page. The browser
continues to communicate only with the Flask API; it has no Supabase client or
privileged database configuration.

## Findings addressed

- The landing page now presents EduGD's Android-only, offline-first operating
  model, controls, privacy limits and stakeholder context. Its device artwork
  is an explicitly neutral illustration, not a screenshot or fleet simulation.
- The admin dashboard reads DPC totals from a dedicated authenticated API
  summary; device detail reads persisted override and evidence records.
- Policy creation produces immutable server-validated v3 revisions. Legacy v2
  policies remain readable and are not converted client-side.
- Blocked-domain evidence contains only a 32-byte hash, rule identifier,
  outcome and policy identity. Raw domains, URLs and allowed browsing are not
  stored or rendered.
- OpenAPI parity, backend route tests, migration tests, frontend unit tests,
  Playwright/axe checks, and the production-configured Vite build pass locally.
- The first clean staging deployment
  `81a90eba-7e7b-42e8-9169-7b259fd01dcf` stopped at `database_revision`, which
  correctly prevented an application/database contract mismatch.
- The approved additive migration advanced staging from `ab4e6f2c9d71` to
  `c2f8a1b4d630`. Read-only verification confirmed TLS, RLS, the runtime-only
  grant, Data API-role denial, the evidence immutability trigger and the
  `policy.manage` permission constraint.
- Replacement staging deployment `c491c828-f5a4-4118-a0f6-78c37386d3be` is
  `SUCCESS`. Its hosted verifier reported `PASS`; `/api/v1/health` and
  `/api/v1/ready` returned HTTP 200; the approved staging Vercel origin passed
  an administrator-route CORS preflight.
- Vercel staging deployment `dpl_GdSP5nP3dvtqcjkvL5svRDHkt6Fz` is `READY` at
  the approved staging alias. Browser verification confirmed the landing page
  and login route render, protected dashboard navigation redirects to login,
  and no browser-console errors occurred. The build used only the staging
  Flask API URL.
- Production backend migration completed at `c2f8a1b4d630`; Railway deployment
  `0cfebf18-925f-43c2-9cd2-77235ba44749` is `SUCCESS`, with hosted verification
  `PASS` and HTTPS health/readiness both returning `200`.
- Vercel production deployment is `READY` at `https://edug-admin.vercel.app`.
  Public browser verification found the EduGD landing page, redirected the
  protected dashboard to login, and recorded zero console errors.
- The first authenticated staging policy submission exposed a frontend payload
  defect: four required `device_controls` fields were omitted and the API
  correctly returned HTTP 400. The editor now sends the complete v3 control
  set; typecheck, lint, unit tests (31), and the production-configured build
  pass. Corrected Vercel staging deployment `AmUnZ34H6qxdbZN4Ka9aL69iaB1V`
  is `READY`, and a real authenticated staging policy was created successfully
  (`da917322-f750-4248-bc72-1846375dc324`).
- Direct route checks for the corrected production frontend returned HTTP 200
  for `/`, `/login`, and `/dashboard`; production API `/health` and `/ready`
  also returned HTTP 200.

## Automated verification snapshot

- PASS: backend Ruff and Mypy; 680 ordinary backend tests.
- PASS: frontend TypeScript, ESLint, production-configured build, 31 unit
  tests, and 10 Playwright browser tests (Chromium and mobile Chromium,
  including axe checks).
- FAIL: frontend coverage command; statements/branches/lines pass, but
  function coverage is 85.07%, below the configured 90% threshold.
- BLOCKED: the isolated PostgreSQL migration/concurrency container suite could
  not start because its disposable PostgreSQL 17 container exited with code
  137 (Docker resource termination). Containers, network, and volume were
  removed afterward. No hosted database was used.

## Remaining PASS gates

Before this audit can become PASS, verify authenticated, real-data policy
assignment, Block/clear and evidence workflows with the existing staging
administrator. Staging currently has no enrolled device, so those workflows
cannot be exercised without creating an approved real test enrollment. The
policy detail screen also exposes revisions read-only and has no lifecycle
action controls; activation/revision lifecycle coverage therefore remains
incomplete. The production backend and public frontend routes are deployed and
healthy; this report does not claim administrator actions that were not
executed. Record only redacted evidence in this file.
