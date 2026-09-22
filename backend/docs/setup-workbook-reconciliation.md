# EduGD backend and frontend setup

This execution record reconciles the supplied `inter.md` workbook with the
approved September 2026 configuration. It describes a personal, non-commercial
undergraduate proof of concept for offline-first phone-policy enforcement on
school-owned Android devices in Ugandan secondary schools. It is not evidence
of operational readiness for a school or of completed Android enforcement.

The current authorization covers implementation and verification within Free
plans. The instruction to leave commits and pushes to the owner remains in
force. Workbook instructions are reference material; they do not override the
current two-project, zero-cost and secret-protection requirements.

## Corrections to the reference workbook

| Workbook instruction or conflict | Applied decision |
| --- | --- |
| Separate hosted integration project | Use the existing isolated Docker PostgreSQL stack. Never run destructive tests against either approved Supabase project. |
| Railway private Redis | Use approved Upstash Free staging and Aiven Free Valkey production through authenticated, verified TLS. |
| Existing database verification or source transfer only | Add a fresh-installation path: inspect the empty target, run reviewed Alembic upgrades, apply restricted grants and verify. No dump/restore from a nonexistent source and no manual revision stamping. |
| New services use `/backend/railway.json` | Use supported dashboard configuration or reviewed Railway IaC. New services cannot opt into deprecated Config as Code.[1] |
| Automatic pre-deploy migrations | Keep automatic migrations disabled. Run migration-owner DDL explicitly after target/security checks, separately from the runtime API. |
| Pin Python 3.12.10 | Use a verified supported Python 3.12 patch; the isolated runner passed on 3.12.14. Confirm the hosted build version. |
| Pool size 3, overflow 2 | Retain reviewed pool size 1, overflow 0 initially; measure capacity and deployment overlap. |
| Read sealed credentials through CLI | Sealed values are available to builds/deployments, not CLI variable retrieval or `railway run`. Validate inside an approved execution context; never overwrite them because CLI output is empty.[2] |
| Record the last four secret characters | Record names and pass/fail evidence only, with no secret fragments. |
| Enrollment tests require issuing tokens while administration is disabled | Keep the selected `legacy`/`false` policy. Verify issuance is denied in that configuration; token lifecycle coverage belongs to isolated tests with enrollment enabled. Do not claim live issuance passed. |
| Free capacity or Trial balance proves sustainable zero cost | Verify actual recurring allowance, usage and plan enforcement before compute starts. Free has $1 monthly credit; resource usage is metered. Trial credits are not proof that both APIs can run continuously for free.[3] |
| Android offline checks can be inferred from backend tests | Require actual managed-device evidence. This checkout contains no Android implementation. |

Vercel Hobby eligibility rests on the confirmed personal, non-commercial nature
of the project, consistent with its current plan restrictions.[4]

## Current execution evidence

### Staging frontend deployment

Vercel CLI authentication restored. Deployment
`dpl_DL8mnqv57ZfiS4kbTVUcAjHy9GzT` reached READY in `sun-g/edug-admin-staging`.
It used an isolated archive of the tracked frontend, linked only to project
`prj_8FoiuHbud8Q0nKCPxxNWfPUKT3Tu`. Remote `npm ci` and TypeScript/Vite build
passed; npm reported zero vulnerabilities. No commit or push was performed.

`https://edug-admin-staging.vercel.app/login` returns 200 and renders the
administrator login form in Sun Chrome. The public bundle contains the exact
staging API `/api/v1` URL. CSP is present and Cache-Control is `no-store`.
The CLI additionally reported the project's existing `project-irlim.vercel.app`
alias; use only the approved staging domain for CORS-compatible verification.

Historical manual gate: staging sign-in subsequently passed. Authentication,
dashboard API calls, RBAC and logout are recorded in the staging authenticated
acceptance section below. Production rollout subsequently passed and is
recorded in the current-production status.

