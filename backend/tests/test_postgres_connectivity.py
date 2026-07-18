from contextlib import closing
from typing import Any

import psycopg2
import pytest
from flask import Flask
from sqlalchemy import event

from app.extensions import db
from app.services.readiness import check_readiness
from test_support.postgres_safety import (
    validate_connected_postgres_test_environment,
    validate_postgres_test_environment,
)

CONNECT_TIMEOUT_SECONDS = 10
STATEMENT_TIMEOUT_MILLISECONDS = 10_000


@pytest.mark.postgres
def test_approved_postgres_connection_is_read_only_and_uses_tls() -> None:
    approved = validate_postgres_test_environment()
    failure_phase = "connection"

    try:
        connection = psycopg2.connect(
            approved.application_database_url,
            application_name="edug-nondestructive-connectivity-test",
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
        )
        with closing(connection):
            validate_connected_postgres_test_environment(connection, approved)
            failure_phase = "read-only session setup"
            connection.set_session(readonly=True, autocommit=False)
            failure_phase = "metadata query"
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL statement_timeout = %s",
                    (str(STATEMENT_TIMEOUT_MILLISECONDS),),
                )
                cursor.execute(
                    """
                    SELECT
                        1,
                        version() LIKE 'PostgreSQL %',
                        current_setting('server_version_num') ~ '^[0-9]+$',
                        current_setting('transaction_read_only') = 'on'
                    """
                )
                result = cursor.fetchone()
            failure_phase = "transaction cleanup"
            connection.rollback()
    except psycopg2.Error as error:
        exception_class = type(error).__name__
        sqlstate_status = "available" if error.diag.sqlstate else "absent"
        raise AssertionError(
            "Approved PostgreSQL connectivity probe failed during "
            f"{failure_phase}; driver class={exception_class}; "
            f"SQLSTATE={sqlstate_status}"
        ) from None

    assert result == (1, True, True, True)


@pytest.mark.postgres
def test_live_postgres_readiness_applies_statement_timeout(
    postgres_app: Flask,
) -> None:
    captured_parameters: list[object] = []

    def capture_readiness_statement(
        _connection: Any,
        _cursor: Any,
        statement: str,
        parameters: object,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if "set_config" in statement and "statement_timeout" in statement:
            captured_parameters.append(parameters)

    with postgres_app.app_context():
        approved = validate_postgres_test_environment()
        engine = db.engine
        with engine.connect() as connection:
            validate_connected_postgres_test_environment(connection, approved)
        event.listen(engine, "before_cursor_execute", capture_readiness_statement)
        try:
            check_readiness(postgres_app)
        finally:
            event.remove(
                engine,
                "before_cursor_execute",
                capture_readiness_statement,
            )

    assert any(
        isinstance(parameters, dict) and parameters.get("timeout") == "2000ms"
        for parameters in captured_parameters
    )
