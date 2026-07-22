# Device enrollment authentication design

## Status and scope

This began as the approved Remediation 10 design artifact. Remediation 11 is now
approved and its server-side persistence, migration, token administration,
enrollment, signed synchronization, rotation, revocation, and automated tests
are implemented in this repository. The migration has not been applied to a
production database. Live PostgreSQL migration/concurrency verification and an
Android client implementation remain deployment proof gates, not silently
assumed completed work.

The design applies to the single-school proof-of-concept deployment. A future
multi-school deployment must add explicit tenant ownership to every token,
device, credential, policy, and audit query before sharing one backend.

## Security objectives

The enrollment protocol must:

- preserve the Android DPC-generated canonical UUID as external device identity;
- require school authorization before first registration or legacy enrollment;
- make pairing tokens short-lived, single-use, and useless after consumption;
- prove possession of a non-exportable device private key during enrollment;
- authenticate subsequent synchronization and forensic-log upload requests;
- support immediate server-side credential revocation;
- reject replayed or stale requests;
- never store raw pairing tokens or device private keys on the server;
- avoid placing credentials, pairing tokens, signatures, or request bodies in
  application logs, Sentry, or ordinary API error responses; and
- append immutable security events for issuance, consumption, authentication,
  rotation, revocation, and rejected attempts.

## Assets, actors, and trust boundaries

Protected assets are policy content, device identity, device credentials,
pairing-token verifiers, registration and synchronization events, forensic-log
uploads, and administrator actions.

Trusted actors and components are an authorized school administrator, the
provisioned Android Device Policy Controller, the Flask service, and the
approved PostgreSQL database. The Android private key is trusted only while it
remains non-exportable in Android Keystore.

Trust boundaries are:

1. administrator to token-issuance mechanism;
2. out-of-band delivery of a pairing token to the physical school device;
3. Android DPC to Flask over TLS;
4. Flask to PostgreSQL over validated TLS; and
5. Flask authorization decisions to append-only security events.

The design does not trust a submitted `device_uuid`, source IP address, Android
version string, credential identifier, timestamp, nonce, or public key until
the relevant validation and cryptographic checks succeed.

## Threat model

| Threat | Primary control | Residual consideration |
| --- | --- | --- |
| UUID pre-registration | One-time school token plus device-key proof | A stolen unused token can enroll one attacker-controlled device until it expires or is revoked. |
| Pairing-token database disclosure | Store a keyed HMAC verifier, never the token | The server-side pepper must remain outside the database and support versioned rotation. |
| Pairing-token guessing | 256 random bits, short expiry, attempt limit, IP rate limit | Source-IP limiting is imperfect behind shared school networks. |
| Concurrent token consumption | Row lock and atomic consume/device/credential transaction | PostgreSQL concurrency tests are mandatory. |
| Token replay | Single-use consumed state committed atomically | Failed transactions must leave the token unconsumed. |
| Credential theft from server | Store only device public keys | A compromised signing service or database write path can still substitute keys; changes require audit events. |
| Credential theft from device | Non-exportable Android Keystore key | Hardware backing is not guaranteed on every API 21–29 device; compromise of the DPC process remains residual risk. |
| Request replay | Signed timestamp, nonce, body hash, and unique nonce record | Clients need bounded clock correction using server time. |
| Request tampering | Signature covers method, path, query, body hash, identity, timestamp, and nonce | Canonicalization must have one test-vector specification shared with Android. |
| Credential enumeration | Uniform HTTP 401 response | Operational events may retain internal failure categories with restricted access. |
| Revoked device continuing offline | Server rejects future requests immediately | The device retains its last locally enforced policy while offline, as already approved. |
| Malicious downgrade report | Authenticated metadata update rejects lower API level and audits it | Administrator review workflow remains a later implementation concern. |
| Administrator misuse | Named actor, reason, expiry, and immutable issuance/revocation events | Administrator authentication and authorization require their own approved implementation. |
| Sensitive logging | Fixed event categories and existing redaction/Sentry controls | Tests must inspect structured log output for every authentication failure path. |

## Cryptographic choices

### Normative encoding and signature rules

The words **must**, **reject**, and **exactly** in this section are normative.
All signed messages use UTF-8, exactly one line-feed byte (`0x0a`) between
fields, and no final line-feed. Every field is already validated and
canonicalized before message construction; field values may not contain a
carriage return, line feed, or NUL byte.

