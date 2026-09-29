# Policy synchronization v1 contract

`GET /api/v1/sync/policies/<device_uuid>` supports a transitional legacy mode
and an explicit operation mode. All responses use `Cache-Control: no-store`.
Production deployments should require the device-credential request signature
described in `device-enrollment-authentication-design.md`.

## Explicit operation mode

Send `current_version` as ASCII decimal text in the range 0 through
2,147,483,647. A client that has policy identity state should also send both
`current_policy_uuid` and `current_revision_uuid` as canonical UUIDv4 text.
Sending only one identity field is invalid.

The response always contains `device_uuid`, `operation`,
`server_policy_version`, and `policy`:

- `apply`: persist and enforce the returned exact revision.
- `no_change`: the desired state already matches; retain the current state.
- `clear`: remove the locally enforced policy because the server desires no
  assignment.
- `rollback`: deliberately apply the returned older revision of the same
  policy.
- `blocked`: do not change policy state and stop normal synchronization until
  the server permits it.

An assigned policy document includes `policy_uuid`, `policy_revision_uuid`,
`policy_version`, and `blocked_apps`. The client must persist both UUIDs with
the applied version. A different policy identity is always `apply`, regardless
of numeric version. `rollback` is returned only when the client identifies the
same policy and reports a version above the server's assigned revision.

Without both identity fields, the server cannot prove that a higher client
version belongs to the same policy, so it returns `apply` rather than inferring
a rollback. This is the safe compatibility behavior for older version-aware
clients.

Errors use the same top-level fields with `policy: null` and a nested
`error` object containing stable `code` and human-readable `message` fields.
Unknown device responses are deliberately generic. Inactive devices and
unavailable assigned policies are classified separately internally and emit
safe `blocked` responses.

Device-signature rejection occurs before synchronization dispatch and retains
the established authentication protocol body, `{"error":"authentication_failed"}`.
This deliberate compatibility exception prevents a response-format change
from weakening or destabilizing the shared enrollment/authentication boundary.

## Legacy compatibility and deprecation

Omitting `current_version` preserves the original successful response shape so
deployed Android clients are not silently broken. Legacy responses include
`Deprecation`, `Sunset`, and `Link` headers. New clients must use explicit
operation mode. The planned legacy sunset is 31 December 2027; removing it
requires a separately reviewed API version or rollout decision.

## Audit and privacy

Every handled synchronization attempt appends a database audit event with an
event UUID, request time, reported identity/version, desired operation,
outcome, server version, authenticated credential when present, and a hash link
to the preceding event for the device pseudonym. The raw requested UUID is not
stored for unknown-device events. Policy and assignment state remain unchanged
during a pull; `last_sync_at` remains unused because audit events are the
authoritative source for derived last-sync information.
