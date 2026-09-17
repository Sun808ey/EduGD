# Apply and verify the reviewed production runtime grants and RLS policies.
# Run under the same Windows account that saved the encrypted owner handoff.
$ErrorActionPreference = 'Stop'
$edugBackend = Split-Path -Parent $PSScriptRoot
$edugPython = Join-Path $edugBackend 'venv\Scripts\python.exe'
$edugHandoff = Join-Path $edugBackend 'operator-evidence\production-migration-url.clixml'
$edugPointer = [IntPtr]::Zero
$edugSecure = $null

if (-not (Test-Path -LiteralPath $edugPython)) { throw 'Backend Python environment is missing.' }
if (-not (Test-Path -LiteralPath $edugHandoff)) { throw 'Encrypted production handoff is missing.' }

$edugSecurity = @'
import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

EXPECTED_HEAD = "e4a1b7c9d2f6"
TABLES = (
    "administrator_authentication_events",
    "administrator_permissions",
    "administrator_sessions",
    "administrators",
    "alembic_version",
    "device_credentials",
    "device_enrollment_events",
    "device_policy_assignments",
    "device_registration_events",
    "device_request_nonces",
    "devices",
    "enrollment_tokens",
    "policies",
    "policy_assignment_chain_heads",
    "policy_assignment_events",
    "policy_revisions",
    "policy_synchronization_chain_heads",
    "policy_synchronization_events",
)
READ_WRITE = {
    "administrators",
    "administrator_permissions",
    "administrator_sessions",
    "devices",
    "policies",
    "enrollment_tokens",
    "device_credentials",
    "device_policy_assignments",
    "policy_assignment_chain_heads",
    "policy_synchronization_chain_heads",
}
NONCE_TABLE = "device_request_nonces"
APPEND_ONLY = {
    "policy_revisions",
    "device_registration_events",
    "administrator_authentication_events",
    "device_enrollment_events",
    "policy_assignment_events",
    "policy_synchronization_events",
}
PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
DATA_API_ROLES = ("anon", "authenticated", "service_role")

def expected_privileges(table):
    allowed = {"SELECT"}
    if table in READ_WRITE:
        allowed.update(("INSERT", "UPDATE"))
    elif table == NONCE_TABLE:
        allowed.update(("INSERT", "DELETE"))
    elif table in APPEND_ONLY:
        allowed.add("INSERT")
    return allowed

