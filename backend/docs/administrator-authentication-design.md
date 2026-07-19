# Administrator authentication and authorization design

## Status and scope

This design-only increment defines the administrator security boundary required
before device-enrollment token administration can be exposed. It does not add
routes, administrator records, passwords, sessions, migrations, pairing-token
issuance, or runtime authentication behavior. Implementation remains separately
approval-gated.

Implementation status: the four persistence models, migration
`f2a9d4c7e1b3`, and trusted-operator CLI bootstrap/recovery commands are now
implemented. Administrator login, logout, identity inspection, database-backed
session validation, login rate limiting, and reusable permission authorization
are also implemented. Enrollment-token administration remains absent, and no
administrator record was created by the implementation work.

The design is for the single-school proof-of-concept deployment. It must be
revisited before multiple schools share one backend because every administrator,
role, session, token, device, and audit query would then need a tenant boundary.

## Decision

Use locally managed, database-backed administrator accounts and short-lived JWT
access tokens. JWTs identify a session but do not become the authoritative
authorization record: every protected administrator request must load the
session and administrator from PostgreSQL and fail closed if either is absent,
expired, revoked, disabled, or unauthorized.

There is no public administrator registration route. The first administrator is
created through an interactive Flask CLI bootstrap command executed by a trusted
server operator. Password recovery and emergency session revocation also remain
CLI-only for the MVP. Passwords must never be accepted as command-line arguments.

## Security objectives

The administrator boundary must:

- authenticate a named human administrator before any privileged operation;
- authorize each operation using a database-authoritative permission;
- support immediate account disablement and session revocation;
- resist password guessing and username enumeration;
- keep passwords, JWTs, pairing tokens, verifiers, and request bodies out of
  logs, Sentry, audit-event details, and ordinary error responses;
- obtain the acting administrator identity only from the verified session,
  never from request JSON or an HTTP identity header;
- append immutable authentication and administration events suitable for
  forensic reconstruction; and
- preserve a recovery path that does not require email, SMS, or continuous
  Internet service.

## Trust boundaries and threats

Trusted components are the authorized school administrator, the TLS endpoint,
the Flask service, the approved PostgreSQL database, and the trusted operator
who controls the server CLI. Browser storage, submitted role claims, source IP
addresses, usernames, and all request bodies are untrusted.

| Threat | Required control | Residual consideration |
| --- | --- | --- |
| Password guessing | Per-source rate limit, per-account cooldown, strong password rules, generic failures | Shared school networks can make source limits imprecise. |
| Username enumeration | One generic login response and comparable password-verification work | Timing equivalence must be regression-tested. |
| JWT theft | TLS, 15-minute expiry, no persistent browser storage, server-side session check | A stolen token remains useful until revoked or expired. |
| JWT forgery or confusion | Fixed algorithm, issuer and audience checks, dedicated JWT secret | Key rotation requires an approved operational procedure. |
| Disabled administrator reuse | Load administrator and session on every request | Database availability is required for administration. |
| Role-claim escalation | Ignore JWT role claims for authorization; load permissions from PostgreSQL | A database compromise can still change authorization state. |
| CSRF | Bearer token in the `Authorization` header; no authentication cookies | The future frontend must not move the token into a cookie silently. |
| XSS token theft | Keep access token in memory and apply frontend CSP/escaping | Frontend hardening remains a separate concern. |
| Bootstrap misuse | Local interactive command, explicit actor/reason, one-time bootstrap guard | Host administrators remain highly trusted. |
| Audit deletion or rewriting | Append-only application behavior and restrictive foreign keys | Database superusers can alter records and remain a residual risk. |
| Pairing-token abuse | Separate enrollment permission, reason, short expiry, immutable event | A malicious authorized administrator can still misuse issued tokens. |

## Administrator identity and permissions

An administrator has a random UUID, canonical username, display name, password
verifier, status, and timestamps. Usernames are lowercase ASCII identifiers of
3 through 64 characters using letters, digits, period, underscore, and hyphen.
Display names are 1 through 120 printable characters. Passwords are not
normalized and are bounded before hashing.

Approved account statuses for this design are:

- `active`: may authenticate and use assigned permissions;
- `disabled`: cannot authenticate and all sessions fail immediately; and
- `locked`: temporarily blocked after repeated authentication failures.

When the lock expiry passes, the next otherwise valid login atomically returns
the account to `active`; an administrator with `administrator.manage` may also
unlock it earlier with a recorded reason.

Permissions, rather than client-supplied roles, control privileged operations:

