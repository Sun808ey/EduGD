# DPC policy protocol v2

This document freezes the backend policy contract that the Android DPC must implement. It is a wire specification, not a claim that the Android client is present in this repository.

## Compatibility boundary

- Protocol version: `2`.
- Policy schema version: `2`.
- Minimum Android version: Android 10 / API 29.
- DPC builds compile and target API 36.
- The DPC advertises capabilities during enrollment. The server must not assign a policy whose required capabilities are absent.
- This branch implements the policy serialization and signing contract only.
  Device capability resolution, independently verified emergency handlers,
  physical-device certification, authenticated v2 enrollment, signing-key
  management, and live signed-policy sync remain required before activation.
  Self-reported capabilities or package names do not establish device trust.
- Current enrollment and policy-sync endpoints retain their existing protocol.
  The v2 contract does not change the database's Android compatibility range or
  activate v2 policies through a protocol-v1 enrollment response.
- Existing protocol-v1 RSA credentials remain a migration compatibility path. New DPC credentials should use a hardware-backed P-256 key when enrollment adds algorithm negotiation.

## Policy behavior

A policy uses `Africa/Kampala` and contains one or more named modes. Every mode uses an application allowlist, must include every emergency package, and may contain an explicit blocked list, lock-task allowlist, Android user restrictions and boolean device controls. Allowed and blocked lists are disjoint. Lock-task packages are a subset of allowed packages.

Schedules use ISO weekday numbers 1 (Monday) through 7 (Sunday) and minutes since local midnight. A start greater than an end denotes an overnight window beginning on the listed day and ending on the next day, wrapping Sunday to Monday. Overlapping schedules are resolved by priority. Two overlapping schedules with the same priority are invalid, preventing device-specific tie breaking.

`refresh_after_seconds` marks a verified policy stale. It does not expire the policy. A device without connectivity continues enforcing the last verified and successfully activated policy, records a stale-policy event and retries with bounded backoff. Invalid signatures, verified rollback and local integrity failure are separate high-risk states.

## Canonical encoding and signature

The server validates and normalizes the policy before signing it:

1. Object keys are sorted lexicographically.
2. Strings and keys are normalized to Unicode NFC.
3. JSON is UTF-8 with no byte-order mark or insignificant whitespace.
4. Arrays retain semantic order except set-like lists, modes and schedules, which the validator sorts.
5. Floating-point numbers are forbidden.
6. `payload_hash` is lowercase SHA-256 hex over the canonical policy payload.
7. The signature is Ed25519 over the canonical unsigned envelope.
8. The signature is unpadded base64url.

The unsigned envelope contains exactly `protocol_version`, `policy_uuid`, `revision_uuid`, `revision_number`, `issued_at`, `payload_hash`, `signing_key_id`, and `payload`. `issued_at` is whole-second UTC in the exact form `YYYY-MM-DDTHH:MM:SSZ`.

The DPC verifies the key ID against its pinned/rotated public-key set, verifies the Ed25519 signature, recomputes the payload hash, validates the policy schema, checks capability and minimum-version requirements, persists it atomically, and only then activates it.

## Interoperability evidence

`tests/fixtures/policy_v2_golden_vector.json` contains the public key, normalized payload, unsigned envelope, canonical UTF-8 bytes encoded as base64url, payload hash and signature for a deterministic test key. The private test key is not stored. Python and Kotlin implementations must reproduce and verify this vector byte-for-byte.
