import base64
import json
from pathlib import Path
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from app.device_cryptography import (
    DeviceCryptographyError,
    canonicalize_request_target,
    decode_base64url,
    encode_base64url,
    enrollment_message,
    request_message,
    validate_public_key,
    verify_signature,
)

VECTOR_PATH = Path(__file__).parents[1] / "docs" / "device-auth-v1-test-vectors.json"


def _vectors() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(VECTOR_PATH.read_text(encoding="utf-8")),
    )


def test_production_verifier_accepts_shared_enrollment_vector() -> None:
    vectors = _vectors()
    enrollment = vectors["enrollment"]
    public_key = validate_public_key(vectors["public_key_spki_base64url"])
    message = enrollment_message(
        device_uuid=enrollment["device_uuid"],
        token_uuid=vectors["pairing"]["token_uuid"],
        algorithm=enrollment["credential_algorithm"],
        public_key_fingerprint=public_key.fingerprint,
        android_version=enrollment["android_version"],
        api_level=enrollment["api_level"],
        nonce=enrollment["nonce_base64url"],
    )

    verify_signature(public_key.key, enrollment["proof_base64url"], message)


def test_production_verifier_accepts_shared_request_vector() -> None:
    vectors = _vectors()
    request = vectors["request"]
    public_key = validate_public_key(vectors["public_key_spki_base64url"])
    message = request_message(
        method=request["method"],
        canonical_path=request["canonical_path"],
        canonical_query=request["canonical_query"],
        body_hash=request["body_sha256"],
        timestamp=request["timestamp"],
        nonce=request["nonce_base64url"],
        credential_uuid=request["credential_uuid"],
        device_uuid=request["device_uuid"],
    )

    assert message.decode() == request["canonical_message"]
    verify_signature(public_key.key, request["signature_base64url"], message)


def test_verifier_rejects_wrong_rsa_padding_and_protocol_domain() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    message = b"DEVICE-AUTH-V1\ntest"
    pss_signature = key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    with pytest.raises(DeviceCryptographyError):
        verify_signature(key.public_key(), encode_base64url(pss_signature), message)

    vectors = _vectors()
    public_key = validate_public_key(vectors["public_key_spki_base64url"])
    with pytest.raises(DeviceCryptographyError):
        verify_signature(
            public_key.key,
            vectors["enrollment"]["proof_base64url"],
            vectors["request"]["canonical_message"].encode(),
        )


@pytest.mark.parametrize(
    "value",
    ["AA==", "AA+_", " AA", "AA\n", "a"],
)
def test_base64url_decoder_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(DeviceCryptographyError):
        decode_base64url(value)


@pytest.mark.parametrize(
    "target",
    [
        "/api/%2Fadmin",
        "/api/%5cadmin",
        "/api/%ZZ",
        "/api/../admin",
        "/api//admin",
        "/api?x=1&x=2",
        "/api?missing_equals",
    ],
)
def test_request_target_rejects_ambiguous_encodings(target: str) -> None:
    with pytest.raises(DeviceCryptographyError):
        canonicalize_request_target(target)


def test_request_target_uses_rfc3986_plus_and_sorting() -> None:
    path, query = canonicalize_request_target(
        "/api/%7Edevice?b=%7e&a=hello%20world&plus=%2b"
    )

    assert path == "/api/~device"
    assert query == "a=hello%20world&b=~&plus=%2B"


def test_request_target_canonicalizes_literal_unicode_as_utf8() -> None:
    path, query = canonicalize_request_target("/api/café")

    assert path == "/api/caf%C3%A9"
    assert query == ""


def test_public_key_parser_rejects_wrong_rsa_size() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    der = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with pytest.raises(DeviceCryptographyError):
        validate_public_key(encode_base64url(der))


def test_decoder_rejects_padded_encoding_even_when_bytes_are_valid() -> None:
    canonical = encode_base64url(b"test")
    padded = base64.urlsafe_b64encode(b"test").decode("ascii")
    assert canonical != padded
    with pytest.raises(DeviceCryptographyError):
        decode_base64url(padded)


def test_decoder_enforces_decoded_length() -> None:
    with pytest.raises(DeviceCryptographyError):
        decode_base64url(encode_base64url(b"short"), decoded_length=16)


@pytest.mark.parametrize(
    "encoded_key",
    [
        encode_base64url(b"not-a-der-key"),
        encode_base64url(b"x" * 513),
        encode_base64url(
            ec.generate_private_key(ec.SECP256R1())
            .public_key()
            .public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        ),
    ],
)
def test_public_key_parser_rejects_invalid_unsupported_or_oversized_keys(
    encoded_key: str,
) -> None:
    with pytest.raises(DeviceCryptographyError):
        validate_public_key(encoded_key)


@pytest.mark.parametrize(
    "target",
    [
        "relative/path",
        "/path#fragment",
        "/path?a=1?b=2",
        "/path?bad=%ZZ",
        "/path?control=%00",
        "/path?invalid=%FF",
        "/path?=empty",
    ],
)
def test_request_target_rejects_invalid_syntax_and_octets(target: str) -> None:
    with pytest.raises(DeviceCryptographyError):
        canonicalize_request_target(target)


def test_request_message_rejects_noncanonical_body_digest() -> None:
    with pytest.raises(DeviceCryptographyError):
        request_message(
            method="GET",
            canonical_path="/api/v1/test",
            canonical_query="",
            body_hash="A" * 64,
            timestamp="1",
            nonce=encode_base64url(b"0" * 16),
            credential_uuid="00000000-0000-4000-8000-000000000001",
            device_uuid="00000000-0000-4000-8000-000000000002",
        )
