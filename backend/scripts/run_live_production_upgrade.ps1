# Live additive production upgrade runner. Run only during an approved maintenance
# window and only under the Windows account that encrypted the migration handoff.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupRestoreEvidence,
    [Parameter(Mandatory = $true)]
    [switch]$MaintenanceWindowConfirmed
)

$ErrorActionPreference = 'Stop'
$edugBackend = Split-Path -Parent $PSScriptRoot
$edugPython = Join-Path $edugBackend 'venv\Scripts\python.exe'
$edugHandoff = Join-Path $edugBackend 'operator-evidence\production-migration-url.clixml'
$edugEvidence = Resolve-Path -LiteralPath $BackupRestoreEvidence -ErrorAction Stop
$edugPointer = [IntPtr]::Zero
$edugSecure = $null

if (-not $MaintenanceWindowConfirmed) { throw 'An approved maintenance window is required.' }
if (-not (Test-Path -LiteralPath $edugPython)) { throw 'Backend Python environment is missing.' }
if (-not (Test-Path -LiteralPath $edugHandoff)) { throw 'Encrypted production handoff is missing.' }

# The evidence contains no credentials. It is an operator attestation for a
# completed backup-and-restore rehearsal against this exact production revision.
$edugAttestation = Get-Content -LiteralPath $edugEvidence -Raw | ConvertFrom-Json
if (
    $edugAttestation.status -ne 'PASS' -or
    $edugAttestation.project_ref -ne 'hszskxrgkptbytuquyfu' -or
    $edugAttestation.before_revision -ne 'ab4e6f2c9d71' -or
    -not $edugAttestation.restore_completed_at -or
    -not $edugAttestation.artifact_sha256 -or
    -not $edugAttestation.restore_inventory_sha256 -or
    -not $edugAttestation.migration_log_sha256 -or
    -not $edugAttestation.archive_path -or
    $edugAttestation.artifact_sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
    $edugAttestation.restore_inventory_sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
    $edugAttestation.migration_log_sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
    -not (Test-Path -LiteralPath $edugAttestation.archive_path) -or
    ((Get-FileHash -LiteralPath $edugAttestation.archive_path -Algorithm SHA256).Hash -ne $edugAttestation.artifact_sha256)
) { throw 'Backup-and-restore rehearsal evidence is incomplete or does not match production.' }

$edugUpgrade = @'
import json
import os
from pathlib import Path

from flask import Flask
from flask_migrate import Migrate, upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.extensions import db

PROJECT_REF = "hszskxrgkptbytuquyfu"
EXPECTED_START = "ab4e6f2c9d71"
EXPECTED_HEAD = "c2f8a1b4d630"
EXPECTED_HOST = "aws-1-eu-west-1.pooler.supabase.com"
EXPECTED_USER = "postgres.hszskxrgkptbytuquyfu"
NEW_RELEASE_TABLES = {"device_web_filter_events"}
HARDENED_FUNCTIONS = {
    "edug_reject_certification_mutation", "edug_reject_device_audit_mutation",
    "edug_reject_device_control_event_mutation",
    "edug_reject_device_status_evidence_mutation",
    "edug_reject_policy_assignment_event_mutation",
    "edug_reject_policy_revision_mutation",
    "edug_reject_policy_sync_event_mutation", "edug_valid_blocked_apps",
    "edug_valid_policy_revision_payload",
}

result = {"production_schema_migration": "FAIL", "stage": "local_identity"}
engine = None
lock_connection = None


