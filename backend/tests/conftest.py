from collections.abc import Iterator

import pytest
from flask import Flask
from flask_migrate import upgrade

from app import create_app
from app.extensions import db
from test_support.postgres_safety import (
    PostgresTestSafetyError,
    validate_postgres_test_environment,
)


POSTGRES_TEST_MARKERS = frozenset(
    {
        "postgres",
        "migration",
        "concurrency",
    }
)
SAFE_DEFAULT_MARK_EXPRESSION = (
    "not postgres and not migration and not concurrency"
)


def pytest_configure(config: pytest.Config) -> None:
    """Validate safety before collecting an explicit PostgreSQL category."""
    marker_expression = config.option.markexpr
    if (
        not marker_expression
        or marker_expression == SAFE_DEFAULT_MARK_EXPRESSION
    ):
        return

    requests_postgres_category = any(
        marker_name in marker_expression
        for marker_name in POSTGRES_TEST_MARKERS
    )
    if requests_postgres_category:
        try:
            validate_postgres_test_environment(
                require_migration="migration" in marker_expression,
            )
        except PostgresTestSafetyError as error:
            raise pytest.UsageError(str(error)) from None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Classify tests without a PostgreSQL category as isolated unit tests."""
    for item in items:
        has_postgres_category = any(
            item.get_closest_marker(marker_name) is not None
            for marker_name in POSTGRES_TEST_MARKERS
        )
        if not has_postgres_category:
            item.add_marker(pytest.mark.unit)


@pytest.fixture()
def app() -> Iterator[Flask]:
    application = create_app("testing")
    with application.app_context():
        upgrade()

    yield application

    with application.app_context():
        db.session.remove()
