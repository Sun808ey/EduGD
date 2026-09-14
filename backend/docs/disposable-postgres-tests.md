# Disposable PostgreSQL integration checks

The local Compose stack runs PostgreSQL 17 and the pinned Python test libraries
without a hosted database or cloud credit consumption. It exercises ordinary
PostgreSQL migration, schema and concurrency behavior, not Supabase platform
permissions or deployed network paths. Those remain separate checks.

Start Docker Desktop's Linux engine, then run from `backend`:

```powershell
docker compose -f compose.postgres-test.yml run --build --rm tests
```

After the run, remove only this named stack and its disposable certificate volume:

```powershell
docker compose -f compose.postgres-test.yml down --volumes
```

No ports are published. The runtime network is internal and the database lives
in tmpfs. `db.eduglocaltest0000001.supabase.co` is a Docker DNS alias for this
local container, not a real Supabase assignment. The alias preserves the existing
identity and verify-full TLS validation. A temporary certificate is generated
inside the stack and shared read-only with PostgreSQL and the test runner.
Its private key never enters the repository or image. The fixed disposable
password is only for this isolated synthetic database; never reuse it elsewhere.
Image/dependency downloads require internet during build, not hosted credentials.

The runner image uses explicit COPY paths and a restrictive `.dockerignore` to
exclude local credentials, evidence and virtual environments. Both approved
Supabase references are unconditionally rejected by test safety validation,
even if protected environment variables are absent.

The revised GitHub workflow uses this same stack through manual dispatch, without
a GitHub environment or database secrets. Existing remote workflow behavior does
not change until the owner commits and pushes these edits. Check Actions Free
quota before dispatch; no paid capacity is authorized.

Validation: all 38 isolated PostgreSQL/migration/concurrency tests passed, and
the default backend suite passed 495 tests. Targeted identity, test-safety and
Compose configuration checks passed separately. Ruff lint/format and mypy passed.
An authorization test now uses the admin route whose error envelope it asserts.
Certificate initialization is idempotent during repeated runs; a fresh teardown
and run also passed. Cleanup removed the stack and temporary certificate volume.
These results do not establish hosted connectivity or application readiness.

The old hosted workflow was disabled on GitHub on 14 September 2026 and verified
`disabled_manually`. Re-enable only after the safe replacement reaches the
default branch and Free Actions availability is confirmed.
