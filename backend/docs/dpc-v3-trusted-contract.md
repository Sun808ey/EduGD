# DPC v3 trusted contract

The sole v3 synchronization route is `GET /api/v1/sync/v3/devices/{device_uuid}/state`.
Every response is a canonical-JSON Ed25519 signed state containing protocol version,
server time, `signing_key_id`, operation (`apply`, `no_change`, `clear`, `rollback`,
or `blocked`), policy/revision identity, a signed policy envelope or null, and a
separately signed override state. `/sync/policies/{device_uuid}` is legacy-only and
MUST reject a v3 protocol request.

The backend owns a versioned signed capability catalogue. Each active entry has a
stable ID, DPC minimum version, API range 29--35, mapped v3 controls, evidence rule,
and status (`active`, `deprecated`, or `revoked`). The initial active IDs are
`app_suspension`, `lock_task`, `screen_time`, `web_filter`, `wifi_only`,
`mobile_network_restriction`, `tethering_restriction`, `user_vpn_restriction`,
`always_on_filtering_vpn`, `vpn_lockdown`, `outgoing_call_restriction`,
`sms_restriction`, `emergency_call_preservation`, `forensic_audit_chain`, and
`offline_policy_enforcement`.

A capability report is a DEVICE-AUTH-V1 authenticated canonical JSON object with
only device UUID, active credential UUID, DPC version, Android version/API, build
fingerprint, security patch, catalogue version, unique supported IDs, observed UTC
time, elapsed realtime, boot count, and report UUID. Unknown fields, unknown or
duplicate IDs, API outside 29--35, stale observations, or identity mismatch fail
closed.

A verifier-signed receipt is dual-operator approved and binds the device UUID,
credential public-key fingerprint, DPC package/digest, attestation result, build,
handler package/digests, mobile-network decision, emergency-call result, issue/expiry,
activation state, and reason code. Expiry, drift, incomplete evidence, or mismatch
quarantines the device. Receipt ingress requires HTTPS and Ed25519 verification
against the backend-pinned verifier key set; Flask does not trust forwarded client
certificate headers. Mutual TLS is a future external-infrastructure enhancement,
not an application-level fallback. Assignment and v3 signing require the current receipt and
latest compatible report; templates are resolved through certification first.