- UUIDs use canonical lowercase hyphenated text.
- Decimal integers use ASCII digits with no sign or leading zeroes, except the
  value zero is encoded as `0`.
- SHA-256 digests use exactly 64 lowercase hexadecimal characters.
- Binary values use RFC 4648 base64url without padding. Decoders reject `=`,
  whitespace, non-url-safe alphabet characters, and non-canonical encodings.
- Nonces decode to exactly 16 bytes and pairing-token secrets decode to exactly
  32 bytes.
- `RSA_2048_SHA256` means an RSA public key with a 2048-bit modulus and public
  exponent 65537, encoded as one complete DER SubjectPublicKeyInfo value with
  no trailing bytes. Signatures use RSASSA-PKCS1-v1_5 with SHA-256 (Android
  `SHA256withRSA`) and decode to exactly 256 bytes. RSA-PSS is not accepted
  under this algorithm identifier.
- A parser rejects an input instead of repairing, trimming, case-folding, or
  accepting an alternate representation.

The machine-readable interoperability vectors in
[`device-auth-v1-test-vectors.json`](device-auth-v1-test-vectors.json) are part
of this specification. Android and Flask implementations must reproduce every
canonical message, digest, HMAC verifier, and RSA signature verification result
before either enrollment or signed-request enforcement can be enabled.

### Pairing token

- Generate 32 cryptographically random bytes.
- Encode the secret using unpadded base64url.
- Present it as `<token_uuid>.<secret>` so the UUID can select one verifier row
  without searching token hashes.
- Store
  `HMAC-SHA-256(pepper, ASCII(canonical_token_uuid) || 0x00 || raw_secret)` and
  a pepper-version identifier; never store the presented token. The separator
  and fixed-width decoded secret make the verifier input unambiguous.
- Keep the pepper in a production secret named `PAIRING_TOKEN_PEPPER`, distinct
  from Flask and JWT secrets. Production must fail closed if token issuance or
  consumption is enabled without it.

Because the secret has 256 bits of entropy, a keyed SHA-256 verifier resists
offline guessing without introducing a password-hashing dependency. Comparisons
must use constant-time verification.

Default token lifetime is ten minutes. A token is single-use, may be revoked
before consumption, and is locked after five failed verification attempts.
Token values are displayed exactly once at issuance and are never retrievable.

### Device credential

The DPC generates an RSA-2048 signing key in Android Keystore and requests
`SHA256withRSA`. RSA is selected for consistent API 21–29 support. The private
key is non-exportable when the device implementation supports it. Hardware
backing and key attestation may be recorded as optional evidence but cannot be
mandatory because they are not uniformly available across the supported range.

The server stores:

- a random credential UUID used only as a public lookup identifier;
- the device ID;
- algorithm identifier;
- DER-encoded public key;
- SHA-256 public-key fingerprint;
- status: `active`, `revoked`, or `superseded`;
- issuance, last-use, revocation, and supersession timestamps; and
- revocation reason and responsible administrator when applicable.

There must be at most one active credential per device. The server never
receives or stores the private key and never returns a reusable bearer secret.

## Pairing-token lifecycle

1. An authenticated and authorized administrator requests a token with a
   reason and ten-minute expiry.
2. For an existing legacy device, the token must be bound to that device ID and
   canonical UUID. A general token cannot claim an existing device record.
3. For a newly provisioned school device, the token may be unbound but remains
   valid for only one new device.
4. The server stores only its verifier and returns the plaintext once.
5. The administrator transfers the token out of band to the physical device.
6. Enrollment locks the token row with `SELECT ... FOR UPDATE`.
7. The server checks status, expiry, attempt count, optional device binding, and
   verifier in constant time.
8. Successful enrollment marks the token consumed in the same transaction that
   creates or binds the device credential and appends the enrollment event.
9. Expired, revoked, consumed, locked, or invalid tokens return the same generic
   enrollment failure response.
10. Plaintext token material is erased from DPC memory and UI state immediately
    after the enrollment attempt.

Token issuance cannot be exposed until administrator authentication and an
authorization role for enrollment administration are separately approved.

## Enrollment sequence

1. During first provisioning, the DPC creates and securely persists its
   canonical UUIDv4 if one does not already exist.
