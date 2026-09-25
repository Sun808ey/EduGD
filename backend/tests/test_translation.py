from __future__ import annotations

from typing import Any

import pytest

from app.extensions import db
from app.services import sunbird_translation
from app.services.sunbird_translation import (
    TranslationProviderError,
    clear_translation_cache,
    translate_text,
)
from app.translation import SUPPORTED_TRANSLATION_LANGUAGES, normalize_language
from tests.test_administrator_authentication import (
    PASSWORD,
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


def test_translation_service_caches_successful_provider_result(app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_translation_cache()
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
        first = translate_text(text="Hello", source_language="eng", target_language="lug")
        second = translate_text(text="Hello", source_language="eng", target_language="lug")

    assert first.translated_text == "Oli otya?"
    assert first.cached is False
    assert second.cached is True
    assert calls == 1


def test_provider_failure_is_not_cached(app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_translation_cache()
    app.config["SUNBIRD_API_TOKEN"] = "provider-secret"
    calls = 0

    def fail_provider(text: str, source: str | None, target: str) -> str:
        nonlocal calls
        calls += 1
        raise TranslationProviderError("provider unavailable")

    monkeypatch.setattr(sunbird_translation, "_call_sunbird", fail_provider)
    with app.app_context():
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
        lambda text, source, target: (_ for _ in ()).throw(TranslationProviderError("down")),
    )
    response = app.test_client().post(
        "/api/v1/public/translation/translate",
        json={"content_key": "hero.title", "target_language": "lug"},
    )
    assert response.status_code == 200
    assert response.get_json()["fallback"] is True
    assert response.get_json()["translated_text"] == "Keep the school day in focus, even when the network cannot."
    assert "provider-secret" not in response.get_data(as_text=True)

    rejected = app.test_client().post(
        "/api/v1/public/translation/translate",
        json={"content_key": "https://example.test", "target_language": "lug"},
    )
    assert rejected.status_code == 400


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
