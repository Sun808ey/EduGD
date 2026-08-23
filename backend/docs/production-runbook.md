# Production deployment and recovery runbook

## Non-negotiable pre-deployment gates

1. Rotate every Neon password and application secret that ever appeared in
   `.history` or `.github/env.txt`. Historical values are compromised even
   after file deletion.
2. Scan the current tree and all Git revisions with an approved secret scanner.
   Do not deploy until it reports no live credentials.
3. After taking a separate recoverable mirror, purge `.history` and
   `.github/env.txt` from Git history with `git filter-repo`. The repository
   owner performs the force-push; every collaborator must re-clone afterward.
4. Confirm separate Neon development, integration-test, staging, and
   production branches. Runtime URLs are pooled; migration URLs are direct;
   every URL requires TLS.
5. Run the complete quality workflow and the explicitly safety-gated PostgreSQL
   migration/concurrency suite on `backend-integration-test`.

## Secret hygiene and history recovery

Do not paste credentials into source files, shell transcripts, issue comments,
or documentation. Use Render secret variables, Neon credentials, Redis
connection settings, and local `.env` files that are ignored by Git. Keep
`.env.example` placeholder-only.

Before declaring repository readiness, install approved secret-scanning and
history-rewrite tooling on a clean clone. Run the scanner against the current
tree and all revisions without printing matched secret values. After all
affected credentials are rotated or revoked, remove historical secret blobs with
`git filter-repo`, verify the cleaned history with the scanner, force-push only
under repository-owner approval, and require every collaborator to re-clone.

Enable provider-side secret scanning and push protection where available. A
push that introduces a real credential is a release blocker, even when the
credential is quickly deleted in a later commit.

## Render deployment

`render.yaml` defines the Python 3.12 web service, Render Key Value service,
one pre-deploy migration command, Gunicorn, and the dependency-aware readiness
health check. `/api/v1/health` remains a dependency-free liveness endpoint.
Populate every `sync: false` variable in the Render dashboard. Use two workers
and four threads initially. The declared defaults cap the application at
`2 × (3 persistent + 2 overflow) = 10` connections. This deterministic
application budget must be checked against the actual Neon plan limit before
changing workers, instances, or pool settings.

Before the first production migration, create and verify a Neon restore point.
Render must run `flask --app run.py db upgrade` once in the pre-deploy phase.
Gunicorn workers must never run migrations. A deployment is acceptable only
when `/api/v1/health` returns 200, `/api/v1/ready` returns 200, shared limits
work across workers, logs contain no credentials, and the assignment/sync
audit-chain verifiers pass.

## Operations and monitoring

Monitor readiness failures, HTTP 5xx/429 rates, authentication and
authorization failures, audit persistence failures, Neon latency/connections,
Redis availability, and Sentry events. Treat any audit persistence failure as
a security-relevant incident because protected mutations and sync responses
fail closed when evidence cannot be stored.

Export evidence read-only, in event order, with event UUID, canonical evidence,
hash, and predecessor hash. Never update or delete forensic rows. Rotation of
`POLICY_SYNC_AUDIT_KEY` starts new pseudonym identities; preserve controlled
key-version records outside the database if continuity must be demonstrated.

## Rollback and recovery

Roll application code back only to a release compatible with the current
schema. Forensic migrations are forward-only after evidence exists; their
downgrades intentionally refuse data loss. Database restoration requires
recorded authorization, a preserved copy of the affected database/evidence,
and a post-restore chain verification. Record incident times and operator
identity outside the affected system.