def require(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(label)


try:
    raw = os.environ.pop("EDUG_PRODUCTION_MIGRATION_URL")
    require(os.environ.pop("EDUG_BACKUP_RESTORE_EVIDENCE") == "PASS", "backup evidence missing")
    url = make_url(raw)
    require(url.database == "postgres", "unexpected database")
    require(url.host == EXPECTED_HOST and url.port == 5432, "unexpected migration host")
    require(url.username == EXPECTED_USER, "unexpected migration role")
    require(url.query.get("sslmode") == "verify-full", "TLS verification is required")
    ca_path = url.query.get("sslrootcert")
    require(bool(ca_path and Path(ca_path).is_file()), "migration CA is unavailable")

    engine = create_engine(raw, pool_pre_ping=True, poolclass=NullPool)
    result["stage"] = "read_only_inventory"
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            require(connection.execute(text("SELECT current_database()")).scalar_one() == "postgres", "unexpected database")
            require(connection.execute(text("SELECT current_user")).scalar_one() == "postgres", "unexpected migration owner")
            require(connection.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")).scalar_one() is True, "TLS is unavailable")
            current = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
            require(current == EXPECTED_START, "unexpected Alembic starting revision")
            inventory = set(connection.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE'"
            )).scalars())
        finally:
            transaction.rollback()

    app = Flask("edug_live_production_upgrade")
    app.config.update(
        APP_ENV="production", SQLALCHEMY_DATABASE_URI=raw,
        SQLALCHEMY_TRACK_MODIFICATIONS=False, MIGRATION_DATABASE_URI=raw,
    )
    db.init_app(app)
    from app import models  # noqa: F401
    expected_final = {table.name for table in db.metadata.sorted_tables} | {"alembic_version"}
    require(inventory == expected_final - NEW_RELEASE_TABLES, "unexpected public schema inventory")

    # Keep this session open throughout the upgrade so a second approved runner
    # cannot run concurrently. The maintenance-window gate protects application writers.
    lock_connection = engine.connect()
    require(lock_connection.execute(text(
        "SELECT pg_try_advisory_lock(hashtext('edug-production-schema-upgrade'))"
    )).scalar_one() is True, "production migration lock is unavailable")

    result["stage"] = "alembic_upgrade"
    Migrate(app, db, compare_type=True)
    with app.app_context():
        upgrade(directory=str(Path.cwd() / "migrations"), revision=EXPECTED_HEAD)

    result["stage"] = "post_migration_verification"
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            require(connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one() == EXPECTED_HEAD, "final Alembic revision mismatch")
            tables = set(connection.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE'"
            )).scalars())
            require(tables == expected_final, "unexpected final public schema")
            require(connection.execute(text(
                "SELECT bool_and(c.relrowsecurity) FROM pg_class c "
                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relkind='r'"
            )).scalar_one() is True, "RLS verification failed")
            require(connection.execute(text(
                "SELECT bool_and(has_table_privilege('edug_runtime', "
                "quote_ident(table_schema)||'.'||quote_ident(table_name), 'SELECT')) "
                "FROM information_schema.tables WHERE table_schema='public' "
                "AND table_type='BASE TABLE'"
            )).scalar_one() is True, "runtime read grants are incomplete")
            require(connection.execute(text(
                "SELECT NOT has_table_privilege('anon', 'public.administrators', 'SELECT') "
                "AND NOT has_table_privilege('authenticated', 'public.administrators', 'SELECT')"
            )).scalar_one() is True, "Data API roles retain administrator access")
            triggers = set(connection.execute(text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid IN "
                "('public.device_audit_batches'::regclass, "
                "'public.device_control_events'::regclass, "
                "'public.device_web_filter_events'::regclass) AND NOT tgisinternal"
            )).scalars())
            require({
                "trg_device_audit_batches_immutable",
                "trg_device_control_events_immutable",
                "trg_device_web_filter_events_immutable",
            } <= triggers, "immutable trigger verification failed")
            require(connection.execute(text(
                "SELECT pg_get_constraintdef(oid) LIKE '%policy.manage%' "
                "FROM pg_constraint WHERE conrelid='public.administrator_permissions'::regclass "
                "AND conname='ck_administrator_permissions_permission'"
            )).scalar_one() is True, "policy management permission verification failed")
            configured = set(connection.execute(text(
                "SELECT p.proname FROM pg_proc p JOIN pg_namespace n "
                "ON n.oid=p.pronamespace WHERE n.nspname='public' "
                "AND p.proname = ANY(:names) "
                "AND COALESCE(p.proconfig, ARRAY[]::text[]) @> ARRAY['search_path=\"\"'] "
                "AND has_function_privilege('edug_runtime', p.oid, 'EXECUTE') "
                "AND NOT has_function_privilege('anon', p.oid, 'EXECUTE') "
                "AND NOT has_function_privilege('authenticated', p.oid, 'EXECUTE') "
                "AND NOT has_function_privilege('service_role', p.oid, 'EXECUTE')"
            ), {"names": list(HARDENED_FUNCTIONS)}).scalars())
            require(configured == HARDENED_FUNCTIONS, "function hardening verification failed")
        finally:
            transaction.rollback()
    result = {
        "production_schema_migration": "PASS", "alembic_head": EXPECTED_HEAD,
        "tls": "verified", "runtime_security": "verified",
    }
except Exception as error:
    diagnostic = str(error).lower()
    result["reason"] = next((label for fragment, label in (
        ("certificate verify failed", "certificate_verification_failed"),
        ("root certificate file", "ca_file_unavailable"),
        ("password authentication failed", "authentication_failed"),
        ("timeout expired", "connection_timeout"),
    ) if fragment in diagnostic), "migration_or_verification_failed")
    result["error_type"] = type(error).__name__
finally:
    if lock_connection is not None:
        try:
            lock_connection.execute(text("SELECT pg_advisory_unlock(hashtext('edug-production-schema-upgrade'))"))
        finally:
            lock_connection.close()
    if engine is not None:
        engine.dispose()

print(json.dumps(result), flush=True)
raise SystemExit(0 if result["production_schema_migration"] == "PASS" else 1)
'@

try {
    $edugSecure = Import-Clixml -LiteralPath $edugHandoff
    $edugPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($edugSecure)
    $env:EDUG_PRODUCTION_MIGRATION_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($edugPointer)
    $env:EDUG_BACKUP_RESTORE_EVIDENCE = 'PASS'
    Push-Location $edugBackend
    try {
        $edugOutput = @($edugUpgrade | & $edugPython -)
        $edugExitCode = $LASTEXITCODE
        $edugOutput | Write-Output
        if ($edugExitCode -ne 0) { throw 'Live production upgrade failed.' }
    } finally { Pop-Location }
} finally {
    Remove-Item Env:EDUG_PRODUCTION_MIGRATION_URL -ErrorAction SilentlyContinue
    Remove-Item Env:EDUG_BACKUP_RESTORE_EVIDENCE -ErrorAction SilentlyContinue
    if ($edugPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($edugPointer) }
    if ($null -ne $edugSecure) { $edugSecure.Dispose() }
}
