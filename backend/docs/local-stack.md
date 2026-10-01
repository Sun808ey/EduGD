# Disposable local Flask and Vite stack

This procedure runs the host Flask and Vite applications against a disposable
local PostgreSQL 17 container. It does not access Supabase, Railway, Redis
providers, Vercel, or production resources.

The launcher creates a fresh process-local database password, starts the
database on `127.0.0.1:55432`, applies the repository migrations, starts Flask
on `127.0.0.1:5000`, waits for `/api/v1/ready`, starts Vite on
`127.0.0.1:5173`, and uses the Vite proxy for `/api` requests. The password is
never written to a file or printed. The database uses tmpfs and is removed on
exit.

## Prerequisites

- Python 3.12 with backend development dependencies installed.
- Node.js and npm versions required by the frontend `package.json`.
- `npm ci` already completed in `frontend/school-policy-admin`.
- Docker Desktop or a compatible Docker engine running.

## Start the stack

From `backend`:

```powershell
python scripts/local_stack.py
```

Then open `http://127.0.0.1:5173/login`. The API base is
`http://127.0.0.1:5000/api/v1`; the browser reaches it through the Vite
development proxy. Press `Ctrl+C` to stop Flask and Vite and remove only the
`edug-local-stack` containers, network, and disposable volume.

The launcher accepts `--backend-port`, `--frontend-port`, and `--postgres-port`
when an explicitly verified local port is unavailable. It does not silently
select a different port.

## Smoke verification

Run this from `backend` to start the complete stack, verify PostgreSQL
migrations, Flask readiness, and Vite login delivery, then clean up:

```powershell
python scripts/local_stack.py --smoke
```

The smoke command is not administrator lifecycle evidence. Administrator
fixtures and credentials must be created by the approved local test harness or
operator procedure; real credentials must not be placed in this document.

## Safety boundaries

- The existing `compose.postgres-test.yml` remains the isolated PostgreSQL
  integration/concurrency test path and is not changed by this procedure.
- The local compose file publishes PostgreSQL only on loopback and stores data
  in tmpfs.
- The launcher uses a unique Compose project name and removes only that
  project during cleanup.
- No hosted database URL, provider token, Redis credential, Sentry credential,
  private key, or production variable is required.
- If Docker, dependencies, migrations, readiness, or Vite startup fails, the
  launcher exits and reports the failed gate; it does not fall back to a
  hosted resource or continue against an unknown target.
