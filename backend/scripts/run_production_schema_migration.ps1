# Explicit production schema migration for the confirmed fresh installation.
# Run under the same Windows account that saved the encrypted handoff.
$ErrorActionPreference = 'Stop'
$edugBackend = Split-Path -Parent $PSScriptRoot
$edugPython = Join-Path $edugBackend 'venv\Scripts\python.exe'
$edugHandoff = Join-Path $edugBackend 'operator-evidence\production-migration-url.clixml'
$edugPointer = [IntPtr]::Zero
$edugSecure = $null

if (-not (Test-Path -LiteralPath $edugPython)) { throw 'Backend Python environment is missing.' }
if (-not (Test-Path -LiteralPath $edugHandoff)) { throw 'Encrypted production handoff is missing.' }

$edugMigration = @'
import json
import os
from pathlib import Path

from flask import Flask
from flask_migrate import Migrate, upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.extensions import db

EXPECTED_HEAD = "a6d4e8f2b1c7"
EXPECTED_TABLES = {
    "administrator_authentication_events",
    "administrator_permissions",
    "administrator_sessions",
    "administrators",
    "alembic_version",
    "device_audit_batches",
    "device_audit_chain_heads",
    "device_check_ins",
    "device_compliance_states",
    "device_credentials",
    "device_enrollment_events",
    "device_policy_assignments",
    "device_policy_states",
    "device_registration_events",
    "device_request_nonces",
    "device_security_events",
    "devices",
    "enrollment_tokens",
    "policies",
    "policy_application_events",
    "policy_assignment_chain_heads",
    "policy_assignment_events",
    "policy_revisions",
    "policy_synchronization_chain_heads",
    "policy_synchronization_events",
}

result = {"production_schema_migration": "FAIL", "stage": "connection"}
engine = None
try:
    raw = os.environ.pop("EDUG_PRODUCTION_MIGRATION_URL")
    engine = create_engine(raw, pool_pre_ping=True, poolclass=NullPool)

    # Repeat the destructive-operation gates immediately before Alembic runs.
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            result["stage"] = "pre_migration_gate"
            assert connection.execute(text("SELECT current_database()")).scalar_one() == "postgres"
            assert connection.execute(text("SELECT current_user")).scalar_one() == "postgres"
            assert connection.execute(
                text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")
            ).scalar_one() is True
            assert connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE'"
                )
            ).scalar_one() == 0
            assert connection.execute(
                text("SELECT to_regclass('public.alembic_version') IS NULL")
            ).scalar_one() is True
        finally:
            transaction.rollback()

    result["stage"] = "alembic_upgrade"
    app = Flask("edug_production_schema_migration")
    app.config.update(
        APP_ENV="production",
        SQLALCHEMY_DATABASE_URI=raw,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MIGRATION_DATABASE_URI=raw,
    )
    db.init_app(app)
    from app import models  # noqa: F401
    Migrate(app, db, compare_type=True)
    with app.app_context():
        upgrade(directory=str(Path.cwd() / "migrations"), revision="head")

    result["stage"] = "post_migration_verification"
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            head = connection.execute(
                text("SELECT version_num FROM public.alembic_version")
            ).scalar_one()
            tables = set(
                connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_type='BASE TABLE'"
                    )
                ).scalars()
            )
            assert head == EXPECTED_HEAD
            assert tables == EXPECTED_TABLES
        finally:
            transaction.rollback()

    result = {
        "production_schema_migration": "PASS",
        "alembic_head": EXPECTED_HEAD,
        "public_tables": len(EXPECTED_TABLES),
        "runtime_security": "pending",
    }
except Exception as error:
    diagnostic = str(error).lower()
    reason = "migration_or_verification_failed"
    for fragment, label in (
        ("password authentication failed", "authentication_failed"),
        ("tenant or user not found", "pooler_user_not_found"),
        ("certificate verify failed", "certificate_verification_failed"),
        ("could not translate host name", "dns_failed"),
        ("timeout expired", "connection_timeout"),
        ("assert", "verification_failed"),
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
    # Safe recovery evidence: object names are compared locally and never emitted.
    try:
        if engine is not None:
            with engine.connect() as diagnostic_connection:
                diagnostic_transaction = diagnostic_connection.begin()
                try:
                    diagnostic_connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                    existing_tables = set(
                        diagnostic_connection.execute(
                            text(
                                "SELECT table_name FROM information_schema.tables "
                                "WHERE table_schema='public' AND table_type='BASE TABLE'"
                            )
                        ).scalars()
                    )
                    version_exists = "alembic_version" in existing_tables
                    current_revision = None
                    if version_exists:
                        current_revision = diagnostic_connection.execute(
                            text("SELECT version_num FROM public.alembic_version")
                        ).scalar_one_or_none()
                    result["recovery_state"] = {
                        "public_tables": len(existing_tables),
                        "alembic_revision": current_revision or "absent",
                        "unexpected_tables": bool(existing_tables - EXPECTED_TABLES),
                    }
                finally:
                    diagnostic_transaction.rollback()
    except Exception:
        result["recovery_state"] = "unavailable"
finally:
    if engine is not None:
        engine.dispose()

print(json.dumps(result), flush=True)
raise SystemExit(0 if result["production_schema_migration"] == "PASS" else 1)
'@

try {
    $edugSecure = Import-Clixml -LiteralPath $edugHandoff
    $edugPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($edugSecure)
    $env:EDUG_PRODUCTION_MIGRATION_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($edugPointer)
    Push-Location $edugBackend
    try {
        $edugOutput = @($edugMigration | & $edugPython -)
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
