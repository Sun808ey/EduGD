# Environment resource map

## Status and scope

**Workbook continuation:** the owner authorized completion against `inter.md`
for the academic proof of concept, subject to current Free-only instructions.
The [workbook reconciliation](setup-workbook-reconciliation.md) records current
evidence and supersedes stale pending-input statements below. Fresh installation,
saved/sealed variables and the selected enrollment settings are owner-confirmed.
Browser access is restored: both Supabase projects now have SSL enforcement on
and Data API disabled, dashboard-verified. Production SSL was enabled during
this continuation. The encrypted staging owner handoff passed validation and
TLS connection checks. Staging migrations reached `e4a1b7c9d2f6` with 18 public
tables; restricted runtime grants and 18 role-specific RLS policies committed
after 126 permission checks. The hosted diagnostic now passes after correcting
public CA inclusion in the runtime image. Staging API deployment
`7e5c7c43-2c34-4719-afc8-b132b6eb81f9` is healthy at
`https://edug-api-staging-staging.up.railway.app`; health/readiness return 200
and allowed/disallowed CORS checks pass. Administrator bootstrap is verified:
one administrator, five permissions and one bootstrap audit event. Frontend
deployment/authentication verification passed. Production owner preflight then
confirmed the assigned database, verified TLS, effective migration privileges
and an empty schema. Alembic reached `e4a1b7c9d2f6` with exactly 18 public
tables. The runtime security transaction passed 126 permission checks, enabled
RLS on all 18 tables, installed 18 `edug_backend_runtime` policies and denied
the Data API roles. Production runtime connectivity, Railway deployment,
public readiness, Vercel deployment and CORS verification now pass. The
production API is `https://edug-api-production-production.up.railway.app` and
the production frontend is `https://edug-admin.vercel.app`.

**Latest progress, 17 September 2026:** the owner authorized steps 3–7 in
sequence using zero-cost plans and confirmed EduG is strictly personal and
non-commercial. Supabase schema/security checks, Redis TLS checks, Railway API
deployments and Vercel frontend deployments now pass for staging and
production. Android offline-device acceptance remains outstanding because this
checkout has no Android implementation. Earlier pause and approval statements
below are historical where superseded here.

### Verified frontend assignments (step 3)

| Setting | Staging | Production |
| --- | --- | --- |
| Vercel scope/plan | `sun-g`, Hobby | `sun-g`, Hobby |
| Project | `edug-admin-staging` | `edug-admin` |
| Project ID | `prj_8FoiuHbud8Q0nKCPxxNWfPUKT3Tu` | `prj_mOFsRmVw7Ij17if6ETWx1SebWhji` |
| Assigned HTTPS domain | `https://edug-admin-staging.vercel.app` | `https://edug-admin.vercel.app` |
| Git repository | `Sun808ey/EduGD` | `Sun808ey/EduGD` |
| Project's Production branch | `feature/backend-api` | `main` |
| Root | `frontend/school-policy-admin` | `frontend/school-policy-admin` |
| Framework/runtime | Vite, Node 24.x | Vite, Node 24.x |
| Install | `npm ci` | `npm ci` |
| Build/output | Repository config: `npm run build`, `dist` | Dashboard aligned to `npm run build`, `dist` |
| Automatic build hold | `exit 0` (Don't build anything) | `exit 0` (Don't build anything) |

Created the staging project empty, renamed it, connected the existing GitHub
repository and assigned its provider domain. Its initial generated domain
`project-irlim.vercel.app` remains an additional alias. Domain assignment is
verified; the staging domain has no deployed application yet. Vercel's label
"Production" inside this separate staging project means its stable deployment
slot, not EduG production. No paid custom environment or paid build resource
was enabled. Staging project model-training sharing and PR comments were disabled.
The existing production deployment was not replaced. Build holds must be lifted
only for the reviewed staging/release deployments at their respective gates.

The existing production project has `VITE_API_URL` scoped to Production and
Preview; the prepared code reads `VITE_API_BASE_URL`. Correct this mismatch at
step 5 with verified environment-specific endpoints. No secret values were
read into this record. Assignment checks do not establish frontend/API routing.

### Step 4 verified implementation

Local edits replace the hosted-secret PostgreSQL workflow with a manual,
isolated Docker stack and add unconditional test rejection of both approved
Supabase references. See [disposable PostgreSQL checks](disposable-postgres-tests.md).
44 focused safety/identity tests, Ruff, type checking and Compose parsing passed.
Docker recovered after startup delays; all 38 migration/PostgreSQL/concurrency
tests passed against the isolated container. Its containers, network and
temporary certificate volume were removed afterward. Deployment identity guards bind the entry point to the
assigned resources, and [supported Railway settings](railway-deployment-settings.md)
are prepared. The legacy JSON no longer runs migrations automatically. GitHub
workflow 340582975 was disabled and verified `disabled_manually`; its five most
recent runs are completed failures, not active runs. The new manual isolated
workflow remains local until the owner commits and pushes. No commit/push was made.

