# EduG Production Frontend Implementation Audit

## A. Executive summary

The EduG administrator frontend has been implemented as a React 19 and Vite 8
single-page application for Vercel. It integrates only with the existing Flask
administrator API and preserves Flask as the authentication, RBAC, policy,
synchronization and audit authority. It does not connect to Supabase and does
not change Android offline policy enforcement.

The implementation includes login, identity verification, session expiry and
logout; API-backed dashboard, device, policy, enrollment-token and audit views;
permission-aware mutations; structured failures; pagination; rate-limit
handling; runtime payload validation; privacy-filtered Sentry support; security
headers; SPA deep-link routing; CI; unit coverage; and desktop/mobile browser
tests.

The frontend code and its local integration contract pass. Production
deployment remains an external gate because no Vercel project URL, Railway
public URL, production CORS value, production credentials, live Sentry project
or dedicated Supabase test database was available in the repository.

## B. Audit findings

### Architecture

The implemented path is:

```text
Administrator browser
  -> Vercel HTTPS static React/Vite application
  -> Railway HTTPS Flask REST API (/api/v1/admin/*)
  -> SQLAlchemy
  -> Supabase PostgreSQL
```

The Android path remains:

```text
DevicePolicyManager
  -> deterministic local policy engine
  -> Room and local event queue
  -> optional Flask synchronization
  -> PostgreSQL
```

No frontend module imports Android code, SQLAlchemy, a PostgreSQL driver or a
Supabase client. Cloud connectivity is therefore not introduced into Android
policy enforcement.

### Backend contract readiness

The frontend uses the verified `/api/v1` administrator routes:

| Workflow | Method and route | Frontend behavior |
|---|---|---|
| Login | `POST /admin/auth/login` | Holds returned Bearer token in memory. |
| Current identity | `GET /admin/auth/me` | Verifies the token and loads current permissions. |
| Logout | `POST /admin/auth/logout` | Attempts server revocation, then always clears local state. |
| Devices | `GET /admin/devices` | Server pagination and status filter. |
| Device detail | `GET /admin/devices/{uuid}` | Device and synchronization state. |
| Current assignment | `GET /admin/devices/{uuid}/policy-assignment` | Shows the authoritative active assignment. |
| Policies | `GET /admin/policies` | Server pagination and status filter. |
| Policy detail/revisions | `GET /admin/policies/{uuid}` and `/revisions` | Read-only immutable revision history and payload. |
| Assign/clear | `POST /admin/devices/{uuid}/policy-assignment[/clear]` | Permission-gated, reason-bearing mutation followed by cache invalidation. |
| Enrollment tokens | `GET/POST /admin/enrollment-tokens` | Lists, issues and displays the pairing secret once. |
| Revoke enrollment token | `POST /admin/enrollment-tokens/{uuid}/revoke` | Permission-gated reason-bearing revocation. |
| Revoke credential | `POST /admin/devices/{uuid}/credentials/revoke` | Permission-gated active credential revocation. |
| Audit events | `GET /admin/audit-events` | Server pagination and event-type filtering. |

No backend route exists for browser policy creation or administrator-account
management. Those screens were not invented. Administrator management remains
available through the existing controlled backend workflow.

### Dependency audit

`npm ci` installed 324 total packages from the committed lockfile. The direct
frontend runtime dependencies resolved as follows on 11 September 2026:

| Dependency | Resolved version | Purpose |
|---|---:|---|
| React / React DOM | 19.3.0 | Component runtime and rendering |
| React Router DOM | 7.18.3 | Protected routes and SPA navigation |
| Vite / React plugin | 8.3.0 / 6.1.1 | Build and development server |
| TypeScript | 6.0.3 | Static type checking |
| TanStack Query | 5.102.8 | API request state and mutation invalidation |
| Axios | 1.20.0 | HTTP client, timeout and interceptors |
| Zod | 4.6.2 | Runtime API response validation |
| Base UI React | 1.8.0 | Accessible modal dialog primitive |
| Tailwind CSS | 4.3.3 | Styles and responsive layout |
| Lucide React | 1.44.0 | Decorative navigation icons |
| Geist variable font | 5.3.0 | Locally bundled interface font |
| Sentry React | 10.74.0 | Optional filtered browser error reporting |

