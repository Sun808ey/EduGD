# EduGD DPC v3 frontend readiness audit — 23 September 2026

## Verdict: FAIL — staging database gate blocked rollout

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
- Railway staging deployment `81a90eba-7e7b-42e8-9169-7b259fd01dcf` built the
  reviewed clean archive for commit `1c7017e6`, but its read-only hosted
  pre-deploy verifier stopped at `database_revision`. The staging database is
  still on the prior migration head; this candidate requires
  `c2f8a1b4d630`. The service remained on healthy deployment
  `3c66f931-18a7-44ee-abcf-3c5aa70d99fd`; no production migration or deploy was
  attempted.

## Remaining PASS gates

The approved additive staging migration must first advance the staging schema
to `c2f8a1b4d630`, followed by a fresh staging deployment and hosted
verification. Until that migration and verification pass, do not configure or
deploy production. Hosted evidence must confirm OpenAPI parity, RLS, Data API
denial, CORS, public status, policy authoring, assignment, Block/clear,
evidence rendering and the production-configured Vite build. Record only
redacted evidence in this file.
