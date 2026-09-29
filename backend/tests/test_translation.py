from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import TranslationCacheEntry
from app.routes import translation as translation_routes
from app.services import sunbird_translation
from app.services.sunbird_translation import (
    TranslationConfigurationError,
    TranslationProviderError,
    TranslationRateLimitError,
    TranslationResponseError,
    clear_translation_cache,
    translate_text,
)
from app.translation import SUPPORTED_TRANSLATION_LANGUAGES, normalize_language
from tests.test_administrator_authentication import (
    _authorization_header,
    _bootstrap,
    _login,
)


def test_supported_translation_languages_are_stable() -> None:
    assert set(SUPPORTED_TRANSLATION_LANGUAGES) == {
        "eng",
        "ach",
        "lgg",
        "teo",
        "nyn",
        "lug",
    }
    assert normalize_language(" Lug ") == "lug"
    assert normalize_language(None, required=False) is None


@pytest.mark.parametrize("value", ["", "fra", "English", 10])
def test_unknown_translation_language_is_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        normalize_language(value)


def test_translation_service_caches_successful_provider_result(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    calls = 0

    def fake_provider(text: str, source: str | None, target: str) -> str:
        nonlocal calls
        calls += 1
        assert text == "Hello"
        assert source == "eng"
        assert target == "lug"
        return "Oli otya?"

    monkeypatch.setattr(sunbird_translation, "_call_sunbird", fake_provider)
    with app.app_context():
        clear_translation_cache()
        first = translate_text(
            text="Hello", source_language="eng", target_language="lug"
        )
        second = translate_text(
            text="Hello", source_language="eng", target_language="lug"
        )

    assert first.translated_text == "Oli otya?"
    assert first.cached is False
    assert second.cached is True
    assert calls == 1
    with app.app_context():
        cached_row = db.session.execute(select(TranslationCacheEntry)).scalar_one()
        assert cached_row.source_hash == sunbird_translation._source_hash("Hello")
        assert cached_row.provider == "sunbird"
        assert cached_row.quality_status == "machine"


def test_translation_requires_provider_token(app: Any) -> None:
    app.config["SUNBIRD_API_TOKEN"] = None
    with app.app_context(), pytest.raises(TranslationConfigurationError):
        translate_text(text="Hello", source_language="eng", target_language="lug")


class _ProviderResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _ProviderResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.body


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b'{"status":"PENDING"}',
        b'{"status":"COMPLETED"}',
        b'{"status":"COMPLETED","output":{"translated_text":""}}',
    ],
)
def test_sunbird_rejects_malformed_or_incomplete_responses(
    app: Any, monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    monkeypatch.setattr(
        sunbird_translation, "urlopen", lambda *args, **kwargs: _ProviderResponse(body)
    )
    with app.app_context(), pytest.raises(TranslationResponseError):
        sunbird_translation._call_sunbird("Hello", "eng", "lug")


def test_sunbird_parses_completed_response_and_normalizes_text(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    response = _ProviderResponse(
        b'{"status":"COMPLETED","output":{"translated_text":"Oli otya?"}}'
    )
    monkeypatch.setattr(
        sunbird_translation, "urlopen", lambda *args, **kwargs: response
    )
    with app.app_context():
        assert sunbird_translation._call_sunbird("Hello", "eng", "lug") == "Oli otya?"


@pytest.mark.parametrize("error", [TimeoutError(), URLError("offline")])
def test_sunbird_network_failures_are_controlled(
    app: Any, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    monkeypatch.setattr(
        sunbird_translation,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(error),
    )
    with app.app_context(), pytest.raises(TranslationProviderError):
        sunbird_translation._call_sunbird("Hello", "eng", "lug")


def test_sunbird_rate_limit_is_distinguished(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    error = HTTPError(
        "https://api.sunbird.ai/tasks/translate", 429, "limited", {}, None
    )
    monkeypatch.setattr(
        sunbird_translation,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(error),
    )
    with app.app_context(), pytest.raises(TranslationRateLimitError):
        sunbird_translation._call_sunbird("Hello", "eng", "lug")


def test_sunbird_http_failure_is_controlled(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    error = HTTPError("https://api.sunbird.ai/tasks/translate", 500, "failed", {}, None)
    monkeypatch.setattr(
        sunbird_translation,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(error),
    )
    with app.app_context(), pytest.raises(TranslationProviderError):
        sunbird_translation._call_sunbird("Hello", "eng", "lug")


def test_provider_failure_is_not_cached(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    calls = 0

    def fail_provider(text: str, source: str | None, target: str) -> str:
        nonlocal calls
        calls += 1
        raise TranslationProviderError("provider unavailable")

    monkeypatch.setattr(sunbird_translation, "_call_sunbird", fail_provider)
    with app.app_context():
        clear_translation_cache()
        with pytest.raises(TranslationProviderError):
            translate_text(text="Hello", source_language="eng", target_language="ach")
        with pytest.raises(TranslationProviderError):
            translate_text(text="Hello", source_language="eng", target_language="ach")

    assert calls == 2


def test_translation_route_requires_administrator_authentication(client: Any) -> None:
    response = client.post(
        "/api/v1/admin/translation/translate",
        json={
            "source_language": "eng",
            "target_language": "lug",
            "text": "Hello",
            "content_class": "approved_dynamic",
        },
    )
    assert response.status_code == 401


def test_public_translation_accepts_only_landing_content_and_falls_back(
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    monkeypatch.setattr(
        sunbird_translation,
        "_call_sunbird",
        lambda text, source, target: (_ for _ in ()).throw(
            TranslationProviderError("down")
        ),
    )
    response = app.test_client().post(
        "/api/v1/public/translation/translate",
        json={"content_key": "hero.title", "target_language": "lug"},
    )
    assert response.status_code == 200
    assert response.get_json()["fallback"] is True
    assert (
        response.get_json()["translated_text"]
        == "Keep the school day in focus, even when the network cannot."
    )
    assert "provider-secret" not in response.get_data(as_text=True)

    rejected = app.test_client().post(
        "/api/v1/public/translation/translate",
        json={"content_key": "https://example.test", "target_language": "lug"},
    )
    assert rejected.status_code == 400


@pytest.mark.parametrize("target_language", ["eng", "ach", "lgg", "teo", "nyn", "lug"])
def test_public_translation_accepts_each_supported_language(
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
    target_language: str,
) -> None:
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    monkeypatch.setattr(
        sunbird_translation,
        "_call_sunbird",
        lambda text, source, target: f"translated-{target}",
    )
    with app.app_context():
        clear_translation_cache()
    response = app.test_client().post(
        "/api/v1/public/translation/translate",
        json={"content_key": "hero.title", "target_language": target_language},
    )
    assert response.status_code == 200
    body = response.get_json()
    if target_language == "eng":
        assert body["fallback"] is False
        assert body["translated_text"].startswith("Keep the school day")
    else:
        assert body["translated_text"] == f"translated-{target_language}"


def test_translation_route_returns_provider_result_without_secret(
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"

    monkeypatch.setattr(
        sunbird_translation,
        "_call_sunbird",
        lambda text, source, target: "Oli otya?",
    )
    response = app.test_client().post(
        "/api/v1/admin/translation/translate",
        headers=_authorization_header(token),
        json={
            "source_language": "eng",
            "target_language": "lug",
            "text": "Hello",
            "content_class": "approved_dynamic",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "translated_text": "Oli otya?",
        "source_language": "eng",
        "target_language": "lug",
        "cached": False,
        "content_class": "approved_dynamic",
        "quality_status": "machine",
    }
    assert "provider-secret" not in response.get_data(as_text=True)
    with app.app_context():
        db.session.rollback()


def test_translation_route_rejects_unapproved_content_class(app: Any) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    response = app.test_client().post(
        "/api/v1/admin/translation/translate",
        headers=_authorization_header(token),
        json={
            "source_language": "eng",
            "target_language": "lug",
            "text": "Emergency calls remain available.",
            "content_class": "policy_authoritative",
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"content_key": "hero.title"},
        {"content_key": "hero.title", "target_language": "fra"},
    ],
)
def test_public_translation_rejects_malformed_requests(
    app: Any, payload: object
) -> None:
    response = app.test_client().post(
        "/api/v1/public/translation/translate", json=payload
    )
    assert response.status_code == 400


def test_public_translation_maps_provider_validation_failure(
    app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        translation_routes,
        "translate_text",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    response = app.test_client().post(
        "/api/v1/public/translation/translate",
        json={"content_key": "hero.title", "target_language": "lug"},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "error, status",
    [
        (TranslationConfigurationError("missing"), 503),
        (TranslationRateLimitError("limited"), 429),
        (TranslationProviderError("offline"), 503),
    ],
)
def test_admin_translation_maps_provider_failures(
    app: Any,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
) -> None:
    _bootstrap(app)
    token = _login(app).get_json()["access_token"]
    monkeypatch.setattr(
        translation_routes,
        "translate_text",
        lambda **kwargs: (_ for _ in ()).throw(error),
    )
    response = app.test_client().post(
        "/api/v1/admin/translation/translate",
        headers=_authorization_header(token),
        json={
            "source_language": "eng",
            "target_language": "lug",
            "text": "Hello",
            "content_class": "approved_dynamic",
        },
    )
    assert response.status_code == status