- `administrator.manage`: create, disable, unlock, and assign permissions;
- `enrollment_token.issue`: issue general or device-bound pairing tokens; and
- `enrollment_token.revoke`: revoke eligible pairing tokens.

The bootstrap administrator initially receives all three permissions. A normal
enrollment administrator needs only the two enrollment-token permissions.
Permission changes revoke all existing sessions for the affected administrator
so stale JWTs cannot retain prior access.

## Password handling

- Require 12 through 128 Unicode code points.
- Do not trim, case-fold, or normalize a password.
- Reject known placeholder values in bootstrap and tests, but do not add an
  online breach-password dependency to this offline-capable MVP.
- Store only Werkzeug's versioned `scrypt` password verifier; never store or log
  a password or reversible password material.
- Perform a dummy verifier check when a username does not exist.
- After five consecutive failures, lock authentication for 15 minutes. A
  successful login resets the failure counter.
- Rate-limit login to 10 attempts per minute per source address. The account
  cooldown remains authoritative even when source addresses change.

Administrative recovery uses a trusted interactive CLI command that sets a new
password, records the operator-provided reason, revokes every active session,
and appends an audit event. It never reveals the previous password.

## Session and JWT contract

Use `Flask-JWT-Extended` with access tokens only during the MVP. Do not issue a
refresh token, set an authentication cookie, or add a persistent browser token.
The administrator signs in again after expiry.

Each access token must:

- use the configured fixed `HS256` algorithm and dedicated `JWT_SECRET_KEY`;
- expire after 15 minutes;
- contain `sub` as the administrator UUID;
- contain random `jti`, `iat`, `nbf`, `exp`, `iss`, and `aud` claims;
- contain no password, permission list, pairing token, device identity, or
  other sensitive operational data; and
- be returned only once in the successful login response with
  `Cache-Control: no-store`.

The database stores a SHA-256 digest of `jti`, the administrator ID, issue and
expiry times, revocation metadata, and bounded request context. A protected
request validates the JWT cryptographically and then loads the matching session
and administrator. Database errors, missing records, mismatched identities, or
invalid status all deny access.

Logout revokes the current session. An emergency CLI command and administrator
disablement revoke all sessions. Expired session rows may be retained according
to the forensic retention policy and must not be silently reused.

Production startup must continue requiring a distinct `JWT_SECRET_KEY` of at
least 32 characters. Changing that key invalidates every outstanding token and
must be treated as a documented emergency or planned rotation operation.

## Proposed API contract

Authentication routes use the existing `/api/v1` prefix:

```http
POST /api/v1/admin/auth/login
POST /api/v1/admin/auth/logout
GET  /api/v1/admin/auth/me
```

Login accepts a JSON object no larger than 16 KiB:

```json
{
  "username": "enrollment.admin",
  "password": "administrator-entered password"
}
```

A successful login returns HTTP 200:

```json
{
  "access_token": "displayed once",
  "token_type": "Bearer",
  "expires_in": 900,
  "administrator": {
    "administrator_uuid": "c82810ae-1b24-4d79-b55c-c3aa47e41b87",
    "username": "enrollment.admin",
    "display_name": "Enrollment Administrator"
  }
}
```

All invalid login conditions return HTTP 401 with one response:

```json
{
  "error": "authentication_failed"
}
```

Protected administrator requests use:

```http
Authorization: Bearer <access-token>
```

Missing, expired, revoked, disabled, or otherwise invalid sessions return the
same HTTP 401 response. A valid administrator lacking the required permission
receives HTTP 403 with `{"error":"authorization_failed"}`. Both responses use
`Cache-Control: no-store` and reveal no account, session, or permission details.

The later token-administration routes remain:

```http
POST /api/v1/admin/enrollment-tokens
POST /api/v1/admin/enrollment-tokens/<token_uuid>/revoke
```

The first requires `enrollment_token.issue`; the second requires
`enrollment_token.revoke`. Their service layer receives the verified
administrator UUID and canonical username from the authentication context.
Neither route accepts an administrator identity in its request body.

## Bootstrap and recovery boundary

The proposed CLI operations are:

```text
flask admin bootstrap
flask admin reset-password <username>
flask admin disable <username>
flask admin revoke-sessions <username>
```

Interactive prompts collect passwords twice using hidden input. Mutating
commands require a bounded reason and identify the trusted operator through an
explicit non-secret subject. Bootstrap refuses to run when an administrator
already exists unless a separately approved recovery procedure is used.
Commands use a database transaction and append an event before commit.