### Staging authenticated acceptance

PASS on 15 September 2026. An authenticated browser session showed the
bootstrap administrator, dashboard counts of zero devices and policies, and
the expected administrator authentication audit history. Devices, policies and
audit pages loaded their empty fresh-installation collections. Staging enrollment
token issuance was deliberately attempted with a non-secret test reason and
returned `operation is not available`; source review confirms the disabled
setting is checked before token generation or database writes. Logout returned
the browser to `/login`, confirming that the protected frontend session was
cleared. No device, policy, enrollment token or credential was created.

Android offline acceptance remains unverified. This checkout has no Android
Gradle project or wrapper, and `adb` is unavailable on this workstation, so no
emulator/device installation, airplane-mode, restart or queued-event replay
claim is made. This limitation must be resolved with an actual managed Android
device and the Android implementation before the academic proof of concept can
claim device-policy enforcement evidence.

Historical production gate: the separate production migration-owner handoff,
schema migration and runtime-security procedure subsequently passed. Staging
credentials were not reused.

### Staging schema and permissions continuation

Latest gate: PASS. Probe `cc734c53-015e-46ae-8116-07d58cd59264` verified
deployment identity, application/Redis startup, runtime database role and TLS,
revision, table reads and readiness. Earlier CA failures were resolved by
including the reviewed public PEM in the isolated upload and explicitly
allowing its exact path in `.dockerignore`; Gunicorn configuration is now
included too. No credential or sealed URL was changed.

Staging API deployment `7e5c7c43-2c34-4719-afc8-b132b6eb81f9` reached SUCCESS.
HTTPS `/api/v1/health` and `/api/v1/ready` both returned 200 at
`https://edug-api-staging-staging.up.railway.app`. Allowed staging-origin CORS
preflight returned 204 with the exact origin; an untrusted origin returned 403
without an allow-origin header. One worker, no migration hook, restart NEVER
and serverless sleeping are configured. Trial credits funded this bounded
verification; sustainable recurring Free capacity remains a separate gate.

Ignored local inventory `staging-after-migration-20260915.json` completed with
verified TLS, expected head, no missing application tables and zero existing
revision/assignment/synchronization chains. This is fresh-schema verification,
not evidence of successful audit replay with real device events.

Vercel `edug-admin-staging` now has Production-scoped config variable
`VITE_API_BASE_URL=https://edug-api-staging-staging.up.railway.app/api/v1`.
Here Production is the Vercel environment inside the staging-only project.
Administrator bootstrap is owner-confirmed and independently verified by
read-only staging counts: one administrator, five permissions (matching the
current `ADMINISTRATOR_PERMISSIONS` set), and one bootstrap audit event.
No password or password verifier was read. Frontend deployment and
authenticated browser verification subsequently passed.

The verified owner connection applied the existing Alembic chain to
`e4a1b7c9d2f6`; 18 public tables now exist. A separate grants transaction
committed after 126 table-permission checks. Runtime schema/database CREATE is
denied, append-only tables lack UPDATE/DELETE/TRUNCATE, and `anon`,
`authenticated` and `service_role` lack table access.

Supabase automatically enabled RLS on all 18 tables. Explicit
`edug_backend_runtime` policies now allow only the dedicated `edug_runtime`
role through RLS; the narrower SQL grants still constrain permitted operations.
This server role relies on Flask's administrator/device authorization, not
Supabase Auth claims. No browser/API role received a policy or grant. Future
tables require a separate reviewed privilege/policy decision.

The first grants transaction rolled back because this migration owner cannot
`SET ROLE edug_runtime`. Verification was changed to catalog checks without
granting extra role membership. Actual password-authenticated runtime checks
are delegated to the one-shot Railway probe using the existing sealed variables.

