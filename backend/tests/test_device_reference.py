import pytest

from app.device_reference import human_device_reference


@pytest.mark.parametrize(
    ("device_id", "asset_number", "expected"),
    [
        (1, None, "EduGuard-001"),
        (12, "NDEJJE-SS-PHONE-001", "NDEJJE-001"),
        (12, "school-asset-001", "SCHOOL-012"),
        (12, "asset#001", "EduGuard-012"),
    ],
)
def test_human_device_reference_formats_known_and_fallback_assets(
    device_id: int,
    asset_number: str | None,
    expected: str,
) -> None:
    assert human_device_reference(device_id, asset_number) == expected