`bootstrap` requires `--username`, `--display-name`, `--operator`, and
`--reason`. The three recovery commands accept the canonical username argument
and require `--operator` and `--reason`. No command defines a `--password`
option; bootstrap and reset obtain it only from the hidden confirmation prompt.

Production deployment documentation must restrict these commands to trusted
host operators. They must never be exposed as web routes or executed by the
Android DPC.

## Persistence proposal

Implementation requires separately reviewed models and a migration:

### `Administrator`

- UUID, canonical username, display name, password verifier, and status;
- failed-attempt count and lock expiry;
- creation, update, password-change, and disable timestamps; and
- restrictive uniqueness and status/check constraints.

### `AdministratorPermission`

- administrator ID and exact permission name;
- granting administrator, reason, and grant timestamp; and
- uniqueness on administrator and permission.

### `AdministratorSession`

- administrator ID, SHA-256 JTI digest, issue and expiry times;
- revocation time, actor, and reason; and
- unique JTI digest with restrictive foreign keys.

### `AdministratorAuthenticationEvent`

- random event UUID, administrator ID when safely known, category, timestamp;
- bounded failure class, keyed source-address pseudonym, session JTI digest when
  applicable, acting administrator or trusted-operator subject, and reason;
- no username entered during a failed login, password, JWT, pairing token,
  request body, or raw source address.

Event categories include bootstrap, login success/failure, account lock/unlock,
password reset, logout, session revocation, account disablement, permission
grant/revoke, and authorization failure. Enrollment token issuance and
revocation continue using `DeviceEnrollmentEvent`, linked to the verified
administrator subject and token row.

## Audit, logging, and redaction

Security events are appended in the same transaction as the state change they
describe. Login failures that do not change protected state still create a
bounded failure event without preserving the submitted username.

Operational logs use fixed event categories only. They must not contain:

- passwords or password verifiers;
- JWTs, authorization headers, JTI values, or cookies;
- pairing tokens, token verifiers, or pepper values;
- request bodies or submitted usernames on failed login; or
- raw source addresses.

When a stable source pseudonym is required for rate-abuse correlation, compute
`HMAC-SHA-256(ADMIN_AUDIT_PSEUDONYM_KEY, canonical_source_address)` and retain
only the result. A plain hash is prohibited because the IPv4 input space is
small. The pseudonym key is separate from Flask, JWT, and pairing-token secrets;
administrator authentication must fail closed in production when it is enabled
without this key.

Sentry must continue excluding request bodies and authorization data. Tests
must inspect logs and captured error context for representative success and
failure paths.

## Failure and transaction behavior

- Authentication and authorization fail closed on database or configuration
  errors.
- Bootstrap, password reset, permission changes, account status changes,
  logout, and session revocation commit their event and state change together.
- Login commits the session, success event, and failure-counter reset together.
- A failed login commits the bounded failure event and counter/lock update
  together.
- Pairing-token issuance or revocation later commits its enrollment event and
  token state together.
- No response is sent with a usable JWT or pairing token until the associated
  database transaction succeeds.

## Implementation sequence and approval gates

Administrator authentication should be implemented before resuming enrollment
Sub-step 3:

1. administrator, permission, session, and authentication-event models;
2. reviewed migration and CLI bootstrap/recovery commands;
3. login, logout, session validation, rate limiting, and authorization checks;
4. PostgreSQL constraints, transaction, lockout, redaction, and authorization
   tests; and
5. security review and explicit authorization to expose enrollment-token
   administration routes.

Each item remains separately approval-gated. No enrollment pairing token is
created during these increments.

## Acceptance requirements before enrollment Sub-step 3 resumes

- The administrator persistence migration passes upgrade, downgrade, and
  upgrade verification on the approved Neon integration-test branch.
- Bootstrap and recovery never accept passwords on the command line or log
  secret material.
- Authentication uses generic failures and verified constant-work behavior.
- Session and administrator status are checked from PostgreSQL on every
  protected request.
- Permission checks ignore any client-supplied administrator identity or role.
- Lockout, rate limiting, revocation, expiry, rollback, and secret-redaction
  tests pass.
- Token-administration routes remain absent until their final exposure is
  explicitly approved.

## Explicitly deferred work

- multi-school tenancy;
- external identity providers, email, SMS, and online password recovery;
- MFA and hardware security keys;
- browser frontend implementation and CSP deployment;
- automated signing-key rotation;
- remote host-operator identity integration; and
- production alert routing and long-term audit archival.

MFA is strongly desirable for production beyond this proof of concept. Its
absence is an explicit residual risk, not evidence that privileged accounts are
safe with passwords alone.
