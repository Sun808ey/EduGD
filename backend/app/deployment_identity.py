"""Bind the deployed entry point to the reviewed environment resource map."""

from collections.abc import Mapping
from urllib.parse import urlsplit

from app.config import database_project_identity, validate_postgres_database_uri

RESOURCES = {
    "staging": (
        "dviuaqtlbuefmfmswwqt",
        "set-mayfly-105830.upstash.io",
        6379,
        "https://edug-admin-staging.vercel.app",
        "a8928189-e7bb-46be-8788-856816caecd0",
    ),
    "production": (
        "hszskxrgkptbytuquyfu",
        "edug-redis-production-edug-production.a.aivencloud.com",
        22050,
        "https://edug-admin.vercel.app",
        "48e80896-15ef-4616-837e-d59240fc503a",
    ),
}


def validate_deployment_identity(values: Mapping[str, str]) -> None:
    """Fail before opening connections; never render URLs or credentials."""
    environment = values.get("EDUG_ENVIRONMENT", "")
    if environment not in RESOURCES:
        raise RuntimeError("EDUG_ENVIRONMENT must identify staging or production")
    project, redis_host, redis_port, origin, railway_environment = RESOURCES[
        environment
    ]
    if values.get("APP_ENV") != "production":
        raise RuntimeError("Deployed environments must use production hardening")
    if values.get("RAILWAY_ENVIRONMENT_ID") != railway_environment:
        raise RuntimeError("Railway environment does not match EDUG_ENVIRONMENT")
    for name in ("DEVELOPMENT_DATABASE_URL", "POSTGRES_TEST_DATABASE_URL"):
        if values.get(name):
            raise RuntimeError(
                "Deployed services must not contain test/development URLs"
            )
    production_database = validate_postgres_database_uri(
        "PRODUCTION_DATABASE_URL", values.get("PRODUCTION_DATABASE_URL", "")
    )
    if database_project_identity(production_database) != project:
        raise RuntimeError("Database project does not match deployment assignment")
    migration_raw = values.get("MIGRATION_DATABASE_URL")
    if migration_raw:
        migration_database = validate_postgres_database_uri(
            "MIGRATION_DATABASE_URL", migration_raw
        )
        if (
            database_project_identity(migration_database) != project
            or migration_database.database != production_database.database
        ):
            raise RuntimeError("Migration database does not match runtime database")
    try:
        redis = urlsplit(values.get("REDIS_URL", ""))
        valid_redis = (
            redis.scheme == "rediss"
            and redis.hostname == redis_host
            and redis.port == redis_port
            and bool(redis.password)
            and redis.path in ("", "/", "/0")
            and not redis.query
            and not redis.fragment
        )
    except ValueError:
        valid_redis = False
    if not valid_redis:
        raise RuntimeError("Redis TLS endpoint does not match deployment assignment")
    if values.get("ADMIN_FRONTEND_ORIGINS", "").strip() != origin:
        raise RuntimeError("Frontend origin does not match deployment assignment")