### Step 5 partial configuration and manual gate

Both Railway APIs contained only generated platform variables before this step.
Applied and read back seven non-secret settings using `--skip-deploys`:
`APP_ENV=production`, the respective `EDUG_ENVIRONMENT`, `FLASK_APP=run.py`,
`FLASK_DEBUG=false`, each exact frontend origin, pool size 1 and overflow 0.
The platform environment IDs matched the resource map. Both services remain
offline. Database/Redis URLs, signing/audit keys, enrollment settings, TLS trust,
runtime/migration roles and public API endpoints are not yet configured or verified.
Follow [the private configuration handoff](private-environment-configuration.md).
Source attachment, deployment settings and frontend API-variable correction
remain pending; no hosted migration or API deployment was performed.

The CLI volume inventory includes deleted records that the dashboard omitted.
Staging volume `1ba54880-ce0f-4abb-bd94-fa89d9bdf68b` and production volume
`80a9aba1-2879-47c0-a2ef-14ec2d5f3790` both have non-null `deletedAt`,
`isPendingDeletion=true` and no attached service. Their displayed sizes are
approximately 32 MB and 49 MB. This confirms deletion requests, not final provider
purging or zero storage billing; reconcile usage before the deployment gate.
No additional volume deletion was attempted.

**Latest instruction: steps 1 and 2 must use zero-cost Redis alternatives.**
The [zero-cost Redis implementation plan](zero-cost-redis-plan.md) supersedes
proposals below to add Railway production Redis. Upstash Free staging and Aiven
Free Valkey production were proposed. Upstash staging, its TLS endpoint and
synthetic probe writes are now explicitly approved, as is retirement of the
existing Railway staging Redis after replacement verification. Upstash Free staging database `5c8b39a5-c1f5-4a0d-923b-a9bebb84374e`
has been created; the owner reports the staging live probe PASS. The approved
Railway staging Redis service and volume have been deleted and their absence
verified in the dashboard. One Aiven Free Valkey production service with external
TLS and temporary verification writes is now explicitly approved; account
production service is Running on Free-1 as of 14 September 2026;
TLS certificate/hostname verification passed and the owner reports the
production authenticated probe PASS. Historical
resource IDs below are retained as history, not as active inventory.
Step 3 is paused until steps 1 and 2 are verified.

**The owner confirmed both Supabase projects are active (healthy), on Free,
and in `eu-west-1` on 13 September 2026.** The Supabase assignment checkpoint
is satisfied by owner confirmation. The owner also confirmed `blissful-luck`
as the EduG Railway host and reported that the Free-capacity check passed.
The owner supplied distinct Railway staging/production environment IDs and
confirmed staging was created empty, production remained unchanged, and no
deployments or migrations were started. The owner also confirmed production has no EduG API or Redis service.
The empty staging API has since been created and verified as recorded below.
The empty production API has also been created with separate explicit approval.
Redis provisioning and owner-reported local probes are complete; credential
isolation and Vercel assignments remain pending. Historical dashboard observations date from
12 September 2026. It does not authorize deployment, migrations, destructive
tests, credential replacement or changes to unrelated services.

The application remains React/Vite on Vercel, Flask/Gunicorn on Railway, and
Supabase PostgreSQL, with Redis for deployed rate limiting. Local SQLite tests need no hosted database. Hosted destructive PostgreSQL
testing is not assigned a project under the revised Free-tier plan.

## Required resource map

Only two hosted Supabase projects are approved. Their references below were
provided by the owner and are distinct. Status, plan, region and organization
are owner-confirmed; no independent dashboard or credential verification is claimed.
The Railway project and environment assignments are owner-confirmed. The staging
and production API IDs are dashboard-verified; Redis and Vercel assignments
remain pending.
All provider changes require explicit approval; this map authorizes no paid
plans, add-ons, credit purchases or billable overages.

