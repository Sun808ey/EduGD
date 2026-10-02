# EduGD frontend/admin contract coverage

This registry is the source-of-truth checklist for the administrator dashboard.
It describes the current Flask contracts and their safe browser representation.
Device-authenticated routes remain DPC-originated; the browser may display
their persisted evidence but must not impersonate a device.

| Method and route | Auth / permission | Frontend surface | Classification | Verification |
| --- | --- | --- | --- | --- |
| `POST /api/v1/admin/auth/login` | Public; rate limited | Login form and auth service | COVERED | Live login and 429 test |
| `POST /api/v1/admin/auth/logout` | Administrator session | Auth context/logout | COVERED | Live logout/401 test |
| `GET /api/v1/admin/auth/me` | Administrator session | Auth context | COVERED | Live identity test |
| `POST /api/v1/admin/administrators` | `administrator.manage` | Administrators page | COVERED | Live creation/403 test |
| `GET /api/v1/admin/administrators` | `administrator.manage` | Administrators inventory | COVERED | Live inventory test |
| `GET /api/v1/admin/administrators/<uuid>` | `administrator.manage` | Typed detail service | COVERED | Route/schema tests |
| `PATCH /api/v1/admin/administrators/<uuid>/permissions` | `administrator.manage` plus operator password | Administrator permissions dialog | COVERED | Password/self-protection tests |
| `POST /api/v1/admin/administrators/<uuid>/sessions/revoke` | `administrator.manage` plus operator password | Session-revocation dialog | COVERED | Live desktop/mobile test |
| `POST /api/v1/admin/administrators/<uuid>/disable` | `administrator.manage` plus operator password | Account-disablement dialog | COVERED | Audit/self-protection tests |
| `POST /api/v1/admin/administrators/<uuid>/password/reset` | `administrator.manage` plus operator password | Password-reset dialog | COVERED | Audit/session-revocation tests |
| `GET /api/v1/admin/devices` | Administrator session | Devices page | COVERED | Live list/filter test |
| `GET /api/v1/admin/devices/<uuid>` | Administrator session | Device detail | COVERED | Live deep-link test |
| `GET /api/v1/admin/devices/<uuid>/policy-assignment` | Administrator session | Device detail | COVERED | Live assignment test |
| `POST /api/v1/admin/devices/<uuid>/policy-assignment` | `policy.assign` | Device/policy controls | COVERED | Live assignment test |
| `POST /api/v1/admin/devices/<uuid>/policy-assignment/clear` | `policy.assign` | Device/policy controls | COVERED | Live clearing test |
| `POST /api/v1/admin/devices/<uuid>/credentials/revoke` | `device_credential.revoke` | Device detail | COVERED | Live revocation test |
| `GET /api/v1/admin/enrollment-tokens` | Administrator session | Enrollment panel | COVERED | Live list/redaction test |
| `POST /api/v1/admin/enrollment-tokens` | `enrollment_token.issue` | Enrollment panel/QR dialog | COVERED | Live issue/QR test |
| `POST /api/v1/admin/enrollment-tokens/<uuid>/revoke` | `enrollment_token.revoke` | Enrollment panel | COVERED | Live revoke/replay test |
| `GET /api/v1/admin/policies` | Administrator session | Policies page | COVERED | Live list/filter test |
| `GET /api/v1/admin/policies/<uuid>` | Administrator session | Policy detail | COVERED | Live deep-link test |
| `GET /api/v1/admin/policies/<uuid>/revisions` | Administrator session | Policy detail | COVERED | Live revision test |
| `POST /api/v1/admin/policies` | `policy.manage` | Policy creation page | COVERED | Service/UI tests |
| `POST /api/v1/admin/policies/<uuid>/revisions` | `policy.manage` | Policy detail | COVERED | Live revision test |
| `POST /api/v1/admin/policies/<uuid>/lifecycle` | `policy.manage` | Policy detail | COVERED | Live lifecycle test |
| `GET /api/v1/admin/devices/<uuid>/block-overrides` | Administrator session | Device detail | COVERED | Live evidence test |
| `POST /api/v1/admin/devices/<uuid>/block-overrides` | `device.control` | Device detail | COVERED | Live Block test |
| `POST /api/v1/admin/devices/<uuid>/block-overrides/clear` | `device.control` | Device detail | COVERED | Live clear test |
| `GET /api/v1/admin/devices/<uuid>/control-evidence` | Administrator session | Device detail | COVERED | Live evidence test |
| `GET /api/v1/admin/dashboard/dpc-summary` | Administrator session | Dashboard control room | COVERED | Live metrics test |
| `GET /api/v1/admin/audit-events` | Administrator session | Audit logs/dashboard | COVERED | Live ordering/pagination test |
| `GET /api/v1/admin/applications` | Administrator session | Applications page | COVERED | Live list test |
| `POST /api/v1/admin/applications` | `policy.manage` | Applications page | COVERED | Service/UI contract tests |
| `PATCH /api/v1/admin/applications/<uuid>` | `policy.manage` | Applications page | COVERED | Live/service UI update path |
| `POST /api/v1/admin/translation/translate` | Administrator session | Translations page | COVERED | Service/UI contract tests |
| `GET /api/v1/health` | Public | Local dependency status | COVERED | Local health check |
| `GET /api/v1/ready` | Public | Local dependency status | COVERED | Local readiness check |
| `POST /api/v1/devices/register` | Device credential/provisioning | Read-only enrollment evidence | DEVICE_PROTOCOL_READ_ONLY | Signed disposable DPC test |
| `GET /api/v1/sync/policies/<uuid>` | Device credential | Read-only sync evidence | DEVICE_PROTOCOL_READ_ONLY | Signed sync/rollback test |
| `POST /api/v1/devices/<uuid>/check-ins` | Device credential | Read-only check-in evidence | DEVICE_PROTOCOL_READ_ONLY | Signed lifecycle test |
| `POST /api/v1/devices/<uuid>/policy-acknowledgements` | Device credential | Read-only acknowledgement evidence | DEVICE_PROTOCOL_READ_ONLY | Signed lifecycle test |
| `POST /api/v1/devices/<uuid>/audit-batches` | Device credential | Read-only audit-chain evidence | DEVICE_PROTOCOL_READ_ONLY | Signed replay test |
| `POST /api/v1/devices/<uuid>/usage-reports` | Device credential | Read-only usage evidence | DEVICE_PROTOCOL_READ_ONLY | Backend contract tests |
| `POST /api/v1/devices/<uuid>/web-filter-events` | Device credential | Read-only web-filter evidence | DEVICE_PROTOCOL_READ_ONLY | Backend contract tests |
| `GET /api/v1/sync/v3/devices/<uuid>/state` | Device credential | Read-only DPC state evidence | DEVICE_PROTOCOL_READ_ONLY | Signed Block/clear test |
| `POST /api/v1/devices/<uuid>/credentials/rotate` | Device credential | Read-only credential lifecycle | DEVICE_PROTOCOL_READ_ONLY | Signed rotation test |
| Dedicated quarantine/re-enrollment controls | No Flask admin contract | Evidence-only status when available | BACKEND_CONTRACT_MISSING | Separate backend remediation |

## Security invariants

- The browser calls Flask only; it never calls Supabase, Redis, or a device route
  with device credentials.
- Pairing tokens are transient UI state and are never placed in storage,
  analytics, logs, or persisted frontend state.
- Server-side permission checks remain authoritative.
- Missing backend contracts are not simulated in the frontend.
