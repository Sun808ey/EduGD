from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast

import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.types import Event

REDACTED = "<redacted>"
SENSITIVE_CONFIG_KEYS = (
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "DEVELOPMENT_DATABASE_URL",
    "POSTGRES_TEST_DATABASE_URL",
    "PRODUCTION_DATABASE_URL",
    "MIGRATION_DATABASE_URL",
    "SENTRY_DSN",
)
SENSITIVE_FIELD_PATTERN = re.compile(
    r"(?i)(authorization|cookie|credential|dsn|password|secret|token)"
)
CREDENTIAL_URL_PATTERN = re.compile(r"(?i)([a-z][a-z0-9+.-]*://)[^/@\s]+@")
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


class StructuredJsonFormatter(logging.Formatter):
    def __init__(
        self,
        environment: str,
        sensitive_values: Sequence[str],
    ) -> None:
        super().__init__()
        self.environment = environment
        self.sensitive_values = tuple(sensitive_values)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "environment": self.environment,
            "message": redact_text(record.getMessage(), self.sensitive_values),
        }
        event_name = getattr(record, "event", None)
        if isinstance(event_name, str):
            payload["event"] = redact_text(event_name, self.sensitive_values)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging(app: Flask) -> None:
    environment = _environment_label(app.config["APP_ENV"])
    formatter = StructuredJsonFormatter(
        environment,
        _sensitive_config_values(app.config),
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.disabled = False
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.propagate = False


def configure_sentry(app: Flask) -> None:
    environment = _environment_label(app.config["APP_ENV"])
    dsn = app.config.get("SENTRY_DSN")
    if not dsn or environment == "test":
        app.extensions["sentry"] = {
            "enabled": False,
            "environment": environment,
        }
        return

    sensitive_values = _sensitive_config_values(app.config)

    def before_send(
        event: Event,
        _hint: dict[str, Any],
    ) -> Event:
        event.pop("request", None)
        event.pop("breadcrumbs", None)
        return cast(Event, scrub_value(event, sensitive_values))

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[FlaskIntegration()],
        default_integrations=False,
        send_default_pii=False,
        max_request_body_size="never",
        sample_rate=app.config["SENTRY_ERROR_SAMPLE_RATE"],
        traces_sample_rate=app.config["SENTRY_TRACES_SAMPLE_RATE"],
        profiles_sample_rate=0.0,
        attach_stacktrace=False,
        before_send=before_send,
    )
    app.extensions["sentry"] = {
        "enabled": True,
        "environment": environment,
    }


def redact_text(value: str, sensitive_values: Sequence[str]) -> str:
    redacted = value
    for sensitive_value in sorted(sensitive_values, key=len, reverse=True):
        if sensitive_value:
            redacted = redacted.replace(sensitive_value, REDACTED)
    redacted = CREDENTIAL_URL_PATTERN.sub(r"\1<redacted>@", redacted)
    return BEARER_PATTERN.sub(f"Bearer {REDACTED}", redacted)


def scrub_value(value: Any, sensitive_values: Sequence[str]) -> Any:
    if isinstance(value, str):
        return redact_text(value, sensitive_values)
    if isinstance(value, Mapping):
        scrubbed: dict[str, Any] = {}
        for key, nested_value in value.items():
            key_text = str(key)
            if SENSITIVE_FIELD_PATTERN.search(key_text):
                scrubbed[key_text] = REDACTED
            else:
                scrubbed[key_text] = scrub_value(nested_value, sensitive_values)
        return scrubbed
    if isinstance(value, list):
        return [scrub_value(item, sensitive_values) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_value(item, sensitive_values) for item in value)
    return value


def _sensitive_config_values(configuration: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        value
        for key in SENSITIVE_CONFIG_KEYS
        if isinstance((value := configuration.get(key)), str) and value
    )


def _environment_label(app_environment: str) -> str:
    if app_environment in {"testing", "postgres-testing"}:
        return "test"
    return app_environment


__all__ = [
    "StructuredJsonFormatter",
    "configure_sentry",
    "configure_structured_logging",
    "redact_text",
    "scrub_value",
]
