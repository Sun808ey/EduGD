# Reviewed Railway deployment settings

Prepared for the existing empty staging and production APIs. Apply through
supported dashboard settings; new services cannot rely on legacy `railway.json`.
The legacy JSON is retained as a reference, with automatic migrations removed.
Do not attach source or start a deployment until the preceding gates pass.

Applied so far: both services have verified `APP_ENV`, `EDUG_ENVIRONMENT`,
`FLASK_APP`, `FLASK_DEBUG`, `ADMIN_FRONTEND_ORIGINS` and pool settings through
the CLI with `--skip-deploys`. Both remain offline. The build/start/healthcheck
settings below are prepared, not yet verified on the services. See the
[private configuration handoff](private-environment-configuration.md).

| Setting | Both API services |
| --- | --- |
| Repository root | `/backend` |
| Builder | Railpack, Python 3.12 |
| Build command | `pip install --requirement requirements.txt` |
| Start command | `gunicorn --config gunicorn.conf.py run:app` |
| Pre-deploy command | None; migrations are a separate reviewed operation |
| Healthcheck | `/api/v1/ready`, timeout 120 seconds |
| Replicas | 1 |
| Restart | On failure, maximum 3 retries |
| Gunicorn | 1 worker, 4 threads, timeout 30 seconds |
| Database pool | Set `SQLALCHEMY_POOL_SIZE=1`, `SQLALCHEMY_MAX_OVERFLOW=0` initially |
| Automatic source deployments | Hold until environment-specific verification |

`run.py` now validates deployment identity before creating a production app.
Set `APP_ENV=production` in both environments for production hardening, and set
`EDUG_ENVIRONMENT` to `staging` or `production` respectively. The platform-provided
`RAILWAY_ENVIRONMENT_ID` must match the pinned resource map. Never override that
platform identity to make an incorrectly assigned service pass.

Each environment's `PRODUCTION_DATABASE_URL` must use its own assigned Supabase
project and verify-full TLS. If present, `MIGRATION_DATABASE_URL` must match that
same project and database, using the separate migration role. Keep test and
development database URLs absent. `REDIS_URL` must use the exact assigned host,
port and authenticated `rediss://` scheme, without query overrides.
`ADMIN_FRONTEND_ORIGINS` must be the single exact assigned HTTPS frontend origin.

Other application signing, audit and pairing keys remain required by existing
production validation. Supply them privately; never include them in this file,
build arguments, frontend variables or tool output. Preserve existing keys if
data or clients already depend on them. A new deployment does not authorize
silently rotating or replacing such keys.

Before step 6, record source/destination inventory, schema status, runtime role
privileges, backup/recovery needs and migration plan under the migration runbook.
Run reviewed migrations explicitly, never as an incidental image build or API
restart. The guarded entry point applies to `flask --app run.py` as well as
Gunicorn. Do not run the destructive integration suite against either project.

Free-only acceptance additionally requires actual startup resource/egress usage
and remaining Railway allowance. Redis provider Free plans do not establish that
two always-running APIs fit Railway's recurring Free allowance. Stop before paid
upgrades or overages; if resources cannot fit, report the gate as unmet.

References: [Railway Config as Code](https://docs.railway.com/config-as-code),
[Railway Infrastructure as Code](https://docs.railway.com/infrastructure-as-code).