One-shot staging deployment `4b833691-0007-425a-8080-b3cec8525b16` built and
passed application startup, but failed database verification. Follow-up probe
`4fd5540e-da5c-4990-838e-b5c0bdbd67a6` separates connection, role, TLS, revision
and read-permission stages, emitting only fixed diagnostic codes.
It uses tracked backend source at the reviewed commit plus the local
`scripts/verify_hosted_environment.py` probe and reviewed public CA. No encrypted
handoff or owner credential is included. The start command runs the probe and
exits; restart policy is NEVER, no public domain was created, no API listener
starts and no migration hook runs. It is diagnostic evidence, not the final
application release. The later PASS and application deployment above supersede
these earlier diagnostic failures.

Latest continuation supersedes the earlier browser interruption below:

- Browser control restored. Staging SSL enforcement is on; its Data API is disabled.
- Production SSL enforcement was off, was enabled through its confirmation
  dialog, and the resulting switch was verified on. Production Data API is disabled.
- A read-only staging SQL transaction returned database `postgres`, inspection
  role `postgres`, PostgreSQL 17.6, zero public tables and no Alembic table.
- `edug_runtime` exists with LOGIN; SUPERUSER, CREATEDB, CREATEROLE, REPLICATION
  and BYPASSRLS are all false. Password correctness, object grants after schema
  creation and Railway-to-database TLS remain separate pending checks.
- Retrieved the public certificate from the dashboard's download URL into
  ignored `backend/operator-evidence/supabase-ca.crt`. It contains a CA certificate
  and no private key, subject/issuer `Supabase Root 2021 CA`, expiry
  `2031-04-26T10:56:53+00:00`, SHA-256
  `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`.
  This establishes the downloaded trust material, not a successful database TLS
  handshake. Nothing was staged or added to a deployment image.
- No Supabase connector tools are callable in this session despite the installed
  skill. The authenticated dashboard supports inspection; the repository's
  Alembic migrations require a separately authenticated migration runner.
  No local migration-owner connection is currently available. See the private
  handoff below. No schema migration or API deployment has started.

- Reviewed local commit: `d50447b229eb9c2626a3cb7c8546a04bb585c3da`.
  Remote `feature/backend-api` matches it. Remote `main` is
  `0a5a33f6fb0cabdd81d9c172169bece4da368f26`; Phase 1's main/deployed-revision
  equality is therefore not yet satisfied. No commit, push or merge was made.
- Repository Alembic head: `d8f1a3c6e9b2`, read without a database connection. The
  separately recorded hosted head remains unchanged until the new migrations receive
  explicit approval.
- Prior local checks: 38 isolated PostgreSQL tests, 495 backend default tests,
  and subsequent 33 enrollment/authentication tests passed. Those runs are local
  evidence, not hosted grant or TLS verification.
- Both Supabase projects are owner-confirmed fresh with no application data.
  Runtime passwords are owner-confirmed separate; Railway entries are
  owner-confirmed saved and sealed. Non-secret enrollment settings are version
  1, `legacy`, administration `false`; local parsing passed.
- Staging Supabase database settings loaded on the Free organization and showed
  SSL enforcement switched off. The attempted enable action timed out, browser
  recovery failed, and its resulting state is unknown. No successful security
  change is claimed. Production SSL and both Data API settings remain unverified.
- Railway CLI reported approximately $0.46044 current resource usage and no
  workspace usage limit. This is metered usage, not evidence of an amount charged
  to a payment method. The current plan/credit balance and ongoing operating
  budget still need reconciliation before API deployment.
- Local Node is 24.19.0; default npm is 12.0.2, outside the project's npm 11
  requirement. `npm ci` and `npm run quality` passed with npm 11.12.0:
  type checking, lint, all 26 tests and the production build succeeded. Reported
  coverage was 98.63% statements and 92.98% branches for configured coverage
  targets. The frontend workflow now explicitly installs npm 11.12.0 before
  `npm ci`. Existing npm 12 user-configuration options emitted npm 11 warnings;
  the user's global settings were not changed. The build used the reserved
  `https://api.example.invalid/api/v1` target and must not be deployed as-is.
  Browser end-to-end and live API integration checks remain pending.