Development dependencies provide ESLint, typescript-eslint, Vitest, Testing
Library, V8 coverage, Playwright and Axe. Unused shadcn, MSW, class-variance,
class-merging, animation and user-event packages were removed. `npm audit` and
`npm audit --omit=dev` both report zero known vulnerabilities.

### Authentication and RBAC

The access token exists only in module memory. Login is not considered complete
until `/admin/auth/me` succeeds. Session expiration uses the server-supplied
token lifetime. A protected `401` clears the token, user and complete Query
cache. Logout clears local state even if server revocation is temporarily
unavailable and tells the administrator when revocation was not confirmed.

The browser never stores the Bearer token or pairing token in Web Storage,
IndexedDB or cookies. A page reload requires authentication again. This follows
the backend security design and avoids silently changing the system to cookie
authentication or Supabase Auth.

Mutation controls require the matching server permission:

- `policy.assign`
- `enrollment_token.issue`
- `enrollment_token.revoke`
- `device_credential.revoke`

The server remains authoritative and rechecks permissions on every request.

### API behavior and resilience

The shared client enforces a bounded timeout and normalizes backend structured
errors. It shows safe 4xx messages, withholds 5xx details, distinguishes network
and timeout failures, and provides retry actions for reads. Login `429`
responses use `Retry-After` when the browser can read it and otherwise apply a
60-second safe fallback. Query retries are limited to transient/network and 5xx
failures; mutations never retry automatically.

All API payloads used by the UI are checked with Zod before rendering. This
turns backend contract drift into a controlled query error instead of allowing
undefined or malformed security-relevant data into UI decisions.

### Security and privacy

- Only public values use the `VITE_*` prefix. Vite documents that these values
  are embedded into client bundles.^1
- Production API configuration requires an absolute HTTPS URL ending exactly
  in `/api/v1`; credentials, query strings, fragments and malformed paths fail
  the build.
- The production build injects an exact API/Sentry `connect-src` CSP. Vercel
  response headers also block framing, MIME sniffing and unused browser
  capabilities.
- React escapes rendered values. Policy JSON is rendered as text in a `pre`
  element; it is never inserted as HTML.
- Route parameters are URL encoded before API use.
- Sentry receives no default PII, request, user, breadcrumb, arbitrary message,
  extra data or raw exception text. Stack frame URLs lose credentials, query
  strings and fragments.
- Authentication and API responses are not intentionally cached by the
  frontend. Vercel serves hashed assets with immutable caching and other SPA
  responses with `no-store`.
- Pairing secrets are shown once, stay in component memory, support explicit
  copy, and are cleared when the dialog closes.

### Vercel compatibility

`vercel.json` uses the official Vite SPA rewrite so deep links reach
`index.html`.^2 It defines the Vite build, `dist` output and security headers.
The project root must be `frontend/school-policy-admin`, because Vercel reads
project configuration from the configured project root.^3

Vercel's current cache guidance recommends immutable caching for hashed assets
and `no-store` where content must not be cached.^4 The configuration orders the
asset rule after the general SPA rule so the more specific asset cache value is
the final value.

### Accessibility and responsive behavior

The application has semantic main, navigation, table and status/error regions;
proper labels; a keyboard skip link; focus-visible controls; Base UI dialog
focus management; reduced-motion support; and responsive desktop/mobile
navigation. Axe reports zero violations on login and authenticated dashboard in
desktop and emulated mobile Chromium.

## C. Files changed

### Application and API integration

