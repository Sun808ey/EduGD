# Step 5: private configuration handoff

> Historical deployment note: this sealed-variable record describes the
> `e4a1b7c9d2f6` / 18-table deployment snapshot. The current repository head is
> `d8f1a3c6e9b2`; do not use the historical table count as a current migration
> expectation.

The broader setup now follows [the corrected workbook execution record](setup-workbook-reconciliation.md).
Browser control and both projects' SSL/Data API checks now pass. Staging is
now migrated to `e4a1b7c9d2f6`, with restricted runtime grants and RLS policies
verified in the catalog. The encrypted owner handoff passed; no replacement is
needed. The hosted runtime database connection and staging API health/readiness
now pass. Staging administrator bootstrap, frontend deployment and authenticated
browser checks are independently verified; do not repeat them. Production
migration and runtime database security are also complete: head
`e4a1b7c9d2f6`, 18 expected tables, 126 permission checks, RLS on all tables,
18 runtime-only policies and Data API roles denied. Production API runtime
connectivity, public readiness, Vercel deployment and browser login-page checks
now pass. This document preserves the sealed-variable handoff record; it is
not a pending provider-configuration checklist. Android offline-device
acceptance remains outside this web/backend rollout.
The owner has authorized continued implementation. Never send credential values
in chat or commit them to Git.

## 1. Confirm existing data and key ownership

Owner-confirmed checkpoint:

- Installation: fresh.
- Staging application data: absent (owner confirmation).
- Production application data: absent (owner confirmation).
- Owner reports `PRODUCTION_DATABASE_URL`, `PAIRING_TOKEN_PEPPER_VERSION`,
  `DEVICE_ENROLLMENT_MODE` and `ENROLLMENT_ADMIN_ENABLED` entered in both
  environments, with separate `edug_runtime` passwords. Values were not disclosed.
- The owner subsequently confirmed all entries are saved and sealed. The
  saved-versus-pending manual checkpoint is satisfied by that confirmation.
  Do not unseal, overwrite or request re-entry merely to make CLI reads work.
- Earlier independent CLI verification was incomplete: staging listed these names plus
  Redis/signing/audit/pairing secret names, but the value check could not validate
  their contents. Production's name inventory lists only the previously applied
  non-secret settings and Railway-generated variables, not the four reported
  additions. Retain that inventory as a limited observation, not proof of missing
  secrets. Sealed entry confirmation does not independently validate contents.
- The owner supplied `PAIRING_TOKEN_PEPPER_VERSION=1`,
  `DEVICE_ENROLLMENT_MODE=legacy` and `ENROLLMENT_ADMIN_ENABLED=false`, interpreted
  as applying to both environments in the preceding confirmation. Local parsing
  verified integer 1, mode legacy and boolean False. These are supported settings;
  this is not independent readback of sealed provider values.
- Database target/TLS/role and password separation remain unverified
  independently. No database connection was made.
- No credential values disclosed; sources remain unconnected; no deployment
  or migration started (owner confirmation).

The installation/data questions are answered. Do not request existing deployment
settings as though this were a migration. The initial enrollment settings are
now supplied and their local parsing is verified.
Fresh independent signing/audit/pairing keys may be generated as described below.

The policy-input checkpoint is satisfied. Keep the Railway entries sealed.
In `legacy` mode, device routes that allow legacy access bypass the signed-device
authentication requirement; this does not enforce enrollment on those routes.
`ENROLLMENT_ADMIN_ENABLED=false` disables enrollment-token issuance; it does not
disable the entire administrator API. Version 1 identifies the initial pairing
pepper version and is not the pepper secret. These behaviors follow
[`device_authentication.py`](../app/services/device_authentication.py),
[`device_enrollment.py`](../app/services/device_enrollment.py) and
[`config.py`](../app/config.py). No policy change was made.
All 33 existing tests in `test_device_enrollment_authentication.py` and
`test_enrollment_token_issuance.py` passed locally. These cover multiple enrollment
modes and do not establish live Railway authentication or connectivity.

Content/TLS/role verification remains
pending through an approved execution context that can consume sealed values
without printing them; saving variables alone does not pass the deployment gate.

Evidence: owner confirmation in this conversation and authenticated Railway CLI
variable-name inventory with captured values suppressed. These establish the
reported saved/sealed entry and earlier visibility limitation only, not hosted
connectivity or grants. No provider mutation or network database probe was made
to resolve this checkpoint.

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
- For this fresh installation, select initial `PAIRING_TOKEN_PEPPER_VERSION`,
  `DEVICE_ENROLLMENT_MODE` and `ENROLLMENT_ADMIN_ENABLED` settings after reviewing
  enrollment behavior. These are not existing settings to recover. Do not infer
  the intended policy from `.env.example`.

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