## Remaining sequence

1. Restore authenticated Supabase browser control. Verify staging SSL
   enforcement after the interrupted action, enable if still off and confirm
   success. Then verify production SSL and disable the unused Data API in both
   projects. SSL changes can briefly restart the database.[5][6]
2. Inspect existing `edug_runtime` roles and empty schemas, establish verified
   TLS for migration and runtime connections, and confirm the separate migration
   execution context. Do not reset existing passwords. Follow the migration
   runbook's restricted grants and inspect default privileges.
3. Apply and verify staging schema, revision, runtime permissions and audit
   invariants. Do not use the destructive integration suite on staging.
4. Verify Free-plan budget enforcement, apply supported staging deployment
   settings and deploy the reviewed revision. Verify health, readiness, actual
   PostgreSQL/Redis TLS connectivity and measured resource usage.
5. Bootstrap the staging administrator through an interactive secret-safe
   process, configure Vercel `VITE_API_BASE_URL` using the exact staging API
   `/api/v1` URL, and verify browser/CORS/authentication/RBAC/audit behavior.
6. Record Android airplane-mode, restart, queued-event replay and forensic
   duplicate-prevention evidence on an actual managed device. Unsupported
   features remain explicit gaps, not passed checkboxes.
7. Repeat the verified configuration for production, respecting the selected
   enrollment policy and independent credentials. Retain database backup/restore
   and rollback evidence appropriate to the fresh installation after writes begin.
8. The owner publishes reviewed repository changes and reconciles `main` with
   the accepted deployed revision. Complete the acceptance record only when
   hosted checks, Free-only usage and device evidence all pass.

## Immediate manual handoff

**Current manual gate: replace the production direct connection with the
IPv4 session-pooler connection.** Staging browser sign-in, Vercel sign-in and
frontend deployment are complete. Do not repeat SSH key creation,
administrator bootstrap or the staging migration-owner handoff.

The first production handoff passed local validation and was encrypted, but its
read-only connection preflight failed during DNS resolution. Supabase confirms
that this project's direct host uses IPv6 by default and identifies its free
IPv4 session pooler as `aws-1-eu-west-1.pooler.supabase.com:5432`, with owner
username `postgres.hszskxrgkptbytuquyfu`. No database connection or migration
occurred. A paid dedicated IPv4 add-on is outside the Free-only constraint.

In the owner's PowerShell, with the reviewed public CA already present locally,
run:

```powershell
& 'E:\EduG\backend\scripts\save_production_migration_handoff.ps1' -FromClipboard
```

Copy the complete session-pooler URL privately immediately before running the
command. Preserve the existing production owner password, percent-encode its
reserved characters, and append `sslmode=verify-full` plus the existing public
CA path. The helper validates the production project identity, project-qualified
owner role, database, port, verified-TLS parameters and CA path before replacing
the encrypted ignored file, then clears the clipboard. It does not connect,
migrate, deploy or change a secret. Report only `SAVED` or a redacted validation
failure.

After `SAVED`, run the following under that same Windows account. DPAPI prevents
the managed runner from decrypting the handoff directly. This helper performs
only read-only queries inside a rolled-back transaction and emits redacted JSON:

```powershell
& 'E:\EduG\backend\scripts\verify_production_migration_handoff.ps1'
```

Migration remains blocked until it reports `"production_preflight":"PASS"`
with the production database, migration-owner schema privileges, verified TLS,
zero public tables and no Alembic version table. Supabase's managed `postgres`
role is not required to expose conventional unrestricted superuser/role-creation
flags or be the literal catalog owner of a schema represented by
`pg_database_owner`; the preflight checks the effective database and schema
privileges Alembic needs instead.

