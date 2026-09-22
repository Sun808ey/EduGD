# EduG administrator frontend

This React and Vite single-page application is the browser administration
client for the existing Flask REST API. Flask remains the business,
authentication, RBAC, policy, synchronization and audit authority. The browser
never connects to Supabase directly.

The Android application is outside this frontend. Its offline-first policy
engine, Room data and event queue continue operating without cloud
connectivity.

## Supported administration workflows

- Administrator login, identity verification, expiry handling and logout
- Permission-aware policy assignment and clearing
- Device list and device detail
- Active device credential revocation
- Policy list, policy detail and immutable revision history
- Enrollment-token list, issue, one-time display and revocation
- Audit-event list and filtering
- Structured API errors, pagination, retry actions and login rate limiting

There are no browser screens for creating policies or managing administrator
accounts because the current Flask API does not expose those contracts. Do not
invent client-only behavior for them.

## Security model

The Flask API issues an administrator Bearer token. The frontend keeps that
token in JavaScript module memory only and immediately verifies it through
`GET /admin/auth/me`. It never writes authentication or pairing credentials to
`localStorage`, `sessionStorage`, IndexedDB or cookies. Reloading the page
therefore requires a new login.

UI permission checks improve usability; they never replace server-side RBAC.
Every protected request carries `Authorization: Bearer <token>`, and any
protected `401` clears the local session and cached API data. Pairing tokens are
shown only in the issue dialog and are not persisted by this client.

Production builds validate the public API URL and inject a restrictive
build-specific CSP `connect-src`. Vercel adds response-level CSP, anti-framing,
MIME sniffing, referrer, permissions, opener and resource-policy headers.
Browser telemetry strips request, user, breadcrumb, arbitrary exception and
extra data before transmission.

## Prerequisites

- Node.js 24
- npm 11
- A running EduG Flask backend for interactive development
- Playwright Chromium for browser tests

The required Node and npm ranges are recorded in `.nvmrc` and `package.json`.
Install the exact locked tree:

```powershell
cd E:\EduG\frontend\school-policy-admin
npm ci
npx playwright install chromium
```

On Linux CI, install the browser and operating-system dependencies with:

```bash
npx playwright install --with-deps chromium
```

## Public environment variables

Copy `.env.example` to `.env.local` only when local overrides are needed.

| Variable | Required | Meaning |
|---|---:|---|
| `VITE_API_BASE_URL` | Production | Absolute HTTPS Railway API URL ending in `/api/v1`; leave blank locally to use the Vite proxy. |
| `VITE_API_TIMEOUT` | No | Request timeout from 1000 through 60000 ms; default is 30000. |
| `VITE_SENTRY_DSN` | No | Public HTTPS browser-ingest DSN. This is not a Sentry auth token. |
| `VITE_APP_RELEASE` | No | Public release label used to group browser errors. |

Vite embeds every `VITE_*` value in browser assets. Never place any of these in
a `VITE_*` variable:

- Supabase or PostgreSQL URLs, passwords, pooler credentials or service keys
- Flask `SECRET_KEY` or JWT signing key
- audit, synchronization or pairing-token secrets
- Railway tokens
- Sentry authentication or management tokens

## Local development

1. Start the Flask backend on `http://127.0.0.1:5000`.
2. Keep `VITE_API_BASE_URL` blank.
3. Ensure the backend development `ADMIN_FRONTEND_ORIGINS` contains the exact
   Vite origin, normally `http://localhost:5173` and/or
   `http://127.0.0.1:5173`.
4. Run `npm run dev`.

The Vite proxy sends `/api` requests to the local Flask server. Explicit HTTP
API URLs are accepted only for `localhost`, `127.0.0.1` and `::1` in
development.

## Verification

Run all local gates from this directory:

```powershell
npm ci
npm ls --depth=0
npm run typecheck
npm run lint
npm run test:coverage
npm run build
npm run test:e2e
npm audit --audit-level=moderate
npm audit --omit=dev --audit-level=moderate
```

`npm run build` requires an explicit production API URL. Set it in an ignored
`.env.production.local` file for a local production build:

```dotenv
VITE_API_BASE_URL=https://your-railway-service.example/api/v1
```

The unit coverage gate requires 90% statements, functions and lines, and 85%
branches across session, context, configuration, schemas and API services. The
Playwright suite runs the login, dashboard, navigation, storage, rate-limit and
accessibility flows on desktop and emulated mobile Chromium.

## Vercel deployment

The Vercel project must use this directory as its project root so Vercel can
read `vercel.json`, `package.json` and the lockfile.

1. Merge the reviewed frontend branch into the branch Vercel will deploy.
2. In Vercel, choose **Add New > Project** and import the EduGD repository.
3. Set **Root Directory** to `frontend/school-policy-admin`.
4. Confirm framework **Vite**, build command `npm run build`, install command
   `npm ci`, and output directory `dist`.
5. Add `VITE_API_BASE_URL` with the exact public Railway HTTPS API URL and
   `/api/v1` suffix for Production. Add the same value to Preview only when the
   preview deployment should call that backend.
6. Add `VITE_API_TIMEOUT=30000`.
7. Optionally add the public `VITE_SENTRY_DSN` and a non-secret
   `VITE_APP_RELEASE`.
8. Deploy. Confirm `/login`, `/dashboard`, `/devices/<uuid>` and
   `/policies/<uuid>` all return the SPA rather than Vercel 404 responses.
9. Copy the final Vercel production origin, without a path or trailing slash.
10. In Railway, set backend `ADMIN_FRONTEND_ORIGINS` to that exact origin. If a
    stable staging frontend is used, append its exact HTTPS origin separated by
    a comma. The backend intentionally rejects wildcards.
11. Redeploy Railway, then verify an allowed CORS preflight and a denied origin
    before using real administrator credentials.

Generated Vercel preview hosts change. Use a stable custom staging domain when
preview builds need authenticated backend access, then allow only that exact
origin in Railway.

## Post-deployment checks

From a private browser window:

1. Open a deep link such as `/devices/<known-device-uuid>` and confirm the login
   redirect preserves the requested path.
2. Sign in with a dedicated staging administrator.
3. Confirm dashboard totals, device/policy lists and audit events load.
4. Confirm actions appear only for granted permissions and that the backend
   returns `403` when a deliberately underprivileged test account attempts a
   forbidden request.
5. Trigger a failed login rate limit in staging and confirm the form blocks
   repeat submissions.
6. Issue and immediately revoke a staging enrollment token; confirm the pairing
   value appears once and is absent after reload.
7. Assign and clear a test-device policy, then confirm Android synchronization
   and the forensic audit records remain correct.
8. Revoke a test-device credential and confirm re-enrollment is required.
9. Check response security headers and verify the browser console contains no
   CSP or CORS errors.
10. Reload after login and confirm a new login is required; verify browser
    storage contains no credential material.

## Rollback

Vercel deployments are immutable. If a release fails verification, promote the
last known-good Vercel deployment or revert the frontend commit and redeploy.
Restore the previous `ADMIN_FRONTEND_ORIGINS` value in Railway only if the
frontend hostname changed. Frontend rollback does not require a database
migration and must not alter Android offline enforcement.
