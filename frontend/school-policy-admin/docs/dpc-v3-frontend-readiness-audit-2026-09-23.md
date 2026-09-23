# EduGD DPC v3 frontend readiness audit — 23 September 2026

## Verdict: FAIL — verification and hosted rollout pending

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
- OpenAPI, backend route, migration, frontend unit, browser and hosted checks
  remain required before this verdict can become PASS.

## Remaining PASS gates

Run backend static checks and tests, isolated PostgreSQL migration tests,
frontend quality and Playwright/axe checks, then validate an actual staging
deployment. Confirm OpenAPI parity, RLS, Data API denial, CORS, public status,
policy authoring, assignment, Block/clear, evidence rendering and a
production-configured Vite build. Record only redacted evidence in this file.