2. The DPC generates the RSA key pair in Android Keystore.
3. The DPC computes the SHA-256 fingerprint of the public key.
4. The DPC creates an enrollment nonce and signs the exact enrollment canonical
   message specified below.
5. The DPC submits the token, public key, metadata, nonce, and proof-of-possession
   signature over TLS.
6. The server validates request size and shape before decoding cryptographic
   fields, then validates UUID and Android compatibility.
7. The server verifies and locks the token, validates its device binding, parses
   the allowed public-key format, and verifies the proof-of-possession signature.
8. In one PostgreSQL transaction, the server creates or locates the permitted
   device, creates the active credential, consumes the token, and appends an
   immutable enrollment event.
9. The server returns the credential UUID, algorithm, device status, server
   time, and enrollment event UUID. It returns no private or reusable secret.
10. The DPC persists the credential UUID beside the non-exportable key alias and
    uses them for every later protected request.

If any database or cryptographic step fails, the transaction rolls back and the
token remains available unless the failure-attempt limit is atomically reached.

### Enrollment proof canonical message

The proof-of-possession input is exactly:

```text
DEVICE-ENROLL-V1
<device UUID lowercase>
<token UUID lowercase>
<credential algorithm identifier>
<SHA-256 of exact public-key SPKI DER, lowercase hex>
<Android version from the validated Android/API pair>
<API level decimal>
<nonce base64url>
```

`DEVICE-ENROLL-V1` is a fixed domain-separation label. The server splits the
presented pairing token at its single `.` character, strictly decodes its
secret, and requires its token UUID to equal the UUID in the message. It
strictly decodes and parses the supplied public key, recomputes the fingerprint
over the exact accepted DER bytes, validates the Android version/API pair, and
then reconstructs the message from those server-validated values. It never
verifies a client-supplied message blob or client-supplied fingerprint without
recomputation.

The enrollment nonce is unique per DPC attempt. Successful replay is prevented
by atomic single-use token consumption. Concurrent identical submissions are
serialized by the token-row lock: exactly one may commit, and all later
submissions receive the generic enrollment failure. A failed proof increments
the token attempt counter in its own bounded transaction; infrastructure or
server failures do not consume an attempt.

## Proposed enrollment contract

The existing route remains the enrollment entry point:

```http
POST /api/v1/devices/register
Content-Type: application/json
```

Proposed request, still subject to a 16 KiB endpoint limit:

```json
{
  "device_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "android_version": "10",
  "api_level": 29,
  "pairing_token": "token-uuid.base64url-secret",
  "credential": {
    "algorithm": "RSA_2048_SHA256",
    "public_key": "base64url-der-subject-public-key-info",
    "nonce": "base64url-random-128-bits",
    "proof": "base64url-signature"
  }
}
```

Proposed success response:

```json
{
  "device_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "credential_uuid": "663b7fc2-1027-4ad6-8321-128c34331bc1",
  "credential_algorithm": "RSA_2048_SHA256",
  "device_status": "active",
  "server_time": "2026-07-19T10:00:00Z",
  "enrollment_event_uuid": "bcc651b1-5271-4388-ae58-264f170b8057"
}
```

Response categories:

- `201` enrolled;
- `400` malformed or unsupported input;
- `401` generic `enrollment_failed` for every token or proof failure;
- `409` already enrolled or legacy binding conflict;
- `413` request exceeds 16 KiB; and
- `500` generic server failure after rollback.

Responses and logs must never echo the pairing token, public key, proof,
signature, or verifier.

## Authenticated-request protocol

Protected requests carry these headers:

```http
Authorization: DeviceCredential <credential_uuid>
X-Device-Timestamp: <UTC Unix seconds>
X-Device-Nonce: <base64url random 128 bits>
X-Device-Body-SHA256: <lowercase hex SHA-256>
X-Device-Signature: <base64url RSA SHA-256 signature>
```

The signature covers this UTF-8 canonical message, with exactly one line-feed
between fields and no final line-feed:

```text
DEVICE-AUTH-V1
<HTTP method uppercase>
<canonical path>
<canonical sorted query string>
<body SHA-256 lowercase hex>
<timestamp decimal>
<nonce base64url>
<credential UUID lowercase>
<device UUID lowercase>
```

`canonical path` and `canonical sorted query string` are derived from the raw
origin-form request target, before framework form-decoding, as follows:

