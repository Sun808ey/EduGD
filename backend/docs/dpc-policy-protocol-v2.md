# DPC policy protocol v2

This document freezes the backend policy contract that the Android DPC must implement. It is a wire specification, not a claim that the Android client is present in this repository.

## Compatibility boundary

- Protocol version: `2`.
- Policy schema version: `2`.
- Minimum Android version: Android 10 / API 29.
- DPC builds compile and target API 36.
- The DPC advertises capabilities during enrollment. The server must not assign a policy whose required capabilities are absent.
- Android identifiers are configured in `app/android_integration_config.py`: DPC
  `io.github.sun808ey.edugd.dpc` and the initial Classroom, Moodle, Khan Academy,
  and Wikipedia allowlist. The AOSP/Google emulator candidate names are recognition
  hints only; a package name is never proof of its platform signature or role.
- Before activating any device policy, the DPC must report the handlers for
  `ACTION_DIAL`, `ACTION_CALL_EMERGENCY`, the default dialer role, and emergency
  information. A trusted operator/device verification must independently confirm
  each handler's actual signing identity and an emergency-call test. Persist that
  verification with the device-model profile; self-reported `system_signed` or
  `attested` flags must never constitute independent verification. The resolver
  rejects an incomplete or untested profile, duplicates, uninstalled/unknown apps,
  and attempted blocking of essential packages. It preserves the DPC, System UI,
  verified emergency handlers, and required system dependencies in allowed and
  lock-task package sets. `com.android.settings` is not an emergency package.
- `app/device_capability_profile.py` is the fail-closed resolution contract.
  Current protocol-v1 enrollment cannot securely bind a new capability report to
  its proof, and the current device table accepts Android API 21–29 while the new
  check-in contract targets API 29–36. Profile persistence, authenticated v2
  enrollment, signing-key management, and live signed-policy sync therefore remain
  required before production activation. Do not infer that a reported profile is
  verified or activate a v2 policy from the v1 enrollment response.
- The required physical-device procedure and its append-only dual-approval
  evidence are in `docs/physical-device-certification-runbook.md`.
- Existing protocol-v1 RSA credentials remain a migration compatibility path. New DPC credentials should use a hardware-backed P-256 key when enrollment adds algorithm negotiation.

## Policy behavior

A policy uses `Africa/Kampala` and contains one or more named modes. Every mode uses an application allowlist, must include every emergency package, and may contain an explicit blocked list, lock-task allowlist, Android user restrictions and boolean device controls. Allowed and blocked lists are disjoint. Lock-task packages are a subset of allowed packages.

Schedules use ISO weekday numbers 1 (Monday) through 7 (Sunday) and minutes since local midnight. A start greater than an end denotes an overnight window. Overlapping schedules are resolved by priority. Two overlapping schedules with the same priority are invalid, preventing device-specific tie breaking.

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
