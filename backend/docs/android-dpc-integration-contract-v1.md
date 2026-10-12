# EduGD Android DPC Integration Contract v1

Status: server and administrator control-plane contract. This repository contains the Android DPC source; physical Device Owner runtime certification remains a separate verification gate.

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
  "required_capabilities": ["screen_time", "web_filter", "application_restrictions", "device_restrictions", "screen_lock", "network_settings"],
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
  },
  "device_use": {
    "mode": "dedicated_learning",
    "kiosk_mode_enabled": true,
    "display_school_name": true,
    "school_name": "Example Secondary School",
    "support_message": "Contact the ICT office"
  },
  "approved_applications": [
    {
      "application_uuid": "11111111-1111-4111-8111-111111111111",
      "display_name": "Learning app",
      "package_name": "org.example.learning",
      "application_type": "learning_application",
      "required": true,
      "allow_in_kiosk": true
    }
  ],
  "application_controls": {
    "allow_installation_of_other_applications": false,
    "allow_installation_from_unknown_sources": false,
    "allow_uninstall_of_approved_applications": false,
    "allow_disable_of_approved_applications": false,
    "allow_google_play_store": false,
    "allow_file_sharing_applications": false,
    "file_sharing_packages": ["org.example.fileshare"]
  },
  "device_restrictions": {
    "block_factory_reset": true,
    "block_safe_mode": true,
    "block_developer_options_and_debugging": true,
    "block_usb_file_transfer": true,
    "block_account_changes": true,
    "block_user_switching": true,
    "block_network_reset": false,
    "block_wifi_changes": false,
    "disable_screenshots": false,
    "disable_screen_recording": false,
    "disable_camera": false,
    "disable_microphone": false,
    "disable_location": false
  },
  "screen_lock": {
    "require_screen_lock": true,
    "automatic_lock_after_minutes": 5,
    "allow_biometric_unlock": false,
    "allow_learner_change_lock_method": false
  }
}
```

When present, `policy_code` is a unique administrator-facing identifier and
`description` is bounded policy context. The server validates both before
creating revision 1; revision numbers are generated monotonically by the
server. Kiosk mode requires an approved kiosk application, examination mode
requires camera, screenshot, and microphone restrictions, and the EDUGD DPC
package remains in the emergency package set.

The optional `device_use` object is the Iteration 1 school-facing control
surface. The server derives `school_name` from the registered school when
`display_school_name` is enabled; administrators cannot supply an arbitrary
organisation name. Legacy v3 payloads without this object remain valid.

The optional `approved_applications` array is resolved against the server's
managed-application catalogue before the policy is signed. The server rejects
unknown, disabled, unapproved, mandatory-blocked, duplicate, or non-canonical
application identities, and replaces submitted display/package metadata with
the catalogue values. At least one approved application is required when the
array is present. `required` applications cannot be removed from a revision
while that revision remains assigned to an active device. The Android DPC
enforces the resulting package allowlist and kiosk lock-task package list from
the signed `modes` object; the array is descriptive policy evidence and is not
an app store or an installation instruction.

The optional `application_controls` object is server-canonicalized. The
administrator submits only the six boolean choices; the server derives
`file_sharing_packages` from managed catalogue entries whose category is
`file_sharing`. The DPC maps the controls to device-owner restrictions,
per-approved-package uninstall blocks, Play Store suspension, and the
platform Bluetooth-sharing restriction plus suspension of catalogue-known
file-sharing packages. Legacy v3 payloads without this object
retain their existing behavior.

The optional `device_restrictions` object is a strict boolean contract for
core device-owner controls. The DPC maps factory reset, Safe Mode, debugging,
USB file transfer, account changes, user switching, network reset, and Wi-Fi
configuration to `UserManager` restrictions. Camera and screen capture use
`DevicePolicyManager`; screenshot and screen-recording choices converge on
Android's single screen-capture control. Microphone and location controls use
device-owner restrictions, with the DPC also disabling global location where
the Android API supports it. Wi-Fi changes remain allowed by the recommended
defaults so an offline device can reconnect and synchronise. Legacy v3
payloads without this object retain their existing behavior.

The optional `screen_lock` object uses a small allowlisted timeout set. The
DPC applies the timeout with `DevicePolicyManager.setMaximumTimeToLock`, uses
basic `PASSWORD_QUALITY_SOMETHING` only when a screen lock is required,
disables keyguard biometrics when not allowed, and uses
`UserManager.DISALLOW_CONFIG_CREDENTIALS` when learners may not change the
lock method. It does not create, read, or store a learner credential.

The optional `network_settings` object is the administrator-facing network
surface:

```json
{
  "allow_wifi": true,
  "allow_mobile_data": true,
  "allow_bluetooth": false,
  "allow_hotspot_creation": false,
  "allow_vpn_changes": false,
  "allow_network_reset": false
}
```

The DPC maps Bluetooth, hotspot, VPN, and network-reset choices to device-owner
user restrictions and verifies their read-back. Wi-Fi may be disabled only on
Android 13/API 33 or newer; the DPC preserves the prior Wi-Fi state for clear
and rollback. Mobile data remains required to be allowed because the standard
device-owner contract does not provide a portable mobile-data switch; carrier
or OEM privileges are outside this MVP. New policies can synchronize over an
allowed connected network, including cellular or metered Wi-Fi. Legacy payloads
without `network_settings` retain the existing unmetered Wi-Fi sync behavior.

The optional `compliance_settings` object selects the evidence checks shown to
administrators and sets the connection-review threshold:

```json
{
  "device_enrolled": true,
  "dpc_active": true,
  "policy_version_current": true,
  "approved_learning_application_installed": true,
  "kiosk_mode_active": true,
  "unknown_sources_blocked": true,
  "factory_reset_restriction_active": true,
  "required_restrictions_applied": true,
  "connection_review_after_days": 3
}
```

The threshold creates a connection-review indicator when a device has not
synchronised within the selected number of days. It does not change the
enforcement result and does not expire or weaken the last valid device policy.
The DPC's aggregate enforcement health and policy identity remain the signed
device evidence used for the selected checks; no learner content is collected.

The optional `offline_settings` object is fail-safe and fixed for the MVP:
the DPC enforces the last valid local policy, retains its local signed copy,
queues events while disconnected, and applies server changes after
reconnection. `expire_policy_when_offline` must be `false`; the server rejects
any revision that could leave a school device without effective controls merely
because it lost connectivity.

The optional `administrator_notes` field is bounded staff-only context. It is
included in the canonical payload hash and signed envelope for traceability,
but it is not an Android device control and the DPC must not display it to
learners. A school may author a separate, short acceptable-use notice when
learner-facing guidance is required.

The optional `data_collection_settings` object is fixed to management-only
evidence: asset number, policy version, last synchronisation time, compliance
result, and administrative actions. Learner location, private messages,
photographs, microphone recordings, contacts, personal files, and browsing
history are not accepted policy capabilities. The DPC may retain the signed
payload for verification, but must not turn this metadata section into a
surveillance or learner-facing collection path.

Time-window scheduling is intentionally outside the v3 MVP. The `schedules`
field remains required for canonical compatibility, but must be an empty list;
non-empty schedules are rejected before signing. The administrator form does
not expose allowed start/end times, weekday schedules, or outside-hours
locking. The DPC therefore has no clock-based time-window enforcement path,
avoiding restrictions that could become unreliable when a device is offline or
its clock changes.

Domains are strict IDNA-normalized ASCII names. Paths, queries, URLs, and browsing history are not policy fields.

## Application Semantics

Application identity is the canonical package name plus, when verified, the signing-certificate SHA-256 digest. Display names are not identity. The server catalogue stores application UUID, display name, package name, verified signing digest, category, education-approved flag, mandatory-block flag, status, and timestamps. The `games` restriction is a category, not a package identity.

The policy is allowlist-first. The effective allowed set preserves the EduGD DPC, System UI, independently certified emergency packages, required Android dependencies, and administrator-approved educational packages selected from the catalogue. Manageable non-essential third-party packages outside that effective set are suspended.

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
