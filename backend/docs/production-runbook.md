# Production deployment and recovery runbook

## Non-negotiable pre-deployment gates

1. Rotate every former database-provider password and application secret that appeared in
   `.history` or `.github/env.txt`. Historical values are compromised even
   after file deletion.
2. Scan the current tree and all Git revisions with an approved secret scanner.
   Do not deploy until it reports no live credentials.
3. After taking a separate recoverable mirror, purge `.history` and
   `.github/env.txt` from Git history with `git filter-repo`. The repository
   owner performs the force-push; every collaborator must re-clone afterward.
4. Confirm separate development, integration-test, staging and production
   Supabase projects and follow the direct/session, verify-full TLS
   configuration in the migration runbook.
5. Run the complete quality workflow and the explicitly safety-gated PostgreSQL
   migration/concurrency suite on `backend-integration-test`.

## Secret hygiene and history recovery

Do not paste credentials into source files, shell transcripts, issue comments,
or documentation. Use server-only provider secret variables, database credentials, Redis
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

## Railway deployment

The step-by-step [database migration runbook](database-migration-runbook.md)
is authoritative for the Supabase/Railway transition. `backend/railway.json`
uses Railpack, a separate pre-deploy migration, Gunicorn and dependency-aware
readiness. `gunicorn.conf.py` uses one worker/four threads, binding Railway PORT,
with a five-connection default pool ceiling per instance. Include deployment
overlap and provider services when checking the real database connection limit.

Before production migration, verify an independent backup through a restore
rehearsal. Railway runs `flask --app run.py db upgrade` once in pre-deploy only
after operator approval and restored migration-state reconciliation.
Gunicorn workers must never run migrations. A deployment is acceptable only
when `/api/v1/health` returns 200, `/api/v1/ready` returns 200, shared limits
work across workers, logs contain no credentials, and the assignment/sync
audit-chain verifiers pass.

## Operations and monitoring

Monitor readiness failures, HTTP 5xx/429 rates, authentication and
authorization failures, audit persistence failures, database latency/connections,
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

After target writes begin, the retained source is stale. Never switch back to
it without preserving/reconciling target writes under explicit approval.
Prefer a schema/provider-compatible rollback release on the target. No history
rewrite, source deletion, forensic downgrade or secret rotation is automated
by this implementation.
