# EduG administrator frontend foundation

React/Vite calls the existing Flask REST API. This checkout still contains the starter UI; authenticated administrator screens are not implemented.

## Local development

1. Use Node 24 and run `npm ci` in this directory.
2. Copy `.env.example` to `.env.local`. Leave the API URL unset for the Vite `/api/v1` proxy to Flask at `http://127.0.0.1:5000`, or supply an explicit development API URL.
3. Start Flask using the backend environment documentation, then run `npm run dev`.
4. Run `npm test`, `npm run lint`, and `npm run build` for configuration tests, lint, TypeScript and bundling. Builds require the production API URL below.

## Production build configuration

Set `VITE_API_BASE_URL=https://<verified-api-host>/api/v1` in the frontend build environment before running `npm run build`. Serve `dist` over HTTPS. Vite embeds these values at build time; changing them requires rebuilding. Configure the exact frontend HTTPS origin in the backend `ADMIN_FRONTEND_ORIGINS` allowlist.

`VITE_SENTRY_DSN` is optional and must be a public HTTPS browser DSN. Error events exclude user/request context and arbitrary exception messages. Backend Sentry configuration remains independent.

Every `VITE_*` value is public. Never place database URLs, passwords, JWT signing keys, pairing peppers, private keys or Sentry management tokens in these variables. The browser does not connect to Supabase. The CI placeholder API URL is for validation only; do not deploy that artifact.

## API integration work remaining

Use [OpenAPI](../../backend/docs/openapi.json), backend route tests and [environment guidance](../../backend/docs/environment.md) together. The OpenAPI document is a route/contract outline, not complete generated-client schemas.

Implement login/logout/current administrator against `/admin/auth/*`, using the existing Bearer token and server permissions. Never substitute Supabase Auth. Design token handling before introducing persistent browser storage; avoid logging or putting tokens in URLs. Handle expiration, revoked sessions, permission failures, pagination, structured `error.code`/`error.message`, and HTTP 429. Add browser integration tests for those flows and production CORS.

Implement devices, policies, enrollment and audit screens against existing administrator routes. Device registration, signature/nonce authentication and policy synchronization belong to the Android protocol; do not make administrator UI changes to those contracts. Android offline enforcement is external to this checkout and requires separate device testing.

Deployment, migration rehearsal and rollback prerequisites are in the [migration runbook](../../backend/docs/database-migration-runbook.md).
