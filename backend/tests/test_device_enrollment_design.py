import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote_from_bytes, unquote_to_bytes

VECTOR_PATH = Path(__file__).parents[1] / "docs" / "device-auth-v1-test-vectors.json"
SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _load_vectors() -> dict[str, Any]:
    with VECTOR_PATH.open(encoding="utf-8") as vector_file:
        return cast(dict[str, Any], json.load(vector_file))


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _verify_rsa_pkcs1_v1_5_sha256(
    message: str,
    signature_base64url: str,
    modulus_base64url: str,
    exponent_base64url: str,
) -> bool:
    modulus_bytes = _decode_base64url(modulus_base64url)
    signature = _decode_base64url(signature_base64url)
    modulus = int.from_bytes(modulus_bytes, "big")
    exponent = int.from_bytes(_decode_base64url(exponent_base64url), "big")
    encoded = pow(int.from_bytes(signature, "big"), exponent, modulus).to_bytes(
        len(modulus_bytes), "big"
    )
    digest_info = (
        SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(message.encode("utf-8")).digest()
    )
    padding_length = len(modulus_bytes) - len(digest_info) - 3
    expected = b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info
    return hmac.compare_digest(encoded, expected)


def _canonicalize_vector_component(value: str, *, preserve_slash: bool) -> str:
    safe = "/-._~" if preserve_slash else "-._~"
    return quote_from_bytes(unquote_to_bytes(value), safe=safe)


def test_pairing_verifier_vector_is_unambiguous() -> None:
    vectors = _load_vectors()
    pairing = vectors["pairing"]
    secret = _decode_base64url(pairing["secret_base64url"])
    verifier_input = pairing["token_uuid"].encode("ascii") + b"\x00" + secret
    verifier = hmac.new(
        bytes.fromhex(pairing["pepper_hex"]),
        verifier_input,
        hashlib.sha256,
    ).hexdigest()

    assert len(secret) == 32
    assert verifier == pairing["verifier_hex"]


def test_enrollment_canonical_message_and_signature_vector() -> None:
    vectors = _load_vectors()
    enrollment = vectors["enrollment"]
    public_key_der = _decode_base64url(vectors["public_key_spki_base64url"])
    expected_message = "\n".join(
        (
            "DEVICE-ENROLL-V1",
            enrollment["device_uuid"],
            vectors["pairing"]["token_uuid"],
            enrollment["credential_algorithm"],
            vectors["public_key_fingerprint_sha256"],
            enrollment["android_version"],
            str(enrollment["api_level"]),
            enrollment["nonce_base64url"],
        )
    )

    assert (
        hashlib.sha256(public_key_der).hexdigest()
        == vectors["public_key_fingerprint_sha256"]
    )
    assert len(_decode_base64url(enrollment["nonce_base64url"])) == 16
    assert expected_message == enrollment["canonical_message"]
    assert (
        hashlib.sha256(expected_message.encode()).hexdigest()
        == enrollment["canonical_message_sha256"]
    )
    assert _verify_rsa_pkcs1_v1_5_sha256(
        expected_message,
        enrollment["proof_base64url"],
        vectors["public_key_modulus_base64url"],
        vectors["public_key_exponent_base64url"],
    )
    assert not _verify_rsa_pkcs1_v1_5_sha256(
        expected_message.replace("DEVICE-ENROLL-V1", "DEVICE-AUTH-V1", 1),
        enrollment["proof_base64url"],
        vectors["public_key_modulus_base64url"],
        vectors["public_key_exponent_base64url"],
    )


def test_authenticated_request_canonical_message_and_signature_vector() -> None:
    vectors = _load_vectors()
    request = vectors["request"]
    expected_message = "\n".join(
        (
            "DEVICE-AUTH-V1",
            request["method"],
            request["canonical_path"],
            request["canonical_query"],
            request["body_sha256"],
            request["timestamp"],
            request["nonce_base64url"],
            request["credential_uuid"],
            request["device_uuid"],
        )
    )

    assert request["body_sha256"] == hashlib.sha256(b"").hexdigest()
    assert len(_decode_base64url(request["nonce_base64url"])) == 16
    assert expected_message == request["canonical_message"]
    assert (
        hashlib.sha256(expected_message.encode()).hexdigest()
        == request["canonical_message_sha256"]
    )
    assert _verify_rsa_pkcs1_v1_5_sha256(
        expected_message,
        request["signature_base64url"],
        vectors["public_key_modulus_base64url"],
        vectors["public_key_exponent_base64url"],
    )
    assert not _verify_rsa_pkcs1_v1_5_sha256(
        expected_message.replace("current_version=4", "current_version=5", 1),
        request["signature_base64url"],
        vectors["public_key_modulus_base64url"],
        vectors["public_key_exponent_base64url"],
    )


def test_path_and_query_canonicalization_vectors() -> None:
    vectors = _load_vectors()
    path = vectors["path_canonicalization"]
    query = vectors["query_canonicalization"]
    query_pairs = []
    for component in query["raw"].split("&"):
        name, value = component.split("=", 1)
        query_pairs.append(
            (
                _canonicalize_vector_component(name, preserve_slash=False),
                _canonicalize_vector_component(value, preserve_slash=False),
            )
        )
    canonical_query = "&".join(f"{name}={value}" for name, value in sorted(query_pairs))

    assert (
        _canonicalize_vector_component(path["raw"], preserve_slash=True)
        == path["canonical"]
    )
    assert canonical_query == query["canonical"]
