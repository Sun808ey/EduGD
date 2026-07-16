from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIRECTORY / ".env", override=False)


def _environment_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_uri(database_uri: str) -> str:
    if database_uri.startswith("postgres://"):
        return database_uri.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1,
        )
    return database_uri


class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI: str | None = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_ENV_VAR: str | None = "DATABASE_URL"


class DevelopmentConfig(Config):
    DEBUG = _environment_flag("FLASK_DEBUG")


class TestingConfig(Config):
    TESTING = True
    DATABASE_ENV_VAR = None
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"


class PostgresTestingConfig(Config):
    TESTING = True
    DATABASE_ENV_VAR = "POSTGRES_TEST_DATABASE_URL"


class ProductionConfig(Config):
    pass


CONFIGURATIONS: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "postgres-testing": PostgresTestingConfig,
    "production": ProductionConfig,
}


def get_configuration(
    config_name: str | None = None,
) -> tuple[str, type[Config]]:
    selected_name = (config_name or os.getenv("APP_ENV", "development")).lower()
    try:
        return selected_name, CONFIGURATIONS[selected_name]
    except KeyError as error:
        valid_names = ", ".join(sorted(CONFIGURATIONS))
        raise ValueError(
            f"Unknown application environment '{selected_name}'. "
            f"Expected one of: {valid_names}"
        ) from error


def resolve_database_uri(configuration: type[Config]) -> str | None:
    if configuration.DATABASE_ENV_VAR is None:
        return configuration.SQLALCHEMY_DATABASE_URI

    database_uri = os.getenv(configuration.DATABASE_ENV_VAR)
    if not database_uri:
        return None
    return _normalize_database_uri(database_uri)
