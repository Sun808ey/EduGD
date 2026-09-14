# Step 5: private configuration handoff

Step 5 is incomplete. Steps 6 and 7 have not started. The owner authorized the
remaining implementation with zero-cost services only; no further blanket
approval is needed. Credentials and existing-data facts still require private
operator input. Never send credential values in chat or commit them to Git.

## 1. Confirm existing data and key ownership

Report only whether this is a fresh installation or a migration from an existing
EduG installation, whether either Supabase project contains application data,
and the current enrollment mode/admin-enabled state. If migrating, retain
existing signing/audit/pairing keys and identify the source privately; do not
generate replacements or run migrations until inventory/recovery checks pass.
If these facts are unknown, stop here and report that rather than guessing.

## 2. Supply runtime secrets privately

In Railway project `blissful-luck`, select each exact environment and API:

| Environment | Environment ID | Service |
| --- | --- | --- |
| Staging | `a8928189-e7bb-46be-8788-856816caecd0` | `edug-api-staging` |
| Production | `48e80896-15ef-4616-837e-d59240fc503a` | `edug-api-production` |

Keep source unconnected and do not deploy. Use the Variables editor privately
or the authenticated CLI with `--stdin` and `--skip-deploys`; never place secret
values in command arguments/history. Supply only already-established credentials:

- `REDIS_URL`: the approved store's authenticated TLS URL. Staging host/port is
  `set-mayfly-105830.upstash.io:6379`; production is
  `edug-redis-production-edug-production.a.aivencloud.com:22050`.
  Use `rediss://`, database 0 and no query overrides. Preserve and URL-encode
  credentials correctly; changing Aiven's scheme must not change its credentials.
- `PRODUCTION_DATABASE_URL`: runtime-role URL for staging Supabase
  `dviuaqtlbuefmfmswwqt` or production `hszskxrgkptbytuquyfu`, respectively.
  Both APIs use this variable name because both use production hardening.
  Use `sslmode=verify-full` and the reviewed CA trust path when needed. Do not
  substitute an owner/admin URL for a missing least-privilege runtime role.
- `SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_AUDIT_PSEUDONYM_KEY`,
  `POLICY_SYNC_AUDIT_KEY` and applicable `PAIRING_TOKEN_PEPPER`: preserve existing
  values when data or clients depend on them. For a confirmed fresh installation,
  create independent cryptographically random values in a password manager,
  each at least 32 characters; do not reuse values across keys or environments.
- Preserve the verified `PAIRING_TOKEN_PEPPER_VERSION`, `DEVICE_ENROLLMENT_MODE`
  and `ENROLLMENT_ADMIN_ENABLED` settings. Do not infer them from `.env.example`.

If runtime roles, CA trust or required existing keys are not yet available,
report the missing names only. Those prerequisites must be resolved before
configuration can pass; this handoff does not ask you to improvise role SQL.
Keep migration-owner credentials in the private operator/migration environment,
not the API runtime. Do not add development/test URLs or override Railway's
generated environment ID. Do not enter backend secrets into Vercel.

## 3. Confirm completion without values

Confirm which environments have their available secrets entered, list missing
variable names only, and give the non-secret installation/data/enrollment facts
from step 1. The agent can then validate assignments without printing values,
finish roles/TLS/API URLs and configure Vercel `VITE_API_BASE_URL` against the
verified endpoints. No hosted migration should occur during this handoff.

Before staging deployment, also reconcile pending-deletion Railway volumes and
current recurring Free allowance. Temporary Trial credits do not demonstrate
ongoing zero cost. Keep both API deployments stopped until step 5 passes.

Repository publication remains the owner's task. The local workflow/guard changes
must be on the reviewed deployment revision before source deployment; the old
hosted PostgreSQL workflow is currently disabled remotely.