- `src/main.tsx`, `src/App.tsx`
- `src/auth/session.ts`
- `src/context/auth-context.ts`, `src/context/AuthContext.tsx`
- `src/hooks/useAuth.ts`
- `src/services/api.ts`, `auth.service.ts`, `admin.service.ts`, `errors.ts`
- `src/schemas/api.ts`, `src/types/api.types.ts`
- `src/lib/environment.ts`, `format.ts`, `observability.ts`
- `src/components/auth/*`, `src/components/layout/*`
- `src/components/devices/EnrollmentTokensPanel.tsx`
- `src/components/ui/ActionDialog.tsx`, `AsyncState.tsx`, `Pagination.tsx`
- `src/pages/dashboard.tsx`, `devices.tsx`, `DeviceDetailPage.tsx`,
  `policies.tsx`, `PolicyDetailPage.tsx`, `logs.tsx`, `LoginPage.tsx`
- `src/index.css`, `index.html`

### Build, deployment and dependencies

- `package.json`, `package-lock.json`, `.nvmrc`, `.env.example`, `.gitignore`
- `vite.config.ts`, `vitest.config.ts`, `playwright.config.ts`
- `tsconfig.json`, `tsconfig.base.json`, `tsconfig.app.json`,
  `tsconfig.node.json`, `eslint.config.js`
- `vercel.json`
- `.github/workflows/frontend-quality.yml`
- `README.md` and this report

### Tests

- Session, environment, format, telemetry, error, HTTP client, authentication
  service, administrator service and authentication-context unit tests
- `tests/e2e/admin-flow.spec.ts` desktop/mobile browser tests

### Removed unused prototype/starter artifacts

- Vite/React demo assets and unused hero/icon assets
- Empty duplicate login page and obsolete domain types
- Unused shadcn configuration, button wrapper, class-merging helper and old
  configuration test

## D. Files intentionally unchanged

- All Android source, Gradle configuration, Room/event-queue code,
  DevicePolicyManager integration and Android tests
- Flask models, migrations and schema semantics
- Flask authentication, administrator authorization and permission constants
- Policy assignment, synchronization, device enrollment and forensic services
- API routes and OpenAPI contract
- Supabase database selection and TLS verification logic
- Railway entry point, Gunicorn configuration and `railway.json`
- Backend logging, Sentry and audit-chain implementation

No migration is required for this frontend release.

## E. Supabase changes

No Supabase code or database configuration was added to the frontend. The only
valid browser data path is through Flask. `PRODUCTION_DATABASE_URL`,
`MIGRATION_DATABASE_URL`, database passwords, project secrets and service-role
keys remain Railway/backend secrets.

The existing Supabase migration process remains unchanged. Live connectivity
and destructive migration tests require a dedicated test database and were not
run against production.

## F. Railway changes

No Railway deployment file or backend process was changed. The required manual
integration value is `ADMIN_FRONTEND_ORIGINS`, which must contain the exact
deployed Vercel HTTPS origin. Railway must continue running the existing
Gunicorn entry point.

## G. API and frontend integration changes

The starter/prototype screens now use server results instead of placeholder
counts. Every view implements loading, empty and recoverable error states.
Lists use server pagination and supported filters. Mutations send the required
reason, use immutable policy revision UUIDs and invalidate authoritative reads
after success. Active policies alone are offered for assignment, and policy
mutations are unavailable for non-active devices.

Route-level lazy loading reduced the largest production JavaScript asset from
634.02 kB to 366.76 kB minified. Detail, table, dialog and mutation code ships
as smaller on-demand chunks.

## H. Security changes

1. Memory-only administrator token and one-time pairing-token display
2. Immediate `/me` verification and protected-401 session clearing
3. Server-authoritative permission use with UI action gating
4. Strict public-environment validation and credential rejection
5. Runtime API schemas
6. Safe structured errors, 5xx redaction and bounded retries
7. Build-specific CSP and Vercel response security headers
8. Privacy-filtered optional Sentry browser telemetry
9. Immutable asset caching and non-cached SPA documents
10. Automated npm audit, unit coverage, browser and Axe CI gates

## I. Tests and exact results

All results below were produced from the working tree on 11 September 2026.