**Production preflight passed.** It confirmed database `postgres`, the managed
migration owner, effective migration privileges, verified TLS, zero public
tables and no Alembic version table, using a read-only rolled-back transaction.
For this confirmed fresh installation, run the reviewed schema migration under
the same Windows account that owns the encrypted handoff:

```powershell
& 'E:\EduG\backend\scripts\run_production_schema_migration.ps1'
```

The helper repeats the empty-target gate immediately before Alembic, upgrades
to the current repository head `d8f1a3c6e9b2`, and verifies the metadata-derived
public table inventory. Runtime grants,
RLS policies, API deployment and frontend rollout remain blocked until this
step reports `"production_schema_migration":"PASS"`.

**Historical production schema migration passed.** The recorded deployment
applied revisions through `e4a1b7c9d2f6` using transactional PostgreSQL DDL and
found the then-current 18 public tables. For a current deployment, apply and
verify the reviewed
runtime security transaction next:

```powershell
& 'E:\EduG\backend\scripts\configure_production_runtime_security.ps1'
```

This preserves the existing `edug_runtime` password, rejects an absent or
overprivileged role, denies Data API roles, grants only the reviewed table and
sequence operations, enables RLS, and creates one `edug_backend_runtime` policy
per table. API deployment remains blocked until all 126 permission checks and
all 18 policy checks pass.

**Bootstrap completed and independently verified.** Do not rerun it. The
following commands are retained as historical operator instructions. Browser
control was restored and the subsequent Vercel frontend deployment passed.

**Previous gate: staging administrator bootstrap (15 September 2026).** The
earlier migration-owner handoff is complete; do not repeat it. Railway SSH
reported no local SSH keys, so an interactive operator connection must first
be prepared. In the owner's PowerShell, create a dedicated passphrase-protected
key outside the repository (do not overwrite an existing key):

```powershell
$edugKey = Join-Path $env:USERPROFILE '.ssh/edug-staging-operator'
New-Item -ItemType Directory -Force (Split-Path $edugKey) | Out-Null
if (Test-Path -LiteralPath $edugKey) { throw 'Key exists; do not overwrite it.' }
ssh-keygen -t ed25519 -f $edugKey -C edug-staging-operator
railway ssh keys add --key "$edugKey.pub" --name edug-staging-operator
railway ssh -p 7d0c485e-3e9f-411c-9412-af8dd6f32481 -e a8928189-e7bb-46be-8788-856816caecd0 -s 5ac7afd9-8d99-4ab6-92b8-3e4adab1f058 -i $edugKey
```

After the remote shell opens, run:

```sh
python -m flask --app run admin bootstrap --username sunday --display-name "Sunday Emmanuel Lugai" --operator "Sunday Emmanuel Lugai" --reason "Fresh staging installation"
```

Enter a unique 12–128 character administrator password twice at the hidden
prompts and store it privately. The username `sunday` is suggested and may be
changed before running. Report only `Administrator bootstrap completed.` or a
redacted error. Never send the password, private SSH key or connection URL.
This command creates the initial administrator and audited permissions; it
does not migrate the schema. If bootstrap reports it already exists, stop and
report that instead of resetting credentials. Frontend authenticated checks and
production rollout later passed; this is retained only as a historical gate.

The Vercel CLI token was invalid, but authenticated browser access worked and
the staging API base URL was saved. No Vercel login repair is currently required.

**Latest result: handoff accepted.** The clipboard helper saved the encrypted
file before Windows PowerShell rejected its empty-string clipboard-clear call.
Independent verification decrypted the saved file, validated the assigned staging
project and owner role, and connected with `sslmode=verify-full` and the configured
CA. The read-only query confirmed database `postgres`, owner `postgres`, active
TLS, zero public tables and no Alembic table. No migration was performed by this
check. Do not re-enter or replace this working credential.

The helper now clears the clipboard without a Value argument and reports save
success separately from cleanup failure. If the earlier error left the URL in
the clipboard, copy harmless text to replace it. Instructions and failed input
observations below are retained as history, not an outstanding handoff request.

