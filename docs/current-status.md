# EduGuard current project status

**Snapshot date:** 18 November 2026

**Status source:** read-only inspection of this workspace, GitHub, Vercel,
Railway and Supabase. Provider state is time-sensitive; consult the provider
dashboards again before any operational action.

This page is the current status reference for the repository. Dated audit and
execution reports elsewhere preserve historical evidence; their earlier
statements about current deployments, repository contents or readiness do not
override this snapshot.

## Product and repository

- The product name is **EduGuard**. The connected GitHub repository and remote
  URL still use the existing slug `Sun808ey/EduGD`; that provider identity has
  not been renamed.
- This workspace is on `main` at commit
  `00329891190fed463b5553b012944bdd46338799` (31 October 2026), matching the
  GitHub `main` commit observed on 18 November. The workspace contains
  uncommitted local changes, including the EduGuard rename and this
  documentation update. They have not been committed or pushed.
- Backend, administrator frontend and Android DPC source are present. Android
  code is under `android-dpc/` and `app/`. Physical-device certification,
  release signing and end-to-end offline enforcement are not verified by this
  status check. The bundled APK has not been rebuilt from the renamed source,
  so it is not evidence of a current release build.

## Hosted environment status

| Area | Latest observed state | Evidence boundary |
| --- | --- | --- |
| GitHub Actions | Checks attached to current `main` commit `0032989…` completed successfully on 31 October 2026. | No newer run appeared in the read-only query. This does not validate uncommitted workspace changes. |
| Railway staging API | Latest deployment attempt is **FAILED** (`744c3092-405e-4954-a55d-282b3fb26bda`, created 31 October 2026). The prior active deployment is **SLEEPING**, with 9 warnings and no critical alerts. There is no staged or applying work. | Read-only Railway project/environment status. Health and readiness were not re-probed. |
| Railway production API | Latest deployment attempt is **FAILED** (`fad5ccb8-05e6-4eab-a123-0aa5a53913d2`, created 31 October 2026). The service is **OFFLINE**, with 98 warnings and no critical alerts. There is no staged or applying work. | Read-only Railway project/environment status. Health and readiness were not re-probed. |
| Vercel staging frontend | Project `edug-admin-staging` exists, but `live` is false and its latest deployment is **CANCELED** (`dpl_98RCV9isgz16isn7tQihgGWaG1MD`). | Read-only project and deployment metadata. The frontend was not opened or smoke-tested. |
| Vercel production frontend | Project `edug-admin` exists, but `live` is false and its latest deployment is **CANCELED** (`dpl_2hi4tbnJPRLUrt6yMA5YunGzixEV`). | Read-only project and deployment metadata. The frontend was not opened or smoke-tested. |
| Supabase staging | Project `dviuaqtlbuefmfmswwqt` is **ACTIVE_HEALTHY**. | Project status only; schema revision, grants, TLS settings and application connectivity were not inspected. |
| Supabase production | Approved project `hszskxrgkptbytuquyfu` is **INACTIVE**. | Project status only; no database connection or schema inspection was performed. |
| Redis | Existing staging/production Redis assignments are described in the environment records. | No current Upstash or Aiven service status was checked in this snapshot. |

The most recently recorded hosted schema evidence in older reports is Alembic
revision `e4a1b7c9d2f6`. That historical evidence does not establish the current
hosted revision. The current repository migration history contains 40 revisions
with a single head, local rename migration `l7m8n9o0p1`. It was not applied
during this read-only status audit;
the revision currently applied to either hosted project was not inspected.

## Readiness

The codebase and its deployment records are not currently in a verified
staging- or production-ready state. The latest Railway deployments failed in
both environments, the production API is offline, neither Vercel project has a
live deployment, and the approved production Supabase project is inactive.
Current hosted schema, runtime connectivity, Redis health, browser-to-API
behavior and physical-device behavior remain unverified. Do not infer readiness
from older successful deployment records or from successful GitHub checks on
the committed revision.

## Operating boundaries

- Keep hosted changes, migrations, deployments and credential changes behind
  their explicit approval gates.
- Use Free-tier resources only and the two approved Supabase projects. Never
  run destructive integration tests against either hosted project.
- Keep secrets, signing material and private operator evidence out of Git.
- Do not commit or push without the owner's explicit instruction.
