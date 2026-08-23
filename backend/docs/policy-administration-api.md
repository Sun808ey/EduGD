# Policy administration API

Both endpoints require a current administrator JWT and the `policy.assign`
permission. Bodies must be JSON objects with exactly the documented keys;
reasons contain 1–512 printable characters. Responses are `no-store`.

- `POST /api/v1/admin/devices/{device_uuid}/policy-assignment` accepts
  `{"policy_revision_uuid":"<canonical UUIDv4>","reason":"..."}`.
- `POST /api/v1/admin/devices/{device_uuid}/policy-assignment/clear` accepts
  `{"reason":"..."}` and rejects an already-clear device with 409.

Assignment/replacement and clear operations lock the device, update the
materialized assignment state, append an immutable hash-linked administrative
event, and advance its chain head in one transaction. The actor comes from the
validated JWT session, never from request data.

Clearing is durable administrative intent, not an inference from a missing
row. An offline DPC later reports its installed policy identity to the existing
version-aware sync endpoint and receives `clear`; a device already clear
receives `no_change`. The legacy synchronization representation remains
unchanged and deprecated.

Legacy authentication consumers continue receiving `{"error":"..."}`.
These new policy endpoints use `{"error":{"code":"...","message":"..."}}`.
