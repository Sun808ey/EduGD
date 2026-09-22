# Backend test classification

The backend separates fast SQLite tests from tests that depend on PostgreSQL
semantics or may change database state.

## Markers

- `unit` identifies isolated tests that do not require PostgreSQL semantics.
- `postgres` identifies tests that connect only to the approved dedicated
  Supabase test project.
- `migration` identifies tests that inspect or change PostgreSQL migration
  state.
- `concurrency` identifies bounded PostgreSQL transaction or race tests.

Tests without a PostgreSQL category are classified as `unit` during collection.
A PostgreSQL test must declare every applicable category explicitly.

## Safe default

The default command is intentionally limited to tests that are not categorized
as PostgreSQL, migration, or concurrency tests:

```powershell
python -m pytest
```

The equivalent configured selection is:

```text
not postgres and not migration and not concurrency
```

## Explicit selections

Run the isolated suite explicitly with:

```powershell
python -m pytest -m unit
```

PostgreSQL categories must be selected explicitly:

```powershell
python -m pytest -m postgres
python -m pytest -m migration
python -m pytest -m concurrency
```

Before collecting one of these selections, the reusable database safety guard
validates configuration without opening a connection. It requires the exact
non-secret purpose marker `POSTGRES_TEST_PURPOSE=backend-integration-test`, the
exact non-secret `POSTGRES_TEST_PROJECT_REF`, a direct or session-pooler
`POSTGRES_TEST_DATABASE_URL`, `sslmode=verify-full`, and separation from
configured development and production projects. Migration selections also
require `MIGRATION_DATABASE_URL` for the same project and database. Validation
errors name variables but never render database URLs or credentials.

The purpose marker records why the target is approved. The project reference
binds that approval to the tenant encoded in the configured URLs, and the
connected-session guard verifies the exact host, role, port, database and TLS
state after libpq connects. Add both non-secret markers manually to the local
`.env`. Never place credentials in `.env.example`.

Passing the guard does not itself connect, migrate, write, reset, downgrade,
delete, or run concurrency operations. Fixtures for any destructive operation
must call the guard with its destructive requirement enabled.

Destructive PostgreSQL execution additionally requires an exact
`ALLOW_DESTRUCTIVE_POSTGRES_TESTS=true` value and the separately required user
approval. Never use development or production database URLs for these tests.

## Supabase test approval

The purpose marker is `POSTGRES_TEST_PURPOSE=backend-integration-test`. Set
`POSTGRES_TEST_PROJECT_REF` to the exact approved project
reference and configure runtime/migration URLs for that project and database.
Use direct or session-pooler port 5432 with `sslmode=verify-full`. Tenant-qualified
pooler usernames are mandatory. Do not reuse a production project with another
schema or role. The guard also checks the actual libpq host, user/tenant,
database, port and TLS. It does not create, clear or approve a project.

After separate destructive-test approval, run the CI selection on the EMPTY
disposable test project only:

```powershell
python -m pytest -m "postgres or migration or concurrency"
```

Do not run this command on a production-data restore rehearsal. Read-only
source/target verification uses `scripts.database_inventory`, described in the
[migration runbook](database-migration-runbook.md). Unavailable external tests
remain unresolved deployment gates, not passing tests.

For a local Windows pytest temporary-directory permission error, rerun with
authorized filesystem access; do not disable or remove migration tests.
