# EduGD DPC v3 frontend readiness audit — 23 September 2026

## Verdict: FAIL — production rollout has not been evaluated

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

## Remaining PASS gates

Before this audit can become PASS, verify authenticated, real-data policy
authoring, assignment, Block/clear and evidence workflows with the existing
staging administrator. Production requires a current backup/restore
attestation for the observed `ab4e6f2c9d71` state, then the approved additive
migration, backend release and frontend promotion. Record only redacted
evidence in this file.
