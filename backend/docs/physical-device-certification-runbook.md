# Physical-device certification runbook

This runbook certifies one exact factory/OEM build and carrier configuration.
It does not certify a model name, an emulator, a DPC self-report, or a package
name pattern. It is a prerequisite for policy activation and live enrollment.

## 1. Prepare the reference handset

Use a factory-reset, school-owned physical handset. Record manufacturer, model,
product, Android API level, complete build fingerprint, security-patch level,
carrier, and a SHA-256 digest for carrier configuration. API 29 through 35 are
the only supported live range. Devices on API 21 through 28 or API 36 remain
suspended.

Migration `c7e5a9d2f4b8` suspends every active device, including devices already
on API 29, so none bypasses the new certification gate. Downgrading the schema
does not reactivate those devices; reactivation requires a separately reviewed
operational decision after certification.

Capture the approved factory/OEM image baseline hash and obtain the operator's
authorization reference for the test. Store neither credentials nor private
keys in this repository.

## 2. Attest on the trusted server

The server issues a fresh, single-use challenge. The DPC generates a
StrongBox key when available, otherwise a TEE-backed key, and sends its
certificate chain and the result to the trusted verifier service. The verifier
must, independently of the device:

1. validate every certificate signature to a current Google hardware-attestation
   root and check each certificate against the revocation-status list;
2. verify the challenge, hardware security level, Verified Boot state, and
   locked bootloader from the attestation extension;
3. verify the DPC application ID and signing-certificate SHA-256 digest;
4. record a valid Play Integrity device-integrity verdict as corroborating
   evidence, never as the only acceptance test; and
5. sign a canonical verification receipt with the verifier key.

The backend contract accepts only this signed receipt. It does not parse raw
attestation certificates or trust a DPC `attested` flag; raw chain validation
belongs in the separately protected verifier service.

## 3. Independently inventory and test emergency calling

From an operator-controlled workstation, resolve `ACTION_DIAL`,
`ACTION_CALL_EMERGENCY`, the default dialer role, and emergency information.
For each record package, component, version, and signing-certificate SHA-256
digest. Compare the result to both the attested DPC inventory and the approved
factory/OEM image baseline.

Test emergency reachability before, during, and after lock-task enforcement.
Use only a carrier/OEM-approved test number or an exercise coordinated with the
relevant emergency authority. Do not place an unannounced call to a real
emergency number. If an approved end-to-end test is unavailable, record
`NOT_VERIFIED`; activation must remain blocked.

## 4. Dual approval and record storage

Two different authorized operators sign the canonical record. It contains the
full identity, baseline, workstation inventory, verifier receipt, test
procedure and outcomes, timestamps, and the previous append-only record hash.
The server verifies both signatures and writes the record to
`device_capability_certifications`. Updates and deletes are rejected. A new
record is required if any build fingerprint, security patch, handler package,
handler signing digest, or carrier configuration digest changes.

## 5. Enrollment gate

The server sends a new challenge and requires a fresh verifier receipt at
enrollment. Its identity, DPC signing identity, and complete handler inventory
must equal the approved profile. A mismatch is quarantined; it cannot produce
an active device or receive a policy. Until the dedicated verifier service and
authenticated v2 enrollment exchange are connected, production enrollment is
intentionally blocked by `PHYSICAL_CERTIFICATION_REQUIRED`.

The automated contract is in `app/physical_certification.py`. It proves
canonical serialization, signed verifier receipts, dual authorization,
append-only storage, freshness, API range, carrier/build drift, handler drift,
and `NOT_VERIFIED` rejection. It does not substitute for hardware attestation,
OEM signature verification, carrier testing, or an authorized emergency-call
exercise.
