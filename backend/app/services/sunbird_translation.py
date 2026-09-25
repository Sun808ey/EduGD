from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from flask import current_app

from app.translation import (
    normalize_language,
    validate_translation_text,
)


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


_CACHE: dict[str, tuple[float, TranslationResult]] = {}
_CACHE_LOCK = threading.Lock()


def translate_text(
    *,
    text: object,
    source_language: object,
    target_language: object,
) -> TranslationResult:
    source = normalize_language(source_language, required=False)
    target = normalize_language(target_language)
    value = validate_translation_text(
        text,
        current_app.config["SUNBIRD_TRANSLATION_MAX_TEXT_LENGTH"],
    )
    if source == target:
        raise ValueError("source_language and target_language must differ")

    cache_key = _cache_key(value, source, target)
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached is not None and cached[0] > now:
            result = cached[1]
            return TranslationResult(
                result.translated_text,
                result.source_language,
                result.target_language,
                True,
            )
        if cached is not None:
            _CACHE.pop(cache_key, None)

    translated = _call_sunbird(value, source, target)
    result = TranslationResult(
        translated_text=translated,
        source_language=source,
        target_language=target,
        cached=False,
    )
    with _CACHE_LOCK:
        _CACHE[cache_key] = (
            now + current_app.config["SUNBIRD_TRANSLATION_CACHE_TTL_SECONDS"],
            result,
        )
    return result


def clear_translation_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def _call_sunbird(text: str, source: str | None, target: str) -> str:
    base_url = current_app.config.get("SUNBIRD_API_BASE_URL")
    token = current_app.config.get("SUNBIRD_API_TOKEN")
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        raise TranslationConfigurationError("translation provider is not configured")
    if not isinstance(token, str) or not token.strip():
        raise TranslationConfigurationError("translation provider is not configured")

    payload: dict[str, str] = {"target_language": target, "text": text}
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
    if not isinstance(translated, str) or not translated.strip() or not translated.isprintable():
        raise TranslationResponseError("translation provider returned empty output")
    return translated


def _cache_key(text: str, source: str | None, target: str) -> str:
    material = "sunbird-v1\n" + (source or "auto") + "\n" + target + "\n" + text
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


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
