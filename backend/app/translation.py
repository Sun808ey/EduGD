from __future__ import annotations

from typing import Final

SUPPORTED_TRANSLATION_LANGUAGES: Final[dict[str, str]] = {
    "eng": "English",
    "ach": "Acholi",
    "lgg": "Lugbara",
    "teo": "Ateso",
    "nyn": "Runyankole",
    "lug": "Luganda",
}

TRANSLATION_CONTENT_CLASSES: Final[frozenset[str]] = frozenset(
    {"approved_dynamic"}
)

LANDING_PAGE_CONTENT: Final[dict[str, str]] = {
    "hero.eyebrow": "Offline-first school device governance",
    "hero.title": "Keep the school day in focus, even when the network cannot.",
    "hero.body": "EduGD gives Ugandan secondary schools an accountable control surface for phone-use policies on school-owned Android devices.",
    "hero.capabilities": "Capabilities shown are based on the current repository and clearly marked where external Android verification remains required.",
    "hero.explore": "Explore the product",
    "hero.admin": "Open admin console",
    "capabilities.title": "Four connected capabilities for accountable device use.",
    "capabilities.body": "EduGD connects administrator policy decisions with device status, acknowledgements, and security-relevant evidence.",
    "how.eyebrow": "How it works",
    "how.title": "A policy lifecycle designed around real school conditions.",
    "context.eyebrow": "Built for the context",
    "context.title": "Connectivity is a condition to design for.",
    "context.body": "Schools need governance that remains understandable when bandwidth, power, and reconnection are uneven.",
    "status.eyebrow": "Transparent PoC status",
    "status.title": "A credible academic foundation, clearly scoped.",
    "status.body": "The repository contains the React admin portal and Flask contracts. Android DPC sources, device certification, rollout, and production readiness require separate verification.",
}


def normalize_language(value: object, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ValueError("language must be a supported ISO 639-3 code")
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_TRANSLATION_LANGUAGES:
        raise ValueError("language must be a supported ISO 639-3 code")
    return normalized


def validate_translation_text(value: object, maximum_length: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum_length
        or not value.isprintable()
    ):
        raise ValueError("text must be printable and within the supported length")
    return value


__all__ = [
    "SUPPORTED_TRANSLATION_LANGUAGES",
    "TRANSLATION_CONTENT_CLASSES",
    "normalize_language",
    "validate_translation_text",
]