result = {"production_runtime_security": "FAIL", "stage": "connection"}
engine = None
try:
    raw = os.environ.pop("EDUG_PRODUCTION_MIGRATION_URL")
    engine = create_engine(raw, pool_pre_ping=True, poolclass=NullPool)
    with engine.begin() as connection:
        result["stage"] = "prechange_gate"
        assert connection.execute(text("SELECT current_database()")).scalar_one() == "postgres"
        assert connection.execute(text("SELECT current_user")).scalar_one() == "postgres"
        assert connection.execute(
            text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
        ).scalar_one() is True
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one() == EXPECTED_HEAD
        existing_tables = set(
            connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE'"
                )
            ).scalars()
        )
        assert existing_tables == set(TABLES)
        runtime_role = connection.execute(
            text(
                "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
                "rolreplication, rolbypassrls FROM pg_roles WHERE rolname='edug_runtime'"
            )
        ).one_or_none()
        assert runtime_role is not None
        assert tuple(runtime_role) == (True, False, False, False, False, False)

        result["stage"] = "apply_security"
        connection.execute(text("GRANT CONNECT ON DATABASE postgres TO edug_runtime"))
        connection.execute(text("GRANT USAGE ON SCHEMA public TO edug_runtime"))
        connection.execute(text("REVOKE CREATE ON SCHEMA public FROM PUBLIC, edug_runtime"))

        for table in TABLES:
            for role in ("PUBLIC", *DATA_API_ROLES, "edug_runtime"):
                connection.execute(text(f"REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM {role}"))
            connection.execute(text(f"GRANT SELECT ON TABLE public.{table} TO edug_runtime"))
            allowed = expected_privileges(table)
            for privilege in ("INSERT", "UPDATE", "DELETE"):
                if privilege in allowed:
                    connection.execute(
                        text(f"GRANT {privilege} ON TABLE public.{table} TO edug_runtime")
                    )
            connection.execute(text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
            connection.execute(
                text(f"DROP POLICY IF EXISTS edug_backend_runtime ON public.{table}")
            )
            connection.execute(
                text(
                    f"CREATE POLICY edug_backend_runtime ON public.{table} "
                    "AS PERMISSIVE FOR ALL TO edug_runtime USING (true) WITH CHECK (true)"
                )
            )

        for role in ("PUBLIC", *DATA_API_ROLES, "edug_runtime"):
            connection.execute(
                text(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {role}")
            )
        connection.execute(
            text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO edug_runtime")
        )

        # Future migrations must grant deliberately; avoid implicit Data API/runtime access.
        for role in ("PUBLIC", *DATA_API_ROLES, "edug_runtime"):
            connection.execute(
                text(
                    f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
                    f"REVOKE ALL ON TABLES FROM {role}"
                )
            )
            connection.execute(
                text(
                    f"ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
                    f"REVOKE ALL ON SEQUENCES FROM {role}"
                )
            )

        result["stage"] = "catalog_verification"
        permission_checks = 0
        for table in TABLES:
            allowed = expected_privileges(table)
            for privilege in PRIVILEGES:
                actual = connection.execute(
                    text("SELECT has_table_privilege('edug_runtime', :relation, :privilege)"),
                    {"relation": f"public.{table}", "privilege": privilege},
                ).scalar_one()
                assert actual is (privilege in allowed)
                permission_checks += 1
            for role in DATA_API_ROLES:
                for privilege in PRIVILEGES:
                    assert connection.execute(
                        text("SELECT has_table_privilege(:role, :relation, :privilege)"),
                        {
                            "role": role,
                            "relation": f"public.{table}",
                            "privilege": privilege,
                        },
                    ).scalar_one() is False

        rls_tables = connection.execute(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=ANY(:tables) AND c.relrowsecurity"
            ),
            {"tables": list(TABLES)},
        ).scalar_one()
        policies = connection.execute(
            text(
                "SELECT count(*) FROM pg_policies WHERE schemaname='public' "
                "AND tablename=ANY(:tables) AND policyname='edug_backend_runtime' "
                "AND cmd='ALL' AND roles=ARRAY['edug_runtime']::name[]"
            ),
            {"tables": list(TABLES)},
        ).scalar_one()
        assert rls_tables == len(TABLES)
        assert policies == len(TABLES)
        assert permission_checks == 126

    result = {
        "production_runtime_security": "PASS",
        "permission_checks": 126,
        "rls_tables": 18,
        "runtime_policies": 18,
        "data_api_roles": "denied",
    }
except Exception as error:
    diagnostic = str(error).lower()
    reason = "security_change_or_verification_failed"
    for fragment, label in (
        ("password authentication failed", "authentication_failed"),
        ("does not exist", "required_role_or_object_missing"),
        ("permission denied", "owner_permission_denied"),
        ("certificate verify failed", "certificate_verification_failed"),
        ("timeout expired", "connection_timeout"),
    ):
        if fragment in diagnostic:
            reason = label
            break
    result["reason"] = reason
    result["error_type"] = type(error).__name__
    original = getattr(error, "orig", None)
    sqlstate = getattr(original, "pgcode", None) or getattr(original, "sqlstate", None)
    if sqlstate:
        result["sqlstate"] = str(sqlstate)
finally:
    if engine is not None:
        engine.dispose()

print(json.dumps(result), flush=True)
raise SystemExit(0 if result["production_runtime_security"] == "PASS" else 1)
'@

try {
    $edugSecure = Import-Clixml -LiteralPath $edugHandoff
    $edugPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($edugSecure)
    $env:EDUG_PRODUCTION_MIGRATION_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($edugPointer)
    Push-Location $edugBackend
    try {
        $edugOutput = @($edugSecurity | & $edugPython -)
        $edugExitCode = $LASTEXITCODE
        $edugOutput | Write-Output
        if ($edugExitCode -ne 0) { throw 'Embedded verification failed.' }
    } finally { Pop-Location }
} finally {
    Remove-Item Env:EDUG_PRODUCTION_MIGRATION_URL -ErrorAction SilentlyContinue
    if ($edugPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($edugPointer)
    }
    if ($null -ne $edugSecure) { $edugSecure.Dispose() }
}