| Environment | Supabase | Railway | Vercel |
| --- | --- | --- | --- |
| Staging | `dviuaqtlbuefmfmswwqt`; active/healthy, Free, `eu-west-1` (owner-confirmed) | `blissful-luck` (`7d0c485e-3e9f-411c-9412-af8dd6f32481`); `staging` environment `a8928189-e7bb-46be-8788-856816caecd0`; empty API `edug-api-staging`, service `5ac7afd9-8d99-4ab6-92b8-3e4adab1f058` (offline); Railway Redis and volume retired. Replacement: Upstash Free `5c8b39a5-c1f5-4a0d-923b-a9bebb84374e`, external TLS, owner-reported probe PASS; API connection pending | Separate project, proposed `edug-admin-staging`, with a stable HTTPS domain; project/domain pending |
| Production | `hszskxrgkptbytuquyfu`; active/healthy, Free, `eu-west-1` (owner-confirmed) | `blissful-luck` (`7d0c485e-3e9f-411c-9412-af8dd6f32481`); `production` environment `48e80896-15ef-4616-837e-d59240fc503a`; empty API `edug-api-production`, service `8e9b3d47-6efe-4e32-aef3-74fa69b99ef5` (dashboard-verified, offline); external Aiven Free-1 `edug-production/edug-redis-production`, owner-reported probe PASS; API connection pending | Existing `edug-admin` is a candidate; observed domain `edug-admin.vercel.app`; assignment and backend target still require verification |

Use the same reviewed code revision for staging and promotion to production.
Do not treat `feature/frontend-production` as a permanent staging branch merely
because of its name. Record the intended deployment branches separately when
configuring automatic deployments; leave production auto-deployment disabled
until the deployment gates pass.