Use the validating helper for the next entry:

```powershell
& 'E:\EduG\backend\scripts\save_staging_migration_handoff.ps1'
```

If pasting at the masked prompt repeatedly fails, copy the complete prepared URL
privately, then run this alternative. It reads the clipboard locally without
displaying it, validates before saving, and clears the clipboard after success:

```powershell
& 'E:\EduG\backend\scripts\save_staging_migration_handoff.ps1' -FromClipboard
```

Copy the command first if needed, then copy the URL immediately before running
it. Do not paste the URL into the command line or chat. The helper's validator
passed a synthetic URL check; the earlier rejection alone does not establish
whether the cause was the copied text or console paste handling.

It validates privately before overwriting the encrypted file and prints `SAVED`
only after the checks pass. The latest replacement decrypted but did not begin
with a PostgreSQL scheme and remained unparseable; no connection was attempted.
Do not interpret nonempty encrypted output as proof of valid URL contents.

Latest handoff check: the encrypted file exists and decrypts successfully, but
its nonempty content is not parseable as a SQLAlchemy connection URL. It has no
outer whitespace or line breaks and is not prefixed with a `psql` command.
No URL/password was printed and no network connection or migration was attempted.
Replace the content through the same masked prompt with the complete PostgreSQL
connection URL, not a dashboard link, password alone, or command. Do not reset
the database password. Validation will be repeated before any connection.

Browser access and the SSL/Data API checks are complete. The remaining manual
step is supplying the existing staging migration-owner URL privately to the
local runner. Do not reset a password or put this owner credential in Railway's
API runtime. Do not provide the runtime-role URL for schema creation.

Prepare the URL from Supabase Connect for staging `dviuaqtlbuefmfmswwqt`, using
the existing owner credentials, direct or session port 5432, and
`sslmode=verify-full`. For a session connection preserve the exact provider host
and project-qualified owner username. Percent-encode reserved password characters.
Use the downloaded public CA with
`sslrootcert=E:/EduG/backend/operator-evidence/supabase-ca.crt`.

In a local PowerShell window under the same Windows account, run:

```powershell
Read-Host 'Staging migration-owner PostgreSQL URL' -AsSecureString |
  Export-Clixml -LiteralPath 'E:\EduG\backend\operator-evidence\staging-migration-url.clixml'
```

Paste the complete URL only into that masked prompt. The file uses Windows
user-bound encryption and is inside a verified Git-ignored directory. Do not
paste the URL into chat, commands, screenshots or source. Confirm only that the
encrypted file is saved. This does not run a migration; the agent will validate
the target, role and TLS before using the already-authorized migration path.
If the owner password is unavailable, report that instead of resetting it.

## Sources

1. Railway, [Using Config as Code](https://docs.railway.com/config-as-code),
   accessed during this September 2026 review; deprecated, new-service restriction.
2. Railway, [Using Variables: sealed variables](https://docs.railway.com/variables#sealed-variables),
   accessed during this review; availability and CLI limitations.
3. Railway, [Pricing Plans](https://docs.railway.com/pricing/plans), accessed during
   this review; Free allowance and metered resource usage.
4. Vercel, [Hobby Plan](https://vercel.com/docs/plans/hobby), accessed during this
   review; personal non-commercial use.
5. Supabase, [Postgres SSL Enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement),
   accessed during this review; server enforcement and verify-full client TLS.
6. Supabase, [Securing your API](https://supabase.com/docs/guides/api/securing-your-api),
   accessed during this review; grants, default privileges and Data API isolation.
7. Supplied `C:\Users\SUN\Desktop\inter.md`, workbook dated 12 September 2026;
   local reference, not a source of additional authorization.
8. Local source, prior recorded test results, Git remote references, authenticated
   Railway usage output and Supabase dashboard observation. Secret values omitted.