The production WSGI/proxy chain must preserve the exact origin-form target in a
trusted server variable such as `RAW_URI` or `REQUEST_URI`. Signed routes fail
closed when that value is absent, altered, absolute-form, or inconsistent with
the matched route. Implementations must not reconstruct it from Flask
`request.path` or `request.args`, because those values may already have decoded
or normalized security-relevant bytes. This preservation requirement is an
enforcement-mode startup and deployment integration test.

1. Split the raw target at the first literal `?`; an absent query becomes the
   empty string. Fragments are invalid in an HTTP request target.
2. The path must start with `/`. Strictly percent-decode each `%HH` triplet to
   bytes; hex digits are case-insensitive on input. Reject malformed escapes,
   NUL, backslash, control bytes, invalid UTF-8, dot-segments (`.` or `..`),
   empty interior segments, and percent-encoded `/` or `\`. These rejections
   prevent proxy/router path normalization from changing the signed resource.
3. Re-encode the decoded UTF-8 path bytes using RFC 3986 unreserved characters
   (`A-Z a-z 0-9 - . _ ~`) unchanged, preserve literal path separators `/`, and
   encode every other byte as uppercase `%HH`.
4. Split a non-empty raw query only on literal `&`. Every component must contain
   at least one literal `=`; split at the first one to separate a non-empty name
   from its value. Values may be empty. Strictly percent-decode both sides. A
   literal `+` is a plus byte, never a space. Reject malformed escapes, NUL,
   control bytes, invalid UTF-8, blank names, duplicate decoded names, and any
   parameter not declared by the endpoint contract.
5. Re-encode each decoded name and value with the RFC 3986 rule above but
   without preserving `/`. Sort pairs lexicographically by encoded name and
   then encoded value using unsigned ASCII byte order. Join each pair with `=`
   and pairs with `&`. The empty query is the empty canonical field.

The body hash is SHA-256 over the exact HTTP entity bytes as received, before
JSON or form parsing. Requests without an entity use the SHA-256 of zero bytes.
The server compares the computed digest to the bounded header in constant time
before deserializing a protected body. The method is the uppercase method token;
only methods explicitly allowed by the matched route are accepted.

Authentication order is:

1. apply global and endpoint request-size limits;
2. parse bounded authentication headers;
3. load credential by credential UUID;
4. return generic 401 if it is absent, revoked, or superseded;
5. verify credential ownership of the route device UUID;
6. require timestamp within five minutes of server time;
7. verify signature and body hash;
8. insert a hash of the credential UUID and nonce into a table with a unique
   constraint and ten-minute expiry;
9. reject a unique collision as replay; and
10. evaluate device status and endpoint authorization.

Header bounds are: 36 ASCII characters for each UUID, 10 decimal characters
for timestamps through year 2286, 22 base64url characters for a 16-byte nonce,
64 lowercase hexadecimal characters for the body digest, and 342 base64url
characters for a 256-byte RSA signature. Multiple instances, folded values,
leading/trailing whitespace, and non-canonical representations are rejected.

Nonce insertion and the protected state change must share a transaction for
write requests. A failed request uses a new nonce when retried. The DPC uses the
HTTP `Date` header and returned `server_time` to maintain a bounded clock offset;
it never disables timestamp validation.

All authentication failures use the same response:

```json
{
  "error": "authentication_failed"
}
```

The response is HTTP 401 with `Cache-Control: no-store`. Internal append-only
events retain a bounded failure category without storing signatures or tokens.
Successful authentication records `authentication_succeeded`; failures record
`authentication_failed`. Rate limiting and event sampling must never suppress a
security transition event such as issuance, token consumption, rotation, or
revocation.

## Protected API contracts

Policy synchronization remains:

```http
GET /api/v1/sync/policies/<device_uuid>
```

It requires the signed headers above. The authenticated credential, not the
path UUID or source IP, becomes the approved 60-per-minute rate-limit key. The
credential must belong to the path device. Suspended and retired devices still
receive the approved HTTP 403 `operation: blocked` response after successful
authentication.

Future forensic-log upload requests use the same credential and signing
protocol, but each batch also receives a separate idempotency UUID and its own
approved payload-size limit. An authentication nonce is not an upload
idempotency key.

Proposed credential rotation route:

```http
POST /api/v1/devices/<device_uuid>/credentials/rotate
```

The request is signed by the current credential and includes a new public key
and proof of possession. Rotation atomically creates the replacement, marks the
old credential `superseded`, and appends an event. It never returns a private
key or bearer secret.

The new-key proof uses the same normative encoding and RSA rules and signs this
exact message:

```text
DEVICE-ROTATE-V1
<device UUID lowercase>
<current credential UUID lowercase>
<new credential algorithm identifier>
<SHA-256 of exact new public-key SPKI DER, lowercase hex>
<new-key nonce base64url>
```

`DEVICE-ROTATE-V1` is a distinct domain-separation label. The complete HTTP
request, including this proof, is independently signed by the current active
credential using `DEVICE-AUTH-V1`. Thus rotation requires simultaneous proof of
the current private key and the replacement private key.

Proposed administrator operations, blocked until administrator authentication
is approved:

```http
POST /api/v1/admin/enrollment-tokens
POST /api/v1/admin/enrollment-tokens/<token_uuid>/revoke
POST /api/v1/admin/devices/<device_uuid>/credentials/revoke
```

The proposed administrator identity, session, authorization, bootstrap,
recovery, and audit boundary is specified in the
[administrator authentication design](administrator-authentication-design.md).
That design must be accepted and implemented before either enrollment-token
route is exposed.

## Credential revocation and recovery

Revocation is immediate for server communication. A revoked credential cannot
synchronize, rotate itself, or upload logs. Revocation records the credential,
device, administrator, reason, timestamp, and immutable event UUID.

A device that is offline continues enforcing its last local policy. Revocation
does not remotely erase that policy. When it reconnects, authentication fails
before policy disclosure.

Loss of the private key requires administrator recovery. The administrator
revokes any prior credential and issues a new pairing token bound to the
existing device. Recovery uses the enrollment proof-of-possession flow and
creates a new credential; it never reactivates or reveals the old credential.

## Offline-first implications

- Enrollment and credential recovery require connectivity; policy enforcement
  after successful enrollment remains offline-first.
- The DPC keeps its UUID and key alias in app-private storage and the signing
  key in Android Keystore. Pairing tokens are never retained after enrollment.
- Network loss does not weaken authentication or cause fallback to UUID-only
  synchronization.
- Queued forensic batches are signed only when sent so each attempt has a fresh
  timestamp and nonce. Batch identity remains stable for idempotency.
- Clock correction may use the last authenticated server offset, but requests
  outside the five-minute window still fail closed.
- Credential expiry is not proposed for the MVP because forced periodic online
  renewal conflicts with intermittently connected schools. Revocation and
  authenticated rotation provide lifecycle control.

## Persistence proposal

### `EnrollmentToken`

- token UUID, verifier, pepper version;
- optional bound device ID;
- status: `active`, `consumed`, `revoked`, `expired`, or `locked`;
- expiry, failed-attempt count, consumed time and device;
- issuing administrator, reason, creation and revocation metadata.

### `DeviceCredential`

- credential UUID and device ID;
- algorithm, public-key DER, and fingerprint;
- status: `active`, `revoked`, or `superseded`;
- issued, last-used, revoked, and superseded timestamps;
- revocation reason and actor;
- partial unique index allowing one active credential per device.

### `DeviceRequestNonce`

- credential ID, nonce hash, observed time, and expiry;
- unique constraint on credential and nonce hash;
- bounded cleanup after the replay window.

### `DeviceEnrollmentEvent`

- event UUID, device ID, credential ID, and token UUID where applicable;
- category, success/failure class, timestamp, administrator where applicable;
- public-key fingerprint, never the key, token, signature, or verifier;
- append-only retention for forensic reconstruction.

The permitted event categories are `token_issued`, `token_revoked`,
`token_consumed`, `enrollment_succeeded`, `enrollment_failed`,
`authentication_succeeded`, `authentication_failed`, `credential_rotated`,
`credential_revoked`, `legacy_authentication_used`, and
`legacy_authentication_disabled`. Successful enrollment writes
`token_consumed` and `enrollment_succeeded` in the same transaction. The
application runtime database role receives `INSERT` and required `SELECT`, but
not `UPDATE`, `DELETE`, or `TRUNCATE`, on this table; schema-owner privileges are
reserved for reviewed migrations. Remediation 11 must align the model and
database category constraint with this list before any enrollment route is
enabled.

Foreign keys use `RESTRICT` for forensic records. Raw long-lived secrets are
not stored. Every status column receives explicit model validation and database
check constraints.

## Existing-device migration plan

Rollout uses one fail-closed server mode, persisted in deployment configuration
and reported internally by readiness without exposing it publicly:

- `legacy`: enrollment administration and authenticated-device routes are
  disabled; existing behavior is temporarily preserved while schema and DPC
  support are staged.
- `new_devices_required`: every device UUID absent at the mode transition must
  use pairing-token enrollment. UUID-only registration is disabled. Devices
  already present at the recorded transition are the only devices eligible for
  the bounded synchronization compatibility path.
- `all_required`: every protected device request requires a valid credential;
  no UUID-only fallback exists.

The ordered rollout is:

1. Deploy enrollment-token, credential, nonce, and enrollment-event tables in
   `legacy` mode without changing route enforcement. Treat credential absence
   as derived `legacy_pending`; do not rewrite existing device UUIDs.
2. Release and verify the Android DPC update that implements the normative
   Keystore and wire protocol and passes the shared test vectors.
3. Enable administrator token issuance only after its authentication,
   authorization, pepper, audit, and revocation controls pass verification.
4. Record the immutable set or cutoff timestamp identifying devices that
   existed before enforcement. Issue only device-bound migration tokens after
   physical-custody and inventory confirmation.
5. In one reviewed application deployment, switch to
   `new_devices_required`. From that transition onward, new registrations have
   no UUID-only path. A startup/readiness check must fail closed if this mode is
   selected without the required pepper, tables, migration head, and routes.
6. Permit the time-bounded UUID-only synchronization compatibility path solely
   for recorded pre-transition `legacy_pending` devices. It never permits
   registration, metadata changes, credential rotation, or log upload, and
   every use appends `legacy_authentication_used`.
7. Monitor enrollment coverage without logging credentials or request bodies.
   Mode changes and failed downgrade attempts append immutable events.
8. At the explicitly approved cutoff, atomically switch to `all_required`.
   Pending devices receive generic HTTP 401 and retain their last local policy.
9. Remove compatibility code only after cutoff regression verification; never
   delete legacy device or forensic history.

The cutoff date, compatibility-window acceptance, and administrator issuance
mechanism require explicit approval before implementation. Production,
development, and test migrations remain separately gated.

## Required implementation increments and tests

Remediation 11 was implemented in these reviewed sub-steps:

1. persistence models and constraints;
2. reviewed migration and existing-device classification;
3. administrator token issuance and revocation mechanism;
4. registration token consumption and proof of possession;
5. credential issuance and Android storage contract;
6. signed synchronization authentication and replay storage;
7. credential rotation, revocation, and recovery;
8. compatibility cutoff; and
9. PostgreSQL concurrency, migration, cryptographic test vectors, redaction,
   replay, expiry, revocation, and rollback tests.

The PostgreSQL cases are safety-gated and must run against an explicitly
approved disposable test branch before rollout.

Mandatory negative tests include stolen/expired/consumed/revoked tokens,
concurrent token use, altered public keys, invalid proofs, credential/device
mismatch, stale timestamps, reused nonces, altered paths/queries/bodies,
revoked credentials, clock skew, database rollback, and secret-free logs.
Both the Android and Flask suites must consume the shared vectors and add
negative cases for padded or non-canonical base64url, malformed percent escapes,
encoded separators, duplicate or unknown query parameters, literal `+`, invalid
UTF-8, dot-segments, alternate UUID forms, leading-zero timestamps, wrong RSA
padding, and a signature produced for the other protocol domain label.

## Explicitly rejected alternatives

- Device UUID as bearer credential: predictable disclosure boundary and no
  revocation or proof of possession.
- Long-lived plaintext device bearer token: replayable and creates a server
  secret-disclosure target.
- JWT as the device's permanent credential: bearer replay remains possible and
  revocation becomes stateful anyway.
- Pairing token reused for synchronization: violates single-use separation.
- Mandatory mTLS: certificate provisioning and proxy operations exceed this
  proof-of-concept and API 21–29 deployment scope.
- Silent fallback to unauthenticated synchronization: defeats the enrollment
  protocol and is prohibited after the approved migration cutoff.
