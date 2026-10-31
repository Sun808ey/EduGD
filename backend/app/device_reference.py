"""Stable human-facing references for school-owned devices."""

from __future__ import annotations

import re


def human_device_reference(device_id: int, asset_number: str | None) -> str:
    """Return a short display reference without replacing the canonical UUID."""
    known = {
        "NDEJJE-SS-PHONE-001": "NDEJJE-001",
        "NDEJJE-SS-TABLET-001": "NDEJJE-002",
    }
    if asset_number in known:
        return known[asset_number]
    prefix = "EDUGD"
    if asset_number:
        candidate = asset_number.split("-", 1)[0].upper()
        if re.fullmatch(r"[A-Z0-9]{2,12}", candidate):
            prefix = candidate
    return f"{prefix}-{device_id:03d}"
