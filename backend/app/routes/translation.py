from __future__ import annotations

from flask import Blueprint, Response, request

from app.admin_api import admin_error, admin_json
from app.administrator_authorization import administrator_required
from app.extensions import limiter
from app.services.sunbird_translation import (
    TranslationConfigurationError,
    TranslationProviderError,
    TranslationRateLimitError,
    TranslationResponseError,
    translate_text,
)
from app.translation import (
    LANDING_PAGE_CONTENT,
    TRANSLATION_CONTENT_CLASSES,
    normalize_language,
)

translation_bp = Blueprint("translation", __name__)


@translation_bp.post("/public/translation/translate")
@limiter.limit("60 per minute")
def translate_public_landing_content() -> Response:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {
        "content_key",
        "target_language",
    }:
        return admin_error(
            "invalid_translation_request", "invalid translation request", 400
        )
    key = payload.get("content_key")
    if not isinstance(key, str) or key not in LANDING_PAGE_CONTENT:
        return admin_error(
            "invalid_translation_content",
            "content is not approved for landing translation",
            400,
        )
    try:
        target = normalize_language(payload.get("target_language"))
    except (TypeError, ValueError):
        return admin_error(
            "invalid_translation_request", "invalid translation request", 400
        )
    source = LANDING_PAGE_CONTENT[key]
    try:
        if target == "eng":
            return admin_json(
                {
                    "content_key": key,
                    "translated_text": source,
                    "target_language": target,
                    "cached": False,
                    "fallback": False,
                    "quality_status": "canonical",
                }
            )
        result = translate_text(
            text=source, source_language="eng", target_language=target
        )
    except (TypeError, ValueError):
        return admin_error(
            "invalid_translation_request", "invalid translation request", 400
        )
    except (
        TranslationConfigurationError,
        TranslationRateLimitError,
        TranslationProviderError,
        TranslationResponseError,
    ):
        return admin_json(
            {
                "content_key": key,
                "translated_text": source,
                "target_language": target,
                "cached": False,
                "fallback": True,
                "quality_status": "canonical",
            }
        )
    return admin_json(
        {
            "content_key": key,
            "translated_text": result.translated_text,
            "target_language": target,
            "cached": result.cached,
            "fallback": False,
            "quality_status": result.quality_status,
        }
    )


@translation_bp.post("/admin/translation/translate")
@limiter.limit("30 per minute")
@administrator_required()
def translate_admin_content() -> Response:
    try:
        payload = request.get_json(silent=False)
        if not isinstance(payload, dict) or set(payload) != {
            "source_language",
            "target_language",
            "text",
            "content_class",
        }:
            raise ValueError("invalid translation request")
        if payload["content_class"] not in TRANSLATION_CONTENT_CLASSES:
            raise ValueError("content is not approved for dynamic translation")
        result = translate_text(
            text=payload["text"],
            source_language=payload["source_language"],
            target_language=payload["target_language"],
        )
    except (TypeError, ValueError):
        return admin_error(
            "invalid_translation_request", "invalid translation request", 400
        )
    except TranslationConfigurationError:
        return admin_error(
            "translation_unavailable", "translation is not configured", 503
        )
    except TranslationRateLimitError:
        return admin_error(
            "translation_rate_limited", "translation is temporarily rate limited", 429
        )
    except (TranslationProviderError, TranslationResponseError):
        return admin_error(
            "translation_unavailable", "translation is temporarily unavailable", 503
        )
    return admin_json(
        {
            "translated_text": result.translated_text,
            "source_language": result.source_language,
            "target_language": result.target_language,
            "cached": result.cached,
            "content_class": "approved_dynamic",
            "quality_status": result.quality_status,
        }
    )


__all__ = ["translation_bp"]