| Check | Result |
|---|---|
| `npm ci` | PASS — 323 packages added, 324 audited, zero vulnerabilities |
| `npm ls --depth=0` | PASS — no missing or invalid direct dependency |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS — zero errors and warnings |
| `npm run test:coverage` | PASS — 26 tests; 98.63% statements, 92.98% branches, 98.11% functions, 99.46% lines |
| `npm run test:e2e` | PASS — 10 tests across desktop and mobile Chromium after adding revoked-session and read-only-RBAC cases |
| Axe browser scan | PASS — zero violations on login and authenticated dashboard at both viewports |
| `npm run build` | PASS — Vite 8.3.0, 2,575 modules; largest JS chunk 366.76 kB / 117.86 kB gzip |
| `npm audit --audit-level=moderate` | PASS — zero vulnerabilities |
| `npm audit --omit=dev --audit-level=moderate` | PASS — zero vulnerabilities |
| Backend pytest/coverage | PASS — 469 passed, 38 dedicated-PostgreSQL tests deselected, 90.59% total coverage |
| Backend Ruff format/check | PASS — 87 files formatted; all checks passed |
| Backend mypy | PASS — no issues in 43 source files |
| Backend Bandit medium/high | PASS — zero medium/high findings; one accepted low-severity/medium-confidence result |
| Backend `pip check` | PASS — no broken requirements |
| Backend `pip-audit --strict` | PASS — no known vulnerabilities |
| Migration graph | PASS — one head: `e4a1b7c9d2f6` |
| Railway/Supabase/backend contract tests | PASS within the selected local suite |
| Native Gunicorn check | NOT RUN locally — Gunicorn requires Unix `fcntl`; the Linux CI check remains configured |
| Dedicated Supabase PostgreSQL integration tests | NOT RUN — no approved dedicated test database variables were available |
| Live Vercel/Railway CORS and headers | NOT RUN — no deployment exists in the verified evidence |

## J. Remaining risks

| Risk | Severity | Required closure |
|---|---|---|
| Vercel deployment and production hostname are not yet verified. | High deployment gate | Complete the deployment steps below and preserve the deployment URL. |
| Railway does not yet have a verified exact Vercel CORS origin. | High integration gate | Set `ADMIN_FRONTEND_ORIGINS`, redeploy and test allowed/denied preflights. |
| Dedicated Supabase integration/migration suite was not run in this session. | High database gate | Run the existing protected GitHub environment job against a disposable Supabase test database. |
| Linux Gunicorn startup was not executed locally. | Medium | Require the existing `backend-quality` GitHub job to pass. |
| Browser Sentry is optional and externally unconfigured. | Low | Create a dedicated frontend project, set only its public DSN, then inspect a sanitized test event. |
| Generated Vercel preview origins are not stable enough for an exact backend allowlist. | Medium | Use a stable staging custom domain for authenticated previews. |
| A browser refresh intentionally ends the in-memory session. | Accepted UX tradeoff | Keep until the backend explicitly designs a secure refresh/session mechanism. |

## K. Rollback procedure

1. Do not run a database downgrade; this frontend release has no migration.
2. In Vercel, promote the previous known-good immutable deployment, or revert
   the frontend commit and redeploy.
3. If the frontend hostname changed, restore the prior exact
   `ADMIN_FRONTEND_ORIGINS` value in Railway and redeploy Flask.
4. Clear browser site data and open a private window.
5. Verify login, device reads, policy sync and audit records through the prior
   frontend.
6. Leave Android and Supabase data unchanged.

## L. MANUAL ACTION REQUIRED

### 1. Complete protected CI gates

1. Push the branch and open a pull request.
2. Require `frontend-quality`, `backend-quality` and
   `backend-postgres-integration` checks.
3. In GitHub environment `backend-integration-test`, configure only the
   dedicated disposable Supabase test database secrets documented in the
   backend migration runbook.
4. Confirm all three checks pass. Never point destructive tests at production.

### 2. Create the Vercel project

1. Import the EduGD Git repository into Vercel.
2. Set Root Directory to `frontend/school-policy-admin`.
3. Confirm Framework Preset `Vite`, Install Command `npm ci`, Build Command
   `npm run build`, and Output Directory `dist`.
