# Environment resource map

## Status and scope

**Staging and production references confirmed by the owner on 13 September
2026. Live configuration and isolation remain unverified.** This map separates the required design from resources observed on
12 September 2026. It does not authorize deployment, migrations, destructive
tests, credential replacement or changes to unrelated services.

The application remains React/Vite on Vercel, Flask/Gunicorn on Railway, and
Supabase PostgreSQL, with Redis for deployed rate limiting. Local SQLite tests need no hosted database. Hosted destructive PostgreSQL
testing is not assigned a project under the revised Free-tier plan.

## Required resource map

Only two hosted Supabase projects are approved. Their references below were
provided by the owner and are distinct; live status and credentials have not
been independently verified. Railway and Vercel assignments remain proposed.
All provider changes require explicit approval; this map authorizes no paid
plans, add-ons, credit purchases or billable overages.

| Environment | Supabase | Railway | Vercel |
| --- | --- | --- | --- |
| Staging | `dviuaqtlbuefmfmswwqt` (owner-confirmed staging) | Dedicated `staging` environment with its own API service, Redis and secrets; project/environment IDs pending | Separate project, proposed `edug-admin-staging`, with a stable HTTPS domain; project/domain pending |
| Production | `hszskxrgkptbytuquyfu` (owner-confirmed production) | Dedicated `production` environment with its own API service, Redis and secrets; project/environment IDs pending | Existing `edug-admin` is a candidate; observed domain `edug-admin.vercel.app`; assignment and backend target still require verification |

Use the same reviewed code revision for staging and promotion to production.
Do not treat `feature/frontend-production` as a permanent staging branch merely
because of its name. Record the intended deployment branches separately when
configuring automatic deployments; leave production auto-deployment disabled
until the deployment gates pass.

## Observed inventory

These are non-secret dashboard identifiers, not connection strings or tokens.

| Provider | Observed resource | What is established | What remains unknown |
| --- | --- | --- | --- |
| Supabase | `Sun808ey's Project`, dashboard project `hldwbhnaoschhelecksq`, region `eu-west-1` | One project visible in the selected Free organization | Existing data, clients, intended environment, runtime roles and credential scope; do not designate it disposable |
| Railway | `blissful-luck`, project `7d0c485e-3e9f-411c-9412-af8dd6f32481` | Dashboard lists no services; possible candidate for EduG | Intended ownership/purpose, environment inventory and token scopes |
| Railway | `serene-appreciation`, project `c6d8efd6-7ddb-4cf8-b6dc-767b3d244f09` | `production` environment contains online service `PLuwebz` | No evidence connects it to EduG; leave untouched |
| Vercel | `sun-g/edug-admin` | Linked to `Sun808ey/EduGD`; stable domain `edug-admin.vercel.app`; feature-branch previews exist | Environment-specific API URL, production branch/root settings and deployment readiness |
| Vercel | Other projects in `sun-g` | Other repositories are listed | Outside this map; do not repurpose them |

## Free-tier capacity and test policy

The older Supabase reference in the historical inventory is not assigned to this
plan. Do not delete, pause or repurpose it automatically. Verify the two assigned
projects' organization, regions and active status before configuration.

- Supabase Free permits two active projects, includes a 500 MB database per
  project, and pauses inactive projects after one week. Automatic backups and
  point-in-time recovery are not included. Arrange approved manual backup and
  restore checks; do not commit dumps or promise continuous availability.[3]
- Railway Free provides $1 of monthly credit. The observed account was on Trial;
  temporary credits do not establish ongoing Free capacity. Verify eligibility
  and combined API/Redis usage before deployment. Two always-running stacks have
  not been demonstrated to fit Free. Keep required Redis hardening; do not rely
  on paid environment RBAC or upgrade automatically.[6]
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

Create Railway staging as an **empty environment**. Railway's duplication flow
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

1. **Assignments received; live verification pending.** After explicit approval,
   verify staging `dviuaqtlbuefmfmswwqt` and production
   `hszskxrgkptbytuquyfu` in the dashboard, including regions and active Free
   status. Keep independent credentials in the secret manager. Do not create
   a third project. Review hosted destructive CI scope as described above.
2. Confirm the Railway project and ongoing Free API/Redis capacity. Obtain
   explicit approval before establishing separate `staging` and
   `production` environments, starting staging empty. Record each environment
   ID, API service ID and Redis service ID. Configure only the matching
   environment's credentials, private service references and deployment-token
   scope. Keep production deployment and pre-deploy migration inactive during
   setup.
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
