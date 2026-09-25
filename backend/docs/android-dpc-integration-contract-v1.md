# EduGD Android DPC Integration Contract v1

Status: server and administrator control-plane contract. This repository does not contain Android source code or a Device Owner runtime.

## Compatibility

The live-device contract supports exactly:

| Android | API |
| --- | ---: |
| 10 | 29 |
| 11 | 30 |
| 12 | 31 |
| 12L | 32 |
| 13 | 33 |
| 14 | 34 |
| 15 | 35 |

Android 16/API 36 is rejected for new registration, enrollment, activation, check-in metadata, and capability claims. Historical records and evidence remain readable and are not rewritten. Historical API 36 devices cannot remain active.

## Protocol Versions

The server uses explicit wire constants:

- `POLICY_PROTOCOL_VERSION = 3`
- `POLICY_SCHEMA_VERSION = 3`
- `AUDIT_PROTOCOL_VERSION = 3`
- `CONTROL_STATE_PROTOCOL_VERSION = 3`
- `DEVICE_AUTH_PROTOCOL_VERSION = 1`

## Signed Policy

Policy payloads are canonical UTF-8 JSON after NFC normalization, with sorted object keys and integer-only numeric values. The payload hash is SHA-256 over the canonical payload bytes. The signed envelope contains the protocol version, policy UUID, revision UUID, revision number, UTC `issued_at`, payload hash, signing key ID, payload, and base64url Ed25519 signature. The signature covers canonical JSON bytes of the envelope without the `signature` field.

The v3 payload requires:

```json
{
  "schema_version": 3,
  "timezone": "Africa/Kampala",
  "refresh_after_seconds": 3600,
  "default_mode": "school",
  "emergency_packages": ["org.edug.dpc"],
  "required_capabilities": ["screen_time", "web_filter"],
  "minimum_dpc_version": 1,
  "modes": [],
  "schedules": [],
  "screen_time": {
    "daily_limit_minutes": 120,
    "reset_minute": 0,
    "exhausted_mode_id": "restricted"
  },
  "web_filter": {
    "default_action": "block",
    "rules": [
      {
        "rule_id": "ncdc",
        "domain": "ncdc.go.ug",
        "include_subdomains": true,
        "action": "allow",
        "reason": "Approved curriculum resource"
      }
    ]
  },
  "network_controls": {
    "wifi_only": true,
    "disallow_mobile_network_configuration": true,
    "disallow_tethering": true,
    "disallow_user_vpn": true,
    "always_on_filtering_vpn": true,
    "vpn_lockdown_required": true
  },
  "telephony_controls": {
    "disallow_outgoing_calls": true,
    "disallow_sms": true,
    "preserve_emergency_calls": true
  }
}
```

Domains are strict IDNA-normalized ASCII names. Paths, queries, URLs, and browsing history are not policy fields.

## Application Semantics

Application identity is the canonical package name plus, when verified, the signing-certificate SHA-256 digest. Display names are not identity. The server catalogue stores application UUID, display name, package name, verified signing digest, category, education-approved flag, mandatory-block flag, status, and timestamps. The `games` restriction is a category, not a package identity.

The policy is allowlist-first. The effective allowed set preserves the EduGD DPC, System UI, independently certified emergency packages, required Android dependencies, and administrator-approved educational packages. Manageable non-essential third-party packages outside that effective set are suspended.

A blocked application means `SUSPENDED` and is enforced by Android `DevicePolicyManager.setPackagesSuspended`. Application hiding is not enforcement and `setApplicationHidden` is not required by this contract. Emergency and required system packages are preserved.

## Control Precedence

The effective control order is:

1. Device integrity failure.
2. Administrator Block override.
3. Screen-time exhausted mode.
4. Scheduled mode.
5. Default mode.

An administrator Block remains active until explicitly cleared by an authorized administrator.

## Network and Telephony

The policy/capability names are:

- `wifi_only`
- `disallow_mobile_network_configuration`
- `disallow_tethering`
- `disallow_user_vpn`
- `always_on_filtering_vpn`
- `vpn_lockdown_required`
- `DISALLOW_OUTGOING_CALLS`
- `DISALLOW_SMS`

These names are represented in the v3 `telephony_controls` object as
`disallow_outgoing_calls`, `disallow_sms`, and the mandatory
`preserve_emergency_calls` flag.

The generic DPC does not claim universal OEM cellular-modem shutdown. Production certification requires Wi-Fi-only hardware or a verified profile with no active SIM/eSIM/mobile-data path. Emergency calling remains available.

## Device Authentication

Protected device requests use `Authorization: DeviceCredential <credential_uuid>` and the explicit DEVICE-AUTH v1 format. The signed message is UTF-8 lines in this order:

```text
DEVICE-AUTH-V1
<METHOD>
<canonical-path>
<canonical-query>
<body-sha256-lowercase-hex>
<unix-timestamp>
<base64url-nonce>
<credential-uuid>
<device-uuid>
```

The server verifies timestamp skew, nonce uniqueness, body hash, canonical target, credential ownership, credential status, and signature before processing the request. New Android credentials use non-exportable ECDSA P-256 with SHA-256. RSA-2048/SHA-256 remains compatibility-only.

## Forensic Batches

An audit event contains sequential event number, event UUID, UTC timestamp, elapsedRealtime value, boot count, previous event hash, SHA-256 event hash, batch identity, device identity, credential identity, event code, outcome, and bounded metadata. A batch contains its identity, device and credential identities, ordered events, final chain hash, signature algorithm, and asymmetric batch signature. The server verifies the batch with the registered device public key and preserves append-only, idempotent ingestion. No backend-held Android HMAC secret is used.

Blocked-domain evidence contains only the privacy-preserving domain hash, rule ID, outcome, policy UUID, and revision UUID. Allowed browsing history is never stored.

## Android-Facing Endpoints

All protected endpoints use DEVICE-AUTH v1:

- `POST /api/v1/devices/register`
- `GET /api/v1/sync/policies/{device_uuid}`
- `POST /api/v1/devices/{device_uuid}/check-ins`
- `POST /api/v1/devices/{device_uuid}/policy-acknowledgements`
- `POST /api/v1/devices/{device_uuid}/audit-batches`
- `POST /api/v1/devices/{device_uuid}/usage-reports`
- `POST /api/v1/devices/{device_uuid}/web-filter-events`
- `POST /api/v1/devices/{device_uuid}/credentials/rotate`

## Golden Vectors

Existing and new deterministic vectors are kept under `backend/docs/` and `backend/tests/fixtures/`. The device-auth vector file is `backend/docs/device-auth-v1-test-vectors.json`; the policy v3 vector is `backend/tests/fixtures/policy_v3_golden_vector.json`. Vectors must be reproducible by an independent Kotlin implementation byte-for-byte.

## Administrator Portal

Authenticated administrators receive the complete permission set and can configure structured policy controls, application identities, revisions, lifecycle, Block overrides, enrollment operations, credential operations, and API-backed device evidence. The server remains authoritative for authorization.

## Explicit Release Blockers

This repository does not include the Android DPC, DevicePolicyManager runtime, offline/reboot enforcement, managed-device tests, API 29-35 handset evidence, OEM cellular validation, carrier testing, or physical emergency-call certification. These are required before declaring the Android integration gate PASS and are not represented as implemented here.
