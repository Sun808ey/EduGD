# EduG administrator frontend

This React and Vite single-page application uses the existing Flask REST API.
The browser never connects directly to Supabase and must never receive database
credentials, Flask secrets, JWT signing keys, pairing peppers, or management
tokens.

## Prerequisites and installation

Use Node 24 LTS and npm 11. The repository records these requirements in
`.nvmrc` and `package.json`.

```powershell
cd E:\EduG\frontend\school-policy-admin
npm ci
```

`npm ci` installs the complete locked dependency tree. Do not install backend,
PostgreSQL, Supabase, Railway, or Android packages in this directory.

## Local development

1. Copy `.env.example` to `.env.local` if you need to override the defaults.
2. Start the Flask backend on `http://127.0.0.1:5000`.
3. Run `npm run dev`.

Leave `VITE_API_BASE_URL` blank to use Vite's `/api/v1` proxy. It may use HTTP
only for `localhost`, `127.0.0.1`, or `::1` during development. An explicit URL
must end in `/api/v1`.

## Production build

Set an explicit HTTPS Flask API URL before building:

```powershell
$env:VITE_API_BASE_URL = 'https://<approved-api-host>/api/v1'
npm run build
```

Serve `dist` over HTTPS and configure its exact public origin in the backend
`ADMIN_FRONTEND_ORIGINS` allowlist. Vite embeds `VITE_*` values into public
browser assets, so these variables may contain public configuration only.

Supported public variables:

- `VITE_API_BASE_URL`: required for production and restricted to an absolute
  HTTPS URL ending in `/api/v1`.
- `VITE_API_TIMEOUT`: optional request timeout in milliseconds.
- `VITE_SENTRY_DSN`: optional public browser ingest DSN. Never use a Sentry
  authentication or management token here.

## Verification

Run the same checks required by CI:

```powershell
npm ci
npm ls --depth=0
npm run test
npm run lint
$env:VITE_API_BASE_URL = 'https://api.example.invalid/api/v1'
npm run build
npm audit --audit-level=moderate
npm audit --omit=dev --audit-level=moderate
```

The API client attaches the existing administrator Bearer token. Supabase Auth
must not replace the Flask authentication and RBAC contracts.