4. Set production `VITE_API_BASE_URL` to the exact Railway HTTPS URL followed
   by `/api/v1`.
5. Set `VITE_API_TIMEOUT=30000`.
6. Optionally set the public `VITE_SENTRY_DSN` and non-secret release label.
7. Confirm no database, JWT, Flask, pairing, Railway or Sentry management secret
   uses a `VITE_*` name.
8. Deploy and record the exact production origin.

### 3. Allow the frontend in Railway

1. Open the Railway Flask service.
2. Set `ADMIN_FRONTEND_ORIGINS=https://<exact-vercel-host>` without a path or
   trailing slash.
3. Add a stable staging origin with a comma only when needed.
4. Do not use `*` and do not enumerate uncontrolled preview hosts.
5. Redeploy and confirm readiness succeeds.

### 4. Verify production behavior

1. Check deep links and all Vercel security headers.
2. Send an allowed preflight with the Vercel origin and a denied preflight with
   an unrelated origin.
3. Use dedicated staging administrator/device records to test login, logout,
   expiry, denied RBAC, pagination, 429, assign, clear, token issue/revoke and
   credential revocation.
4. Confirm every mutation produces the expected audit record and Android sync
   response.
5. Confirm Android continues enforcing the last cached policy while offline.
6. Inspect browser storage and telemetry for secret absence.
7. Record results, deployment identifiers and rollback target.

## M. Recommended next frontend-integration steps

1. Complete and require the three GitHub checks.
2. Deploy a staging Vercel project and use a stable staging domain.
3. Close the exact Railway CORS and Linux Gunicorn gates.
4. Run the dedicated Supabase integration suite.
5. Perform the end-to-end staging checklist with disposable administrator,
   device, policy and enrollment-token records.
6. Promote the tested Vercel deployment to production and monitor sanitized
   frontend/backend errors.

## Readiness scorecard

| Area | Status | Evidence |
|---|---|---|
| Architecture | PASS | Correct Vercel -> Railway -> Flask -> SQLAlchemy -> Supabase boundary; Android unchanged |
| Backend/API | PASS | Verified route contracts and 469-test backend suite |
| Database | FAIL (external gate) | Schema/migration code passes locally; dedicated live Supabase suite not run |
| Authentication/RBAC | PASS | Memory session, `/me`, expiry/401/logout and permission tests |
| Security | PASS (code) | CSP, header, secret, schema, error, storage and dependency gates pass |
| Deployment | FAIL (external gate) | Vercel/Railway deployment and Linux Gunicorn result not observed |
| Frontend integration readiness | PASS | Complete implemented UI, API client, build, unit and browser checks |
| Rate limiting | PASS | Backend limits preserved; frontend 429 block/fallback verified |
| Logging/error tracking | PASS (code) | Backend unchanged; frontend Sentry scrubber tested; live DSN optional |
| Forensic/audit integrity | PASS | Backend audit implementation unchanged; regression tests pass |

## Final verdict

**FAIL — NOT READY**

The production frontend implementation is complete and ready for staged
integration. The system cannot receive the repository-wide PASS verdict until
the dedicated Supabase test job, Linux CI, Vercel deployment, exact Railway
CORS configuration and live staging checks pass.

## Sources

1. Vite, “Environment Variables and Modes,” accessed 11 September 2026,
   https://main.vite.dev/guide/env-and-mode
2. Vercel, “Vite on Vercel,” accessed 11 September 2026,
   https://vercel.com/docs/frameworks/frontend/vite
3. Vercel, “Static Configuration with vercel.json,” updated 19 December 2025,
   https://vercel.com/docs/project-configuration/vercel-json
4. Vercel, “Cache-Control headers,” updated 5 March 2026,
   https://vercel.com/docs/caching/cache-control-headers
5. Playwright, “Continuous Integration,” accessed 11 September 2026,
   https://playwright.dev/docs/ci
6. Playwright, “Browsers,” accessed 11 September 2026,
   https://playwright.dev/docs/browsers
