from __future__ import annotations

import hashlib
import json
import threading
import unicodedata
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from flask import current_app
from sqlalchemy import select, text
from sqlalchemy.engine import Connection

from app.extensions import db
from app.models import TranslationCacheEntry
from app.translation import normalize_language, validate_translation_text


class TranslationError(RuntimeError):
    """Base error for the controlled translation boundary."""


class TranslationConfigurationError(TranslationError):
    pass


class TranslationProviderError(TranslationError):
    pass


class TranslationRateLimitError(TranslationProviderError):
    pass


class TranslationResponseError(TranslationProviderError):
    pass


@dataclass(frozen=True, slots=True)
class TranslationResult:
    translated_text: str
    source_language: str | None
    target_language: str
    cached: bool
    quality_status: str = "machine"


_CACHE_LOCK = threading.Lock()


def translate_text(
    *,
    text: object,
    source_language: object,
    target_language: object,
) -> TranslationResult:
    source = normalize_language(source_language, required=False)
    target = normalize_language(target_language)
    if not isinstance(target, str):
        raise ValueError("target_language is required")
    value = validate_translation_text(
        text,
        current_app.config["SUNBIRD_TRANSLATION_MAX_TEXT_LENGTH"],
    )
    if source == target:
        raise ValueError("source_language and target_language must differ")

    canonical_text = unicodedata.normalize("NFC", value)
    source_key = source or "auto"
    source_hash = _source_hash(canonical_text)
    lock_hash = hashlib.sha256(
        (source_key + "\n" + target + "\n" + source_hash).encode("utf-8")
    ).hexdigest()

    with _CACHE_LOCK:
        with db.engine.begin() as connection:
            _acquire_cache_lock(connection, lock_hash)
            cached = connection.execute(
                select(TranslationCacheEntry.__table__).where(
                    TranslationCacheEntry.__table__.c.source_language == source_key,
                    TranslationCacheEntry.__table__.c.target_language == target,
                    TranslationCacheEntry.__table__.c.source_hash == source_hash,
                )
            ).mappings().first()
            if cached is not None:
                return TranslationResult(
                    translated_text=cached["translated_text"],
                    source_language=source,
                    target_language=target,
                    cached=True,
                    quality_status=cached["quality_status"],
                )

            translated = _call_sunbird(canonical_text, source, target)
            connection.execute(
                TranslationCacheEntry.__table__.insert().values(
                    source_language=source_key,
                    target_language=target,
                    source_hash=source_hash,
                    source_text=canonical_text,
                    translated_text=translated,
                    provider="sunbird",
                    quality_status="machine",
                )
            )

    return TranslationResult(
        translated_text=translated,
        source_language=source,
        target_language=target,
        cached=False,
    )


def clear_translation_cache() -> None:
    with db.engine.begin() as connection:
        connection.execute(TranslationCacheEntry.__table__.delete())


def _acquire_cache_lock(connection: Connection, source_hash: str) -> None:
    if connection.dialect.name == "postgresql":
        lock_key = int.from_bytes(bytes.fromhex(source_hash[:16]), "big", signed=True)
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )


def _call_sunbird(text_value: str, source: str | None, target: str) -> str:
    base_url = current_app.config.get("SUNBIRD_API_BASE_URL")
    token = current_app.config.get("SUNBIRD_API_TOKEN")
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        raise TranslationConfigurationError("translation provider is not configured")
    if not isinstance(token, str) or not token.strip():
        raise TranslationConfigurationError("translation provider is not configured")

    payload: dict[str, str] = {"target_language": target, "text": text_value}
    if source is not None:
        payload["source_language"] = source
    request = Request(
        urljoin(base_url.rstrip("/") + "/", "tasks/translate"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(
            request,
            timeout=current_app.config["SUNBIRD_TRANSLATION_TIMEOUT_SECONDS"],
        ) as response:
            raw = response.read(64 * 1024 + 1)
    except HTTPError as error:
        if error.code == 429:
            raise TranslationRateLimitError("translation provider rate limited") from error
        raise TranslationProviderError("translation provider request failed") from error
    except (TimeoutError, URLError, OSError) as error:
        raise TranslationProviderError("translation provider unavailable") from error

    if len(raw) > 64 * 1024:
        raise TranslationResponseError("translation provider response is too large")
    try:
        body = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TranslationResponseError("translation provider response is invalid") from error
    if not isinstance(body, dict) or body.get("status") != "COMPLETED":
        raise TranslationResponseError("translation provider response is incomplete")
    output = body.get("output")
    translated = output.get("translated_text") if isinstance(output, dict) else None
    if (
        not isinstance(translated, str)
        or not translated.strip()
        or len(translated) > current_app.config["SUNBIRD_TRANSLATION_MAX_TEXT_LENGTH"]
        or not translated.isprintable()
    ):
        raise TranslationResponseError("translation provider returned empty output")
    return unicodedata.normalize("NFC", translated)


def _source_hash(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


__all__ = [
    "TranslationConfigurationError",
    "TranslationError",
    "TranslationProviderError",
    "TranslationRateLimitError",
    "TranslationResponseError",
    "TranslationResult",
    "clear_translation_cache",
    "translate_text",
]
