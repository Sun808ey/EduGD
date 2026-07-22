from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from urllib.parse import quote_from_bytes

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

BASE64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PERCENT_ESCAPE_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")
ENCODED_SEPARATOR_PATTERN = re.compile(r"%(?:2[fF]|5[cC])")
UNRESERVED_SAFE = "-._~"


class DeviceCryptographyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedPublicKey:
    key: rsa.RSAPublicKey
    der: bytes
    fingerprint: bytes


def decode_base64url(value: object, *, decoded_length: int | None = None) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or BASE64URL_PATTERN.fullmatch(value) is None
    ):
        raise DeviceCryptographyError("invalid base64url value")
    try:
        decoded = base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))
    except (ValueError, TypeError) as error:
        raise DeviceCryptographyError("invalid base64url value") from error
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != value:
        raise DeviceCryptographyError("non-canonical base64url value")
    if decoded_length is not None and len(decoded) != decoded_length:
        raise DeviceCryptographyError("invalid decoded length")
    return decoded


def encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def validate_public_key(value: object) -> ValidatedPublicKey:
    der = decode_base64url(value)
    if len(der) > 512:
        raise DeviceCryptographyError("public key is too large")
    try:
        key = serialization.load_der_public_key(der)
    except (ValueError, TypeError) as error:
        raise DeviceCryptographyError("invalid public key") from error
    if not isinstance(key, rsa.RSAPublicKey):
        raise DeviceCryptographyError("unsupported public key type")
    numbers = key.public_numbers()
    if key.key_size != 2048 or numbers.e != 65537:
        raise DeviceCryptographyError("unsupported RSA parameters")
    canonical_der = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical_der != der:
        raise DeviceCryptographyError("non-canonical public key")
    return ValidatedPublicKey(key, der, hashlib.sha256(der).digest())


def enrollment_message(
    *,
    device_uuid: str,
    token_uuid: str,
    algorithm: str,
    public_key_fingerprint: bytes,
    android_version: str,
    api_level: int,
    nonce: str,
) -> bytes:
    return "\n".join(
        (
            "DEVICE-ENROLL-V1",
            device_uuid,
            token_uuid,
            algorithm,
            public_key_fingerprint.hex(),
            android_version,
            str(api_level),
            nonce,
        )
    ).encode("utf-8")


def rotation_message(
    *,
    device_uuid: str,
    current_credential_uuid: str,
    algorithm: str,
    public_key_fingerprint: bytes,
    nonce: str,
) -> bytes:
    return "\n".join(
        (
            "DEVICE-ROTATE-V1",
            device_uuid,
            current_credential_uuid,
            algorithm,
            public_key_fingerprint.hex(),
            nonce,
        )
    ).encode("utf-8")


def verify_signature(
    key: rsa.RSAPublicKey,
    signature_value: object,
    message: bytes,
) -> None:
    signature = decode_base64url(signature_value, decoded_length=256)
    try:
        key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature as error:
        raise DeviceCryptographyError("invalid signature") from error


def canonicalize_request_target(raw_target: str) -> tuple[str, str]:
    if not raw_target.startswith("/") or "#" in raw_target:
        raise DeviceCryptographyError("invalid request target")
    path, separator, query = raw_target.partition("?")
    if separator and "?" in query:
        raise DeviceCryptographyError("invalid request target")
    canonical_path = _canonicalize_path(path)
    canonical_query = _canonicalize_query(query)
    return canonical_path, canonical_query


def _strict_percent_decode(value: str) -> bytes:
    index = 0
    output = bytearray()
    while index < len(value):
        if value[index] == "%":
            match = PERCENT_ESCAPE_PATTERN.match(value, index)
            if match is None:
                raise DeviceCryptographyError("malformed percent escape")
            output.append(int(value[index + 1 : index + 3], 16))
            index += 3
        else:
            codepoint = ord(value[index])
            if codepoint > 127:
                output.extend(value[index].encode("utf-8"))
            else:
                output.append(codepoint)
            index += 1
    if any(byte == 0 or byte < 0x20 or byte == 0x7F for byte in output):
        raise DeviceCryptographyError("control byte in request target")
    try:
        bytes(output).decode("utf-8")
    except UnicodeDecodeError as error:
        raise DeviceCryptographyError("invalid UTF-8 in request target") from error
    return bytes(output)


def _canonicalize_path(path: str) -> str:
    if ENCODED_SEPARATOR_PATTERN.search(path) or "\\" in path:
        raise DeviceCryptographyError("encoded path separator")
    decoded = _strict_percent_decode(path)
    text = decoded.decode("utf-8")
    segments = text.split("/")
    if any(segment in {"", ".", ".."} for segment in segments[1:-1]):
        raise DeviceCryptographyError("ambiguous path segment")
    return quote_from_bytes(decoded, safe=f"/{UNRESERVED_SAFE}")


def _canonicalize_query(query: str) -> str:
    if not query:
        return ""
    pairs: list[tuple[str, str]] = []
    decoded_names: set[bytes] = set()
    for component in query.split("&"):
        if "=" not in component:
            raise DeviceCryptographyError("invalid query component")
        name, value = component.split("=", 1)
        decoded_name = _strict_percent_decode(name)
        decoded_value = _strict_percent_decode(value)
        if not decoded_name or decoded_name in decoded_names:
            raise DeviceCryptographyError("duplicate or empty query name")
        decoded_names.add(decoded_name)
        pairs.append(
            (
                quote_from_bytes(decoded_name, safe=UNRESERVED_SAFE),
                quote_from_bytes(decoded_value, safe=UNRESERVED_SAFE),
            )
        )
    return "&".join(f"{name}={value}" for name, value in sorted(pairs))


def request_message(
    *,
    method: str,
    canonical_path: str,
    canonical_query: str,
    body_hash: str,
    timestamp: str,
    nonce: str,
    credential_uuid: str,
    device_uuid: str,
) -> bytes:
    if HEX_DIGEST_PATTERN.fullmatch(body_hash) is None:
        raise DeviceCryptographyError("invalid body digest")
    return "\n".join(
        (
            "DEVICE-AUTH-V1",
            method,
            canonical_path,
            canonical_query,
            body_hash,
            timestamp,
            nonce,
            credential_uuid,
            device_uuid,
        )
    ).encode("utf-8")


__all__ = [
    "DeviceCryptographyError",
    "ValidatedPublicKey",
    "canonicalize_request_target",
    "decode_base64url",
    "encode_base64url",
    "enrollment_message",
    "request_message",
    "rotation_message",
    "validate_public_key",
    "verify_signature",
]
