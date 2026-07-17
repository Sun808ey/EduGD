from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from test_support.postgres_safety import (
    ApprovedPostgresTestEnvironment,
    validate_connected_postgres_test_environment,
)


@contextmanager
def isolated_postgres_session(
    engine: Engine,
    approved: ApprovedPostgresTestEnvironment,
) -> Iterator[Session]:
    """Contain commits in a SAVEPOINT and always roll back the outer scope."""
    connection = engine.connect()
    outer_transaction = None
    session = None
    try:
        validate_connected_postgres_test_environment(
            connection,
            approved,
            require_destructive=True,
        )
        outer_transaction = connection.begin()
        connection.exec_driver_sql("SET TRANSACTION READ WRITE")
        session = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        session.begin_nested()
        yield session
    finally:
        if session is not None:
            session.close()
        if outer_transaction is not None and outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()
        if outer_transaction is None or outer_transaction.is_active:
            raise AssertionError("PostgreSQL outer test transaction was not cleaned up")
        if not connection.closed:
            raise AssertionError("PostgreSQL test connection was not closed")


__all__ = ["isolated_postgres_session"]
