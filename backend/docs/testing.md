# Backend test classification

The backend separates fast SQLite tests from tests that depend on PostgreSQL
semantics or may change database state.

## Markers

- `unit` identifies isolated tests that do not require PostgreSQL semantics.
- `postgres` identifies tests that connect only to the approved Neon test
  branch.
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
non-secret branch marker
`POSTGRES_TEST_BRANCH_NAME=backend-integration-test`, a pooled Neon
`POSTGRES_TEST_DATABASE_URL`, the exact non-secret
`POSTGRES_TEST_ENDPOINT_ID` extracted from the approved branch connection
hostname, PostgreSQL TLS, and separation from configured
development and production branches. Migration selections also require a
direct `MIGRATION_DATABASE_URL` for the same test endpoint. Validation errors
name variables but never render database URLs or credentials.

The human-readable branch marker documents the approved purpose. The endpoint
marker binds that approval to the unique Neon compute endpoint encoded in both
the pooled and direct URLs, and the connected-session guard verifies that same
endpoint after libpq connects. Add both non-secret markers manually to the
local `.env`. Never place credentials in `.env.example`.

Passing the guard does not itself connect, migrate, write, reset, downgrade,
delete, or run concurrency operations. Fixtures for any destructive operation
must call the guard with its destructive requirement enabled.

Destructive PostgreSQL execution additionally requires an exact
`ALLOW_DESTRUCTIVE_POSTGRES_TESTS=true` value and the separately required user
approval. Never use development or production database URLs for these tests.
