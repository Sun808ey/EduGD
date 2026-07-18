from uuid import UUID

ANDROID_VERSION_BY_API_LEVEL = {
    21: "5.0",
    22: "5.1",
    23: "6.0",
    24: "7.0",
    25: "7.1",
    26: "8.0",
    27: "8.1",
    28: "9",
    29: "10",
}


def parse_canonical_uuid4(value: object) -> UUID:
    if not isinstance(value, str) or not value:
        raise ValueError("UUID must be canonical version 4 text")

    try:
        parsed_uuid = UUID(value)
    except (AttributeError, ValueError) as error:
        raise ValueError("UUID must be canonical version 4 text") from error

    if value != str(parsed_uuid) or parsed_uuid.version != 4:
        raise ValueError("UUID must be canonical version 4 text")
    return parsed_uuid


def validate_android_compatibility(
    android_version: object,
    api_level: object,
) -> tuple[str, int]:
    if (
        not isinstance(android_version, str)
        or isinstance(api_level, bool)
        or not isinstance(api_level, int)
        or ANDROID_VERSION_BY_API_LEVEL.get(api_level) != android_version
    ):
        raise ValueError("unsupported Android version and API level")
    return android_version, api_level


__all__ = [
    "ANDROID_VERSION_BY_API_LEVEL",
    "parse_canonical_uuid4",
    "validate_android_compatibility",
]
