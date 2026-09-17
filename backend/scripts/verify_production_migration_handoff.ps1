# Run under the same Windows account that saved the encrypted handoff.
# Output is deliberately redacted: never print the URL or provider exception.
$ErrorActionPreference = 'Stop'
$edugBackend = Split-Path -Parent $PSScriptRoot
$edugPython = Join-Path $edugBackend 'venv\Scripts\python.exe'
$edugHandoff = Join-Path $edugBackend 'operator-evidence\production-migration-url.clixml'
$edugPointer = [IntPtr]::Zero
$edugSecure = $null

if (-not (Test-Path -LiteralPath $edugPython)) { throw 'Backend Python environment is missing.' }
if (-not (Test-Path -LiteralPath $edugHandoff)) { throw 'Encrypted production handoff is missing.' }

$edugCheck = @'
import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

result = {"production_preflight": "FAIL", "stage": "local_identity"}
engine = None
try:
    raw = os.environ.pop("EDUG_PRODUCTION_MIGRATION_URL")
    url = make_url(raw)
    assert url.database == "postgres"
    assert url.port == 5432
    assert url.username == "postgres.hszskxrgkptbytuquyfu"
    assert url.host == "aws-1-eu-west-1.pooler.supabase.com"
    assert url.query.get("sslmode") == "verify-full"

    result["stage"] = "connection"
    engine = create_engine(raw, pool_pre_ping=True, connect_args={"connect_timeout": 15})
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            result["stage"] = "database_identity"
            assert connection.execute(text("SELECT current_database()")).scalar_one() == "postgres"
            assert connection.execute(text("SELECT current_user")).scalar_one() == "postgres"

            result["stage"] = "tls"
            assert connection.execute(
                text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
            ).scalar_one() is True

            result["stage"] = "migration_capability"
            capability = connection.execute(
                text(
                    "SELECT "
                    "has_database_privilege(current_user, current_database(), 'CONNECT'), "
                    "has_schema_privilege(current_user, 'public', 'USAGE'), "
                    "has_schema_privilege(current_user, 'public', 'CREATE') "
                    "FROM pg_namespace WHERE nspname = 'public'"
                )
            ).one()
            assert tuple(capability) == (True, True, True)

            result["stage"] = "empty_schema"
            table_count = connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE'"
                )
            ).scalar_one()
            alembic_exists = connection.execute(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            ).scalar_one()
            assert table_count == 0
            assert alembic_exists is False
        finally:
            transaction.rollback()

    result = {
        "production_preflight": "PASS",
        "database": "postgres",
        "role": "migration_owner",
        "migration_capability": "verified",
        "tls": "verified",
        "public_tables": 0,
        "alembic_version": "absent",
        "writes": "none",
    }
except Exception as error:
    diagnostic = str(error).lower()
    reason = "preflight_check_failed"
    for fragment, label in (
        ("password authentication failed", "authentication_failed"),
        ("tenant or user not found", "pooler_user_not_found"),
        ("certificate verify failed", "certificate_verification_failed"),
        ("could not translate host name", "dns_failed"),
        ("timeout expired", "connection_timeout"),
    ):
        if fragment in diagnostic:
            reason = label
            break
    result["reason"] = reason
finally:
    if engine is not None:
        engine.dispose()

print(json.dumps(result), flush=True)
raise SystemExit(0 if result["production_preflight"] == "PASS" else 1)
'@

try {
    $edugSecure = Import-Clixml -LiteralPath $edugHandoff
    $edugPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($edugSecure)
    $env:EDUG_PRODUCTION_MIGRATION_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($edugPointer)
    Push-Location $edugBackend
    try {
        $edugOutput = @($edugCheck | & $edugPython -)
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