Both projects belong to organization
[`ogicyjubywkbhvkcgraf`](https://supabase.com/dashboard/org/ogicyjubywkbhvkcgraf),
as confirmed by the owner. This confirmation does not authorize migrations,
deployments or credential changes.

## Observed inventory

These are non-secret dashboard identifiers, not connection strings or tokens.

| Provider | Observed resource | What is established | What remains unknown |
| --- | --- | --- | --- |
| Supabase | `Sun808ey's Project`, dashboard project `hldwbhnaoschhelecksq`, region `eu-west-1` | One project visible in the selected Free organization | Existing data, clients, intended environment, runtime roles and credential scope; do not designate it disposable |
| Railway | `blissful-luck`, project `7d0c485e-3e9f-411c-9412-af8dd6f32481` | Owner-confirmed EduG host; owner reports Free-capacity check passed. Earlier dashboard observation listed no services | Environment IDs and absent production API/Redis confirmed by owner; service creation, configuration and token scopes pending |
| Railway | `serene-appreciation`, project `c6d8efd6-7ddb-4cf8-b6dc-767b3d244f09` | `production` environment contains online service `PLuwebz` | No evidence connects it to EduG; leave untouched |
| Vercel | `sun-g/edug-admin` | Linked to `Sun808ey/EduGD`; stable domain `edug-admin.vercel.app`; feature-branch previews exist | Environment-specific API URL, production branch/root settings and deployment readiness |
| Vercel | Other projects in `sun-g` | Other repositories are listed | Outside this map; do not repurpose them |

## Free-tier capacity and test policy

The older Supabase reference in the historical inventory is not assigned to this
plan. Do not delete, pause or repurpose it automatically. The owner has now
confirmed the two assigned projects' organization, region, Free plan and healthy
status. No third active project is part of this plan.

- Supabase Free permits two active projects, includes a 500 MB database per
  project, and pauses inactive projects after one week. Automatic backups and
  point-in-time recovery are not included. Arrange approved manual backup and
  restore checks; do not commit dumps or promise continuous availability.[3]
- Railway Free provides $1 of monthly credit.[6] The owner confirmed that the
  Free-capacity check passed for EduG on `blissful-luck`; this checkpoint is
  satisfied by owner confirmation. The earlier Trial observation is historical.
  No independent usage measurements or continuous-uptime guarantee are claimed.
  Keep deployed usage within Free allowances and retain required Redis hardening;
  do not rely on paid environment RBAC or upgrade automatically.
- Use separate Vercel Hobby projects and provider domains without paid custom
  environments. Hobby is limited to personal, non-commercial use; confirm the
  application's eligibility before deployment. Confirm actual domain names and
  quotas. If the plan is unsuitable, propose a no-cost alternative for approval.[4][7]
- Check GitHub Actions availability and included quota before scheduling tests.
  The previously observed billing block is unresolved; do not purchase capacity
  or claim hosted checks passed without execution evidence.

No third hosted project is required for development or integration testing.
Local `APP_ENV=testing` uses SQLite, which does not establish PostgreSQL coverage.
Neither staging nor production is disposable: never supply either reference or
its credentials to the destructive PostgreSQL integration suite.

The existing `backend-postgres.yml` workflow still triggers automatically on
matching pushes/PRs and enables destructive tests. This documentation does not
disable it. Before hosted test execution, privately review its environment and,
with explicit approval, disable hosted destructive execution and remove any live
project credentials from its test scope. Leave hosted test URLs/reference unset.
A compatible local/ephemeral PostgreSQL test path needs implementation because
the current tests enforce Supabase identity and TLS. Until it exists and passes,
record PostgreSQL migration/concurrency coverage as pending, not passed or waived.
Approved staging smoke checks and migration rehearsals are separate activities.

If any requirement cannot fit Free allowances, pause and present a no-cost
alternative for explicit approval. Do not weaken security controls to fit quotas.

## Credential and routing boundaries

| Scope | Allowed configuration | Must remain excluded |
| --- | --- | --- |
| GitHub `backend-integration-test` | No hosted database assignment; test URLs/reference remain unset | Staging/production database credentials, Railway tokens, production data copies |
| Railway staging | Only staging Supabase runtime/migration credentials, staging Redis, independent application signing/audit/pairing secrets, exact staging frontend origin | Production credentials, references to production services or copied production secret values |
| Railway production | Only production Supabase runtime/migration credentials, production Redis, existing valid production signing/audit/pairing secrets, exact production frontend origin | Test/staging database credentials or staging deployment tokens |
| Vercel staging | Public `VITE_API_BASE_URL` pointing to staging Railway `/api/v1`, optional public telemetry configuration | Production API target, all database URLs, Railway tokens and server secrets |
| Vercel production | Public `VITE_API_BASE_URL` pointing to production Railway `/api/v1`, optional public telemetry configuration | Staging API target, all database URLs, Railway tokens and server secrets |

Application runtime and migration roles differ within each Supabase project.
The two URLs for one environment must resolve to that same project/database,
using direct or session connections with certificate-verifying TLS. Reusing a
Supabase project with another schema, role or pooler hostname is not isolation.

Railway staging was created as an **empty environment**, as confirmed by the
owner. Preserve that separation during subsequent service configuration. Railway's duplication flow
copies unsealed variables as well as services; deployment before reviewing copied values
could connect staging to production. Railway isolates private networking by
environment, but external Supabase credentials still require explicit separation.
Review every service/shared variable reference within its selected environment.
Sealed variables are excluded from duplication and must be set independently.[1]

If deployment automation requires Railway tokens, use separately issued project
tokens scoped to the corresponding environment. Do not reuse an account/workspace
token in both deployment jobs. If GitHub-native deployment needs no token, do not
create one solely for this map. Record token scope privately, never token values.[2]

Generate independent staging secrets. Preserve valid production keys and pepper
versions; a map does not authorize rotating deployed keys or invalidating device
credentials. Compare values privately when verifying independence. Do not publish
secrets, their hashes, URL credentials, or environment exports in this document.

## Existing code controls and limits

`backend/app/config.py` derives Supabase project identity from direct hosts or
session-pooler usernames. It rejects project reuse among the configured
development, integration-test and production URLs, rejects authority-overriding
URL parameters, and validates the migration URL against the active database.

`backend/test_support/postgres_safety.py` additionally binds tests to an explicit
project reference, purpose marker and destructive opt-in, then checks the actual
connected database identity and TLS. The PostgreSQL workflow uses the GitHub
environment `backend-integration-test`.

These controls do **not** establish the complete Phase 2 outcome: there is no
`APP_ENV=staging` or `STAGING_DATABASE_URL` configuration, no independently pinned
staging/production project registry, and no cross-provider credential comparison.
The guards cannot compare URLs that are absent from their process. Do not put
production credentials into test jobs merely to make comparison possible.

For a staging deployment of the current code, `APP_ENV=production` is required
to exercise production hardening; its environment-local `PRODUCTION_DATABASE_URL`
must contain the staging project's URL. `APP_ENV=staging` currently fails startup.
This variable naming is easy to misconfigure: a subsequent enforcement step must
bind each deployment to its approved non-secret resource identity before calling
the overall isolation outcome complete. This map adds no runtime behavior.

## Manual configuration sequence

1. **Supabase assignment checkpoint complete by owner confirmation.** Staging
   `dviuaqtlbuefmfmswwqt` and production `hszskxrgkptbytuquyfu` are distinct,
   active/healthy, Free and in `eu-west-1`, organization `ogicyjubywkbhvkcgraf`.
   Keep independent credentials in the secret manager. No third project is
   authorized. Hosted destructive CI scope review remains pending as described
   above; project health does not establish credential isolation or test safety.
2. **Railway environment assignment checkpoint complete by owner confirmation.**
   Use `blissful-luck`, project `7d0c485e-3e9f-411c-9412-af8dd6f32481`:
   staging `a8928189-e7bb-46be-8788-856816caecd0` and production
   `48e80896-15ef-4616-837e-d59240fc503a`. Both IDs have valid UUID syntax and
   differ; syntax checks do not independently verify provider ownership.
   Staging was created empty, production remained unchanged, and no deployments
   or migrations were started. The supplied confirmation contains only non-secret
   identifiers and setup status.

   **Production service inventory complete by owner confirmation.** EduG API:
   absent, name/ID N/A. Redis: absent, name/ID N/A. Staging was created empty.
   The owner confirmed no configuration, deployment, migration, commit or push
   was performed during this inventory check. N/A denotes absence, not an ID.

   **Approved empty staging API creation completed.** Service
   `edug-api-staging` has ID `5ac7afd9-8d99-4ab6-92b8-3e4adab1f058`.
   The dashboard shows it offline, unexposed and with no active deployment.
   The separately approved empty production API was also created; see its
   verification below. Redis and subsequent configuration/deployments remain
   unapproved.
3. Confirm `edug-admin` as the production Vercel project and establish a separate
   stable staging project/domain. Record both project IDs, roots, deployment
   branches and domains. Assign public API URLs to matching environments only;
   previews must not inherit the production API by default.
4. Update this map with verified identities, then validate that the two approved
   Supabase references differ, Railway environments and credentials are
   isolated, frontend/API routing matches, and no unresolved placeholders remain.
   Complete the required code/deployment guard work described above before
   approving the overall isolation outcome.

The owner performs required manual configuration and confirms completion before
the next dependent step. No secrets are needed in chat. Until then this document
is a proposed resource map with an observed inventory, not a completed isolation
certificate.

## Approved empty staging API creation

Following explicit owner approval, created `edug-api-staging` in staging
`a8928189-e7bb-46be-8788-856816caecd0`, service ID
`5ac7afd9-8d99-4ab6-92b8-3e4adab1f058`. The dashboard was checked on
13 September 2026: source is unconnected, the service is offline and unexposed,
and the Deployments tab states there is no active deployment. No repository,
image, variables, credentials or volume was attached; no workload or migration
was started. Production was not modified.

Railway first staged one empty-service addition. Its review dialog showed only
`edug-api-staging will be added`. Applying that change using the dashboard's
**Deploy Changes** button persisted the empty service without a workload
deployment; the pending-change banner disappeared. No Git commit or push was
performed. This completes empty-service creation only.[8][9]

The dashboard still displays a Trial countdown. The owner's Free-capacity
confirmation remains recorded, but ongoing Free eligibility must not be inferred
from the Trial balance before running services.

The service settings also display a notice that new services cannot opt into
legacy Config as Code after 28 August 2026. Before any API deployment, review the
supported configuration path instead of assuming `backend/railway.json` will be
applied. Official documentation confirms that new services cannot opt in and
identifies Infrastructure as Code as the replacement.[11] The migration runbook
now requires supported dashboard settings or reviewed IaC before deployment.
No provider configuration migration was performed in this step.

Redis is a separate approval step because provisioning the database starts a
running service and consumes resources. After approval, the intended design is
one private Redis service per environment, each referenced only by its matching
API. Do not create Redis merely to obtain a service ID while deployments are
still prohibited.[9][10]

Before attaching the API repository or deploying, review environment credentials,
Free resource limits and migration authorization. `backend/railway.json` currently
sets `preDeployCommand` to `flask --app run.py db upgrade`; an API deployment can
therefore run migrations. Empty-service creation does not approve that command.
Production service creation and all deployment/migration actions require their
own explicit approval. Vercel assignments and the hosted destructive-test scope
review remain outstanding; this inventory is not proof of complete isolation.

## Remaining Phase 2.1 checkpoints

| Item | Current evidence | Remaining action |
| --- | --- | --- |
| Supabase assignments | Two distinct owner-confirmed healthy Free projects in `eu-west-1` | Preserve their separate credential scopes |
| Railway environments | Two owner-confirmed distinct IDs in `blissful-luck` | Preserve environment separation |
| Staging API | Empty service created and dashboard-verified offline | Configure only after approval |
| Production API | Empty service `8e9b3d47-6efe-4e32-aef3-74fa69b99ef5` created and dashboard-verified offline | Configure only after approval |
| Redis | Upstash Free staging created; owner-reported live probe PASS; legacy Railway staging Redis and volume retired; Aiven production Running on Free-1, TLS handshake passed | Both local probes owner-reported PASS; API references, Railway connectivity and usage validation remain pending |
| Vercel | Production candidate `edug-admin`; staging unassigned | Confirm production assignment and Hobby eligibility; approve staging project setup and record IDs/domains |
| Credential/routing isolation | Requirements documented; no deployed validation evidence | Configure and verify matching databases, Redis, secrets and frontend/API targets |
| PostgreSQL test safety | Existing workflow still enables destructive hosted tests | Review hosted secret scope; neither approved project may be used; compatible disposable test path remains pending |
| Deployment configuration | Legacy JSON cannot configure new Railway services | Review dashboard settings or IaC before connecting sources; migrations require approval |

## Approved empty production API creation

Following explicit owner approval, created `edug-api-production` in `blissful-luck`
production environment `48e80896-15ef-4616-837e-d59240fc503a`. Service ID:
`8e9b3d47-6efe-4e32-aef3-74fa69b99ef5`, distinct from the staging API ID.

Dashboard verification on 13 September 2026 showed an unconnected source,
an offline and unexposed service, and no active deployment. No repository,
image, variables, secrets, volume or public domain was attached. The change
review contained only the empty production service addition; applying it cleared
the pending-change banner without starting a workload or migration. Staging was
not modified. No Git commit or push was performed.

Both empty API service creation checkpoints are now complete. Redis provisioning,
service configuration, Vercel assignments and isolation verification remain
pending. This approval does not extend to those changes or to a paid plan.

## Completion audit and next approval

Phase 2.1 is **incomplete**. The two Supabase assignments, Railway environment
assignments and empty API service creation are recorded. Empty services do not
prove database connectivity, Redis availability, credential isolation or frontend
routing. Redis and Vercel assignments, supported deployment configuration and
hosted-test safety remain open in the checklist above.

The following **staging Redis provisioning** plan was explicitly approved and
executed; verified results are recorded below:

1. In `blissful-luck`, select staging environment
   `a8928189-e7bb-46be-8788-856816caecd0` and review its current included-credit
   balance and Redis template resource/volume settings before applying changes.
2. Provision one standard Redis service named `edug-redis-staging`, using the
   provider template's generated credentials kept inside Railway. This starts
   a Redis workload and consumes included credits; it is not an empty service.
   Keep the template's private networking; do not add Public Access or a TCP
   proxy. Review any template volume as part of the approval, rather than adding
   unreviewed storage. No paid upgrade, credit purchase or overage is authorized.
3. Verify the service belongs to staging, record its non-secret ID and check
   its running status and private-only networking without exposing credentials.
   Leave both API services unconnected/offline. Do not modify production,
   connect Supabase, run migrations or populate API credentials in this step.
4. If the template cannot be provisioned within the zero-payment constraint,
   stop before applying it. Production Redis needs separate approval after the
   staging result and resource usage have been reviewed.

Railway's documentation says Trial transitions to Free with $1 monthly credit;
that does not establish that two complete always-running stacks fit the budget.
It also warns that Trial-created stateful volumes are deleted 30 days after
credit expiry. The Free-only operating plan therefore needs a reviewed retention
and recovery decision before treating Redis storage as durable.[12] No paid
retention feature is approved. Redis is private by default, while public access
requires a TCP proxy; leave that public access disabled.[10]

## Approved staging Redis provisioning result

Historical result: this Railway service and its volume were subsequently retired
after the Upstash staging probe passed, as recorded below.

On 13 September 2026, provisioned the approved Railway Redis template in
`blissful-luck` staging `a8928189-e7bb-46be-8788-856816caecd0` and renamed it
`edug-redis-staging`.

| Property | Dashboard-verified result |
| --- | --- |
| Service ID | `f189c590-df15-4297-9286-1afa643a171f` |
| Deployment ID | `1a7b9f92-4e09-4ee8-9983-cfa70700b681` |
| Image/status | `redis:8.2`; ACTIVE, deployment successful, service online |
| Networking | Unexposed; Add Public Access remains available, no TCP proxy added; private hostname `redis.railway.internal` |
| Volume | `redis-volume-Zt_B`, ID `1ba54880-ce0f-4abb-bd94-fa89d9bdf68b` |
| Storage | 500 MB maximum, mounted at `/data` |
| Available allowance at creation | Trial dashboard showed 18 days or $4.56 remaining |
| API state | Staging and production API services both remained offline; production has no active deployment |

The database menu provisioned and deployed the template immediately. Its attached
volume was inspected after provisioning and matched the 500 MB allowance; no
additional volume or storage increase was requested. Generated credentials stayed
inside Railway and were not displayed, copied to the APIs or written to Git.
No public endpoint, paid plan, paid add-on or credit purchase was enabled. The
Redis workload and stored data consume the available included allowance; future
usage has not been measured or guaranteed to fit the recurring Free allowance.
Trial volume retention limitations described above still apply.

No API deployment, Supabase connection or migration was performed. Production
Redis is still absent. Production Redis provisioning, API configuration and
Vercel assignment remain separate pending steps requiring approval as applicable.
No Git commit or push was performed. Dashboard health is not an authenticated
application-to-Redis connectivity test; that verification remains pending API
configuration.

## Sequential completion gates

Proceed in this order, recording evidence for each gate before advancing. A
successful provisioning step is not proof of flawless end-to-end operation.

1. **Staging Redis operational and Free-budget review.** The following Railway
   measurements are historical; the resource has since been retired and replaced
   by Upstash Free, with an owner-reported local probe PASS. Application usage
   and Railway-to-Upstash connectivity remain unverified. Earlier creation,
   private networking and the attached 500 MB volume were verified. On the
   subsequent 13 September dashboard review, Cost by Service displayed 0.09 GB
   RAM, 0.02 vCPU and 0.29 GB volume for staging Redis. Current costs rounded to
   zero and the Trial balance still displayed $4.56; neither proves zero ongoing
   consumption. If those resource levels were sustained, the illustrative cost
   is `(0.09 * 10) + (0.02 * 20) + (0.29 * 0.15) = $1.3435/month`, before APIs,
   production Redis or egress.[6] This short observation is not a representative
   monthly forecast. Gather representative average usage and settle a Free-only
   operating/retention plan before expanding. Do not treat the previous owner
   capacity confirmation as proof against newer measured evidence.
2. **Production Redis-compatible store.** Only after gate 1 passes and explicit
   approval is given, follow the zero-cost implementation plan (not a new
   Railway Redis deployment) with independent generated credentials;
   verify its environment, ID, volume, running status and total Free budget.
3. **Frontend assignments.** Confirm the production Vercel project and Hobby
   eligibility, then obtain approval for the separate staging project. Record
   both IDs, deployment branches, roots and exact HTTPS domains. Verify them
   before assigning API targets.
4. **Deployment configuration and test safety.** Prepare supported Railway
   dashboard settings or reviewed IaC for the new services. Ensure destructive
   PostgreSQL CI cannot target either assigned project. Complete the compatible
   disposable test path and required configuration guards before rollout;
   SQLite-only coverage is insufficient. Do not run migrations at this gate.
5. **Environment-specific configuration.** With explicit approval, configure
   runtime/migration roles, TLS trust, separate secrets, private Redis references,
   API URLs and exact CORS origins. Verify each environment's identities and
   absence of cross-environment credentials without exposing secret values.
6. **Staging integration verification.** After migration/deployment approval,
   verify staging readiness, PostgreSQL/TLS and authenticated Redis connectivity,
   frontend routing, rate limiting and isolation. Record actual results and
   resource usage. Resolve every failure before promotion.
7. **Production verification and final audit.** Obtain the separate production
   release/migration approval, perform approved smoke and isolation checks, and
   reconcile the resource map with live settings. Mark the complete outcome only
   when all gates have evidence; a resource map or healthy container alone is
   insufficient. Committing and pushing remain the owner's task.

The earlier sequential review made no provider changes. Subsequently, the owner
approved Upstash Free staging and retirement of the identified Railway Redis
service and volume; both actions are now complete as recorded below. Production
Redis must not be provisioned before its separate provider approval. No paid
upgrade is authorized or applied.

## Upstash staging replacement created

Created the approved `edug-redis-staging` database on Upstash Free in Ireland
(`eu-west-1`), ID `5c8b39a5-c1f5-4a0d-923b-a9bebb84374e`. Dashboard verified
Free Tier and TLS enabled; TCP endpoint `set-mayfly-105830.upstash.io:6379`.
No payment method was added. The owner reported
`PASS: staging TLS/auth, expiry and fixed-window checks.` after running the
command in [the zero-cost plan](zero-cost-redis-plan.md). This is an owner-reported
local test, not an agent-observed probe or verification from Railway.
No production setup, API deployment, Supabase migration, commit or push occurred.

## Approved Railway staging Redis retirement

On 13 September 2026, after the owner-reported Upstash PASS, applied the already
approved deletion of exactly these staging resources:

- Service `edug-redis-staging`, ID `f189c590-df15-4297-9286-1afa643a171f`.
- Volume `redis-volume-Zt_B`, ID `1ba54880-ce0f-4abb-bd94-fa89d9bdf68b`.

Railway's final destructive-change review listed only these two resources in
`blissful-luck/staging`. After applying and reloading, the staging architecture
showed only `edug-api-staging` offline; neither Redis resource nor a pending
change banner remained. A separate production dashboard check showed only
`edug-api-production` offline. No API configuration, deployment, Supabase change,
Git commit or push was performed. Retirement removes these metered resources;
it does not reverse prior credit consumption or establish the whole app's cost.

Staging provider creation, owner-reported compatibility probe and legacy resource
retirement are complete. Production provider creation and owner-reported local
probe are also complete. Railway-to-provider connectivity, representative usage
and environment isolation remain pending. Step 3 remains paused; Phase 2.1 is not fully complete.

## Approved Aiven production setup: onboarding checkpoint

On 13 September 2026, the owner approved one Aiven Free Valkey production service
named `edug-redis-production`, external TLS and temporary synthetic verification
writes, without paid upgrades or API deployment. On 14 September, authenticated
access to `/welcome` was verified in Chrome Sun. The selected Valkey plan displays
Free forever, 1 CPU, 1 GB RAM and auto-assigned Europe. Prepared project name
`edug-production` and service name `edug-redis-production`; creation has not been
submitted because required name and country details await the owner's reply.
No Aiven resource has been created; service identity, host, exact region and
live compatibility remain unknown. Continue the approved scope after those
details arrive without asking for the same approval again. Both APIs remain
offline; step 3 remains paused.

### Aiven production created, 14 September 2026

The owner supplied the required onboarding details, which were entered before
creation. Created one service `edug-redis-production` in project `edug-production`,
organization/account `a5dea12e0be4`. Persisted settings confirm Free-1, 1 CPU,
1 GB RAM, one Valkey 9.1.1 node and `valkey_ssl` enabled. Creation time is
03:35 UTC; provider DigitalOcean, region `ams` (Amsterdam, Netherlands).
Endpoint: `edug-redis-production-edug-production.a.aivencloud.com:22050`.
Public internet with the default IP allowlist; no paid upgrade, API configuration
or deployment, migration, Git commit or push was performed.

After provisioning, refreshed settings show Running and Free-1. An initial DNS
lookup during the build failed; the subsequent direct TLS 1.3 handshake passed
certificate-chain and hostname verification with system trust. Authentication
and synthetic-write compatibility checks subsequently passed by owner report
on 14 September 2026: `PASS: production TLS/auth, expiry and fixed-window checks.`
The authenticated probe was run locally by the owner, not from Railway. No
repeat probe is currently required. This
endpoint differs from staging, but full integration and isolation are unverified.

## Sources

Pricing and Hobby guidance checked 13 September 2026; other guidance accessed
12 September 2026; plan availability and account
configuration must be checked again when provisioning.

1. Railway, [Isolate Staging from Production for Compliance](https://docs.railway.com/guides/isolate-staging-production): environment creation, duplication, network and variable isolation.
2. Railway, [Public API](https://docs.railway.com/integrations/api): project tokens are scoped to one environment.
3. Supabase, [Pricing](https://supabase.com/pricing): Free plan active-project limit.
4. Vercel, [Environments](https://vercel.com/docs/deployments/environments) and [Environment variables](https://vercel.com/docs/environment-variables): environment targets, plan-dependent custom environments and variable scope.
5. Read-only account inventory: [Supabase dashboard](https://supabase.com/dashboard), [Railway dashboard](https://railway.app/dashboard), [Vercel dashboard](https://vercel.com/dashboard). Observations are limited to the selected organization/workspace and visible projects.

6. Railway, [Pricing plans](https://docs.railway.com/pricing/plans): Free allowance and temporary Trial credits.
7. Vercel, [Hobby plan](https://vercel.com/docs/plans/hobby): eligibility and usage limits.

8. Railway, [Services](https://docs.railway.com/services): empty service creation and separate deployment step; checked 13 September 2026.
9. Railway, [railway add](https://docs.railway.com/cli/add): empty services and automatic database deployment; checked 13 September 2026.
10. Railway, [Redis](https://docs.railway.com/databases/redis): provisioning and service connection variables; checked 13 September 2026.

11. Railway, [Config as Code](https://docs.railway.com/config-as-code) and [Infrastructure as Code](https://docs.railway.com/infrastructure-as-code): new-service restrictions and replacement configuration workflow; checked 13 September 2026.

12. Railway, [Free Trial](https://docs.railway.com/pricing/free-trial): transition to Free and Trial volume retention; checked 13 September 2026.
