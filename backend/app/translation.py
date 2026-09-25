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

TRANSLATION_CONTENT_CLASSES: Final[frozenset[str]] = frozenset({"approved_dynamic"})

MARKETING_PAGE_CONTENT: Final[dict[str, str]] = {
    "header.choose_languages": "Choose Languages",
    "header.open_admin": "Open admin console",
    "capabilities.eyebrow": "A focused control surface",
    "how.create": "Create",
    "how.assign": "Assign",
    "how.enforce": "Enforce",
    "how.reconcile": "Reconcile",
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
    "common.scope_note_title": "Scope note",
    "common.scope_note_body": "This public explanation uses repository evidence and marks Android DPC behavior, device certification, and production operation as separate verification requirements.",
    "common.open_admin": "Open admin console",
    "common.capability": "capability",
    "common.explore_capability": "Explore capability",
    "product.eyebrow": "Product overview",
    "product.title": "A focused operating model for school-owned Android devices",
    "product.intro": "EduGD connects policy decisions, device status, and accountable evidence without pretending to be a full commercial MDM platform.",
    "product.administrators.title": "Administrators",
    "product.administrators.text": "Create and assign policies from the protected console.",
    "product.devices.title": "Devices",
    "product.devices.text": "Apply the operating model to school-owned Android hardware.",
    "product.evidence.title": "Evidence",
    "product.evidence.text": "Review status, acknowledgements, and security events.",
    "features.eyebrow": "Capabilities",
    "features.title": "Capabilities grounded in the current PoC",
    "features.intro": "Explore the small set of capabilities EduGD can explain clearly today.",
    "feature.offline-enforcement.title": "Offline-first enforcement",
    "feature.offline-enforcement.intro": "Design policy enforcement for school conditions where connectivity cannot be assumed.",
    "feature.offline-enforcement.bullet1": "Local device-side policy evaluation is part of the intended operating model.",
    "feature.offline-enforcement.bullet2": "Reconnection provides a path for status and policy state synchronization.",
    "feature.offline-enforcement.bullet3": "Android DPC rollout and certification remain external verification requirements.",
    "feature.offline-enforcement.status": "External verification required",
    "feature.policy-management.title": "Policy management",
    "feature.policy-management.intro": "Give authorised administrators a clear path from policy creation to assignment and review.",
    "feature.policy-management.bullet1": "Create and inspect phone-use policies.",
    "feature.policy-management.bullet2": "Assign policies to managed devices.",
    "feature.policy-management.bullet3": "Track acknowledgements and policy state through the administrator surface.",
    "feature.policy-management.status": "Implemented surface",
    "feature.device-management.title": "Device management",
    "feature.device-management.intro": "Maintain an accountable view of school-owned Android devices and their operational status.",
    "feature.device-management.bullet1": "Review device enrollment and status information.",
    "feature.device-management.bullet2": "Use check-ins to understand device connectivity.",
    "feature.device-management.bullet3": "Keep private device records behind the authenticated application.",
    "feature.device-management.status": "Implemented surface",
    "feature.audit-and-forensics.title": "Audit and forensics",
    "feature.audit-and-forensics.intro": "Make security-relevant events reviewable while keeping evidence boundaries explicit.",
    "feature.audit-and-forensics.bullet1": "Review security-event audit records.",
    "feature.audit-and-forensics.bullet2": "Support selected forensic verification where implemented.",
    "feature.audit-and-forensics.bullet3": "Avoid treating a PoC audit trail as a complete forensic platform.",
    "feature.audit-and-forensics.status": "Implemented surface",
    "feature.security.title": "Security by design",
    "feature.security.intro": "Build the public story around authorization, privacy, and accountable evidence.",
    "feature.security.bullet1": "Protected administrator routes and server-side authorization.",
    "feature.security.bullet2": "Secure identity and synchronization principles where implemented.",
    "feature.security.bullet3": "Privacy-limited evidence and fail-closed security controls.",
    "feature.security.status": "Implemented surface",
    "feature.detail.eyebrow": "Capability detail",
    "feature.detail.what_this_means": "What this means in EduGD",
    "how-page.eyebrow": "How it works",
    "how-page.title": "From policy decision to accountable check-in",
    "how-page.intro": "EduGD describes a four-stage lifecycle between the administrator, the API, and the managed Android device.",
    "how-page.card1": "Create a policy",
    "how-page.card2": "Assign to devices",
    "how-page.card3": "Enforce locally",
    "how-page.card4": "Synchronize on return",
    "how-page.card_body": "The public model separates administrative intent from device-side operation and reconnection.",
    "schools.eyebrow": "For schools",
    "schools.title": "Designed around the school day",
    "schools.intro": "EduGD gives different school stakeholders a shared vocabulary for device governance.",
    "schools.ict.title": "ICT administrators",
    "schools.ict.text": "Enroll devices, assign policies, review check-ins.",
    "schools.leadership.title": "School leadership",
    "schools.leadership.text": "Understand policy status and operational accountability.",
    "schools.teachers.title": "Teachers",
    "schools.teachers.text": "Work within a defined learning-device policy.",
    "schools.reviewers.title": "Security reviewers",
    "schools.reviewers.text": "Examine security-event records and evidence boundaries.",
    "security.eyebrow": "Security",
    "security.title": "Security that stays within the evidence",
    "security.intro": "EduGD's public security story is about boundaries: protected access, accountable records, and no unnecessary collection.",
    "security.access.title": "Protected access",
    "security.access.text": "Authentication and authorization keep administrative data behind the application.",
    "security.privacy.title": "Privacy-aware evidence",
    "security.privacy.text": "Public pages do not expose device, school, policy, or audit records.",
    "security.fail_closed.title": "Fail-closed principles",
    "security.fail_closed.text": "Security controls are designed to avoid silently granting access when conditions fail.",
    "architecture.eyebrow": "Architecture",
    "architecture.title": "A simple architecture with an explicit boundary",
    "architecture.intro": "The repository documents the web administrator surface and backend contracts; the Android DPC remains an external verification boundary.",
    "architecture.administrator": "Administrator",
    "architecture.react": "React + Vite",
    "architecture.flask": "Flask API",
    "architecture.database": "PostgreSQL / Redis",
    "architecture.android": "Android DPC",
    "architecture.body": "Repository-verified components and external verification requirements are intentionally shown separately.",
    "resources.eyebrow": "Resources",
    "resources.title": "Resources for understanding the PoC",
    "resources.intro": "Start with the EduGD operating model, then inspect the architecture and security boundaries.",
    "resources.how": "Follow the policy lifecycle.",
    "resources.how.title": "How it works",
    "resources.architecture": "See the system boundary.",
    "resources.architecture.title": "Architecture",
    "resources.security": "Review the trust model.",
    "resources.security.title": "Security",
    "resources.about": "Understand the scope.",
    "resources.about.title": "About the PoC",
    "resources.schools": "Explore stakeholder context.",
    "resources.schools.title": "For schools",
    "resources.contact": "Ask for a walkthrough.",
    "resources.contact.title": "Contact",
    "about.eyebrow": "About the PoC",
    "about.title": "An academic project with transparent scope",
    "about.intro": "EduGD is a final-year academic Proof-of-Concept for offline-first phone-use policy enforcement on school-owned Android devices in Ugandan secondary schools.",
    "about.body1": "The project explores how policy management, device status, offline operation, and security-event evidence can fit together in a local school context.",
    "about.body2": "It is not presented as a finished commercial MDM/UEM platform. Android DPC validation, production rollout, and hosted-environment readiness remain separate engineering and operational gates.",
    "contact.eyebrow": "Contact",
    "contact.title": "Start a conversation about EduGD",
    "contact.intro": "For a walkthrough or academic discussion, contact the project team without sending student, device, credential, or sensitive school data through this public page.",
    "contact.body": "A real submission endpoint is not part of the current frontend contract. Connect an approved mail or form service before adding collection behavior.",
    "contact.link": "Read the PoC scope",
}

LANDING_PAGE_CONTENT = MARKETING_PAGE_CONTENT


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
    "MARKETING_PAGE_CONTENT",
    "LANDING_PAGE_CONTENT",
    "TRANSLATION_CONTENT_CLASSES",
    "normalize_language",
    "validate_translation_text",
]
