# Immutable policy revision design

## Status and scope

This is the approved Remediation 14 design artifact. It defines the production
contract for Remediation 15, but does not change models, migrate a database, or
alter runtime behavior.

The design is deliberately limited to stable policy identity, immutable policy
content, exact revision references, existing-data conversion, synchronization
compatibility, and a non-destructive downgrade boundary. Transactional
assignment replacement and its actor, reason, and event metadata remain
Remediation 16. Synchronization state classification remains Remediation 17.

## Verified current-state risk

`Policy` currently combines stable identity and lifecycle with mutable
`version` and `blocked_apps` content. `DevicePolicyAssignment` references the
policy row and duplicates its numeric version, but does not reference an
immutable content row.

Consequently:

- changing `Policy.blocked_apps` can rewrite the content represented by an old
  assignment;
- a numeric assignment version cannot prove which payload was assigned;
- a version mismatch can identify corruption but cannot recover the missing
  historical payload; and
- the current database cannot forensically reconstruct content that was
  overwritten before immutable revisions existed.

No policy-management endpoint currently writes policy content. Remediation 15
can therefore introduce the revision service before exposing a management API.

## Security and forensic objectives

The implementation must:

- preserve one stable `Policy` identity and lifecycle row;
- append a new `PolicyRevision` for every content change;
- prevent revision update and deletion through both SQLAlchemy and PostgreSQL;
- bind each assignment to one exact revision using a foreign key;
- retain old revisions after supersession or policy lifecycle changes;
- produce a deterministic SHA-256 content hash;
- preserve the current synchronization response shape during this migration;
- reject ambiguous legacy assignment history instead of inventing content; and
- prevent downgrade when doing so would discard genuine revision history.

## Normalized data model

### `Policy`

`Policy` remains the stable identity and lifecycle aggregate:

- `id`: integer primary key;
- `policy_uuid`: unique UUID;
- `name`: bounded display name;
- `status`: `draft`, `active`, `inactive`, or `revoked`;
- `created_at`; and
- `updated_at`.

The mutable `version` and `blocked_apps` columns move off this table after
successful conversion. `Policy.status` controls whether any revision may be
disclosed; it does not alter or delete revision content.

### `PolicyRevision`

Each row is an immutable content snapshot:

- `id`: integer primary key;
- `revision_uuid`: unique server-generated UUID version 4;
- `policy_id`: non-null `RESTRICT` foreign key to `policies.id`;
- `version`: positive integer, unique within the policy;
- `payload`: non-null JSON object;
- `content_hash`: exactly 32 SHA-256 bytes;
- `created_at`: database-backed timestamp; and
- `created_by`: bounded verified administrator UUID text, or a reserved
  migration subject for converted legacy rows.

Required constraints and indexes:

- unique `revision_uuid`;
- unique `(policy_id, version)`;
- unique `(policy_id, content_hash)`;
- check `version >= 1`;
- check `length(content_hash) = 32`;
- PostgreSQL JSON validation for the exact payload schema; and
- index `(policy_id, created_at)` for forensic history.

The first payload schema is exactly:

```json
{
  "schema_version": 1,
  "blocked_apps": [
    "com.facebook.katana",
    "com.instagram.android"
  ]
}
```

No additional or missing keys are accepted. `blocked_apps` uses the package
grammar, duplicate rejection, and order preservation approved in Remediation
13. The payload schema version permits future reviewed evolution without
rewriting old rows.

### `DevicePolicyAssignment`

Remediation 15 replaces `policy_id` and duplicated `policy_version` with:

- `policy_revision_id`: non-null `RESTRICT` foreign key to
  `policy_revisions.id`.

The assignment obtains policy identity and version through its exact revision.
Existing assignment status and timestamps remain unchanged in Remediation 15.
Remediation 16 separately adds and enforces assigning administrator, reason,
event UUID, and transactional replacement behavior.

## Canonical content and hashing

The application constructs a fresh plain payload object and validates it before
hashing. Canonical bytes are UTF-8 JSON produced with:

```text
sort_keys=True
ensure_ascii=False
separators=(",", ":")
allow_nan=False
```

The SHA-256 digest of those bytes is stored as `content_hash`. Package order is
preserved because no sorting or case normalization was approved. Reusing
identical canonical content for the same policy is rejected by
`(policy_id, content_hash)`; an administrator may assign an existing older
revision when an intentional rollback is required.

The PostgreSQL constraint validates payload structure and package values.
Application tests verify that the stored hash matches canonical payload bytes.
The runtime database role must not receive revision `UPDATE`, `DELETE`, or
`TRUNCATE` privileges.

## Immutability enforcement

Immutability is defense in depth:

1. The revision model exposes no content-update service.
2. A SQLAlchemy `before_flush` guard rejects dirty or deleted
   `PolicyRevision` instances.
3. PostgreSQL triggers reject every direct `UPDATE` or `DELETE` on
   `policy_revisions`.
4. Foreign keys use `RESTRICT`, never cascading deletion.
5. Runtime database privileges permit required `SELECT` and `INSERT`, but not
   revision mutation.
6. Reviewed migrations execute as the schema owner and may explicitly replace
   guards only inside a migration transaction.

Bulk SQL statements must not bypass the database trigger. An attempted
mutation fails without changing the revision or its assignments.

## Revision creation service

Remediation 15 introduces an internal transaction service before any public
policy-management route:

1. validate the policy UUID, actor, and payload bounds;
2. lock the stable `Policy` row using `SELECT ... FOR UPDATE`;
3. validate and canonicalize the complete payload;
4. return an existing revision only if explicitly implementing an idempotent
   request with a separately approved idempotency key; otherwise reject a
   duplicate content hash;
