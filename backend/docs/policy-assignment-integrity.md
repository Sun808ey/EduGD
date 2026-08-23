# Policy assignment integrity

Policy assignment replacement is performed only by
`replace_policy_assignment`. The service validates canonical UUIDv4 identities,
requires an active administrator with `policy.assign`, locks the target device,
and replaces the active assignment in one database transaction.

Every assignment references one exact immutable policy revision and records a
unique event UUID, the authorizing administrator, a bounded printable reason,
and its assignment time. Replacement never deletes or rewrites the prior event:
it marks that event `superseded` with a timestamp and inserts a new active event.
The partial unique index on `device_id` is the final database guarantee that a
device has at most one active assignment.

Submitting the already-active revision is idempotent. It returns the existing
event and does not alter its original actor, reason, or timestamps.

The migration converts legacy assignment rows to explicitly marked migration
events. Downgrade refuses once production assignment history or the new
permission is present because removing that evidence would be lossy.

PostgreSQL concurrency verification uses two independent sessions. Both writers
lock the same device row, so they serialize; the resulting history contains two
distinct events and exactly one active assignment.
