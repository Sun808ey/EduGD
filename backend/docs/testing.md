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

The following selections are reserved for later harness increments:

```powershell
python -m pytest -m postgres
python -m pytest -m migration
python -m pytest -m concurrency
```

At the current harness stage, these explicit selections are rejected before
collection. Harness increment B will replace that temporary block with the
reusable database safety guard. Database-category tests must continue to fail
closed unless that guard validates the dedicated test branch. Marker
registration alone does not grant permission to connect, migrate, write, reset,
downgrade, delete, or run concurrency operations.

Destructive PostgreSQL execution additionally requires an exact
`ALLOW_DESTRUCTIVE_POSTGRES_TESTS=true` value and the separately required user
approval. Never use development or production database URLs for these tests.