5. allocate `max(version) + 1` while holding the policy lock;
6. create the immutable revision with its actor and content hash;
7. flush and commit once; and
8. roll back the entire transaction on any validation, uniqueness, or database
   failure.

The service never updates an existing revision. Concurrent requests serialize
on the policy row and cannot allocate the same version.

## Synchronization compatibility

The policy synchronization API retains its existing response shape during
Remediation 15:

```json
{
  "device_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "policy": {
    "policy_uuid": "8e65f112-f7c4-4776-b113-e0eef34ec881",
    "policy_version": 5,
    "blocked_apps": [
      "com.facebook.katana"
    ]
  }
}
```

The service joins:

```text
active assignment
  -> exact PolicyRevision
  -> stable Policy
```

It reads `policy_version` and `blocked_apps` only from the referenced revision.
It continues disclosing content only when the stable policy status is `active`.
It must not select the latest revision implicitly. Assignment corruption and
inactive/revoked classification are handled explicitly in Remediation 17.
`apply`, `clear`, and `rollback` response operations remain Remediations 21 and
22.

## Upgrade and existing-data conversion

The migration runs in a maintenance window with application writers stopped.
Production, development, and integration-test databases remain separately
approved and migrated.

### Preflight

Before destructive column changes, the migration must:

1. verify every legacy policy payload satisfies the Remediation 13 validator;
2. verify every policy version is positive;
3. verify every assignment references an existing policy;
4. verify every assignment `policy_version` equals its referenced policy's
   current `version`; and
5. abort before conversion if any assignment represents content that the
   legacy schema can no longer reconstruct.

The migration must never fabricate historical content for a mismatched legacy
assignment. Such rows require an evidence-backed manual decision before retry.

### Conversion

In one migration transaction:

1. create `policy_revisions` with its constraints, indexes, JSON validator, and
   immutability trigger;
2. create exactly one revision for each existing policy:
   - preserve the legacy numeric version;
   - convert `blocked_apps` into payload schema version 1;
   - compute the canonical SHA-256 content hash;
   - generate a UUID version 4 revision identifier; and
   - record `created_by` as
     `migration:f4a7c9e2b6d1-to-policy-revisions`;
3. add nullable `device_policy_assignments.policy_revision_id`;
4. map every assignment through `(policy_id, policy_version)`;
5. assert every assignment received exactly one revision ID;
6. make `policy_revision_id` non-null and add its `RESTRICT` foreign key;
7. drop legacy assignment `policy_id` and `policy_version`;
8. drop the old policy blocked-app constraint and validator function after
   revision validation is active; and
9. drop `policies.version` and `policies.blocked_apps`.

The migration must verify row counts before and after each conversion stage.
No policy or assignment row is deleted.

## Historical limitation

The migration preserves every historical payload that still exists. It cannot
recover policy contents overwritten before the revision table existed.
Preflight mismatch detection prevents the system from falsely claiming that a
current payload represents an older assignment.

This limitation must be recorded in migration output and deployment evidence;
it must not be hidden by assigning synthetic content.

## Non-destructive downgrade strategy

Downgrade is allowed only while every policy has exactly one converted revision
and no post-migration revision history exists.

The downgrade must first check:

- each policy has exactly one revision;
- every assignment references that sole revision;
- every revision payload and hash are valid; and
- no revision would be discarded without an equivalent legacy representation.

When those checks pass, downgrade:

1. restores `policies.version` and `policies.blocked_apps` from the sole
   revision;
2. restores assignment `policy_id` and `policy_version`;
3. verifies all restored foreign keys and row counts;
4. drops `policy_revision_id`;
5. drops the revision immutability trigger and revision table; and
6. restores the Remediation 13 policy JSON validator and constraint.

If any policy has multiple revisions, downgrade fails before changing schema.
Operators must not bypass this guard because doing so would destroy historical
evidence. A backup is not a substitute for a valid in-place downgrade.

## Failure and recovery behavior

- Migration preflight or conversion failure rolls back the complete migration.
- Revision creation failure rolls back the revision and version allocation.
- Assignment foreign-key failure leaves the prior assignment unchanged.
- No service falls back to mutable `Policy.blocked_apps`.
- Database unavailability fails closed and returns no policy content.
- Migration logs contain counts and fixed categories, never policy payloads,
  administrator tokens, or device credentials.

## Required Remediation 15 verification

### Model and unit tests

- metadata, UUID, JSON, hash, timestamp, uniqueness, and foreign-key contracts;
- canonical hash vectors;
- approved and invalid payloads;
- ORM update and delete rejection;
- duplicate version and content rejection;
- stable policy lifecycle behavior;
- exact revision synchronization; and
- transaction rollback.

### SQLite migration tests

- legacy rows convert without loss;
- assignments receive the exact revision;
- row counts and current synchronization output are preserved;
- safe downgrade works before a second revision exists; and
- downgrade refuses after a second revision exists.

### PostgreSQL tests

- complete upgrade, downgrade, and upgrade cycle on the approved test branch;
- schema/metadata consistency;
- direct `UPDATE` and `DELETE` rejection;
- JSON payload constraint behavior;
- UUID and SHA-256 length behavior;
- `RESTRICT` foreign keys;
- concurrent version allocation;
- exact historical reconstruction after newer revisions are created; and
- no migration or test data remains outside the isolated test scope.

## Acceptance gate for implementation

Remediation 15 may begin only after this design is explicitly accepted.
Implementation is accepted only when:

- current API behavior remains compatible;
- every assignment references one exact immutable revision;
- old and newly created revisions remain reconstructable;
- direct and ORM mutation attempts fail;
- the approved Neon migration cycle passes;
- full regression coverage remains above the configured threshold; and
- downgrade either preserves all history or fails before changing state.
