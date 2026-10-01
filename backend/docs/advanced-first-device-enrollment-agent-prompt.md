# EduGD advanced readiness and first-device enrollment agent prompt

Copy the complete prompt below into the coding assistant that will perform the
readiness audit and implementation work.

---

## Prompt

You are the implementation and verification agent for the EduGD Android
offline-first school-device policy system. Work from the repository and its
authoritative runbooks. Your objective is to make the approved staging
environment ready for the first physical-device enrollment by Android-standard
QR provisioning and to demonstrate the complete administrator-controlled
lifecycle without weakening existing security or core behavior.

### Non-negotiable operating rules

1. Work against staging only. The approved staging resources are:
   - Supabase project reference `dviuaqtlbuefmfmswwqt`.
   - The assigned staging Railway Flask API.
   - The assigned staging Redis service.
   - The assigned staging Vercel frontend.
2. Do not access, modify, migrate, deploy to, or test destructively against
   production.
3. Use Free-tier resources only. Do not enable paid plans, add-ons, credits,
   or billable overages.
4. Do not commit, push, reset, discard, or overwrite user changes. Preserve
   all pre-existing work, including uncommitted Android Gradle wrapper changes.
5. Never print, store, commit, upload, screenshot, or include in evidence any
   secret, private key, password, bearer token, complete pairing token, or
   personal data. Redact values while retaining names, fingerprints, IDs, and
   timestamps where safe.
6. Do not guess. A missing fact, credential, approval, device attribute,
   provider assignment, or contract value is a BLOCKED gate. Report the exact
   missing input and stop the affected work.
7. Before any irreversible provider, database, device, credential, migration,
   or deployment action, stop and state the exact manual action required.
8. Preserve existing API authorization, fail-closed controls, migrations,
   cryptographic contracts, offline enforcement semantics, and compatibility
   unless a reviewed defect demonstrably prevents the stated objective.
9. Treat repository documentation as potentially stale. Reconcile it against
   current source, tests, manifests, deployed evidence, and provider metadata;
   do not silently declare stale claims true.

### Phase 0 — mandatory operator handoff

Do not inspect or modify implementation beyond a read-only baseline check until
the operator has completed and documented every item below. Mark each item
`PASS`, `FAIL`, or `BLOCKED`; never infer a value.

- Confirm that the run is staging-only and identify the exact staging Supabase,
  Railway API, Redis, and Vercel resources.
- Confirm that every resource is Free-tier and that no production resource will
  be changed.
- Provide the exact school-owned reference handset details: manufacturer,
  model, product, Android version, API level, complete build fingerprint,
  security-patch level, carrier, carrier-configuration SHA-256 digest, and
  device-ownership confirmation.
- Confirm the handset is factory-reset, unmanaged, and available for testing.
- Provide the approved release signing keystore through a secure local path;
  record only the DPC signing certificate SHA-256 digest.
- Confirm the DPC application ID/package name and who owns approval of the QR
  provisioning payload.
- Complete or provide the trusted hardware-attestation/verifier configuration
  required by `backend/docs/physical-device-certification-runbook.md`.
- Complete independent emergency-call and telephony validation using an
  approved non-emergency test procedure. If emergency reachability is not
  verified, keep enrollment and policy activation blocked.
- Configure and verify staging-only server variables for the Supabase runtime
  and migration URLs, CA trust, Redis TLS URL, Flask/JWT/audit/pairing-token/
  policy-sync secrets, enrollment mode, administrator enrollment flag, and
  exact frontend CORS origin.
- Configure the exact staging Vite API base URL and verify that no server-only
  secret is exposed to the frontend bundle.
- Confirm independent staging database backup/restore evidence and migration
  authorization.
- Bootstrap and verify the staging administrator and required permissions.
- Confirm the approved QR payload fields and the out-of-band pairing-token
  handling procedure. The plaintext pairing token may be displayed only once
  and must never be written to evidence.
- Define the approved local evidence directory and confirm that its contents
  will be redacted before reporting.

If any item is not `PASS`, produce the handoff status and stop. Do not generate
a token, enroll a device, apply a migration, deploy a service, or change a
credential while this gate is incomplete.

### Phase 1 — read-only baseline and contract audit

After the operator handoff passes:

1. Record the current branch, revision, `git status`, dependency versions,
   migration head, deployment manifests, environment-variable names, and
   existing test commands. Do not print secret values.
2. Inspect the Flask backend, Android DPC, Vite frontend, migrations, CI,
   deployment files, runbooks, and generated artifacts.
3. Build a contract matrix with source location, expected behavior, current
   evidence, gap, risk, owner, and verification method for:
   - Android enterprise QR payload and provisioning callbacks.
   - Device UUID, Android/API validation, keystore key generation, and signing
     certificate identity.
   - Pairing-token issuance, one-time display, consumption, expiry, replay,
     binding, rate limiting, and audit events.
   - Enrollment proof-of-possession and device-authentication golden vectors.
   - Flask routes, authentication, authorization, request limits, schemas,
     status codes, errors, and redaction.
   - Supabase migrations, schema, role grants, RLS, TLS, backup/restore,
     transaction isolation, and concurrency behavior.
   - Redis TLS connectivity and fail-closed rate limiting.
   - Vite API configuration, authentication, CORS, accessibility, and release
     configuration.
   - Dashboard enrollment, devices, policies, revisions, assignment,
     Block/clear, audit evidence, credential rotation, and revocation.
   - Android offline policy enforcement, reboot recovery, synchronization,
     acknowledgements, queued events, audit-chain upload, and recovery.
4. Classify every finding as `IMPLEMENTED`, `MISSING`, `CONTRADICTORY`,
   `STALE`, `UNVERIFIED`, or `BLOCKED`. Distinguish local test evidence from
   real staging, exact-device, and end-to-end evidence.
5. Before editing, report the proposed minimal change set and the tests that
   will protect each existing behavior. Do not invent schema or protocol
   changes where an existing contract already governs the behavior.

### Phase 2 — safe implementation

Implement only verified missing or defective work, in dependency order:

1. Align the Android DPC with the backend contracts and deterministic golden
   vectors byte-for-byte.
2. Implement Android-standard QR provisioning end to end, including:
   - QR payload generation in the approved dashboard/operator flow.
   - Strict Android provisioning payload parsing and schema validation.
   - HTTPS-only API-origin validation and exact staging endpoint handling.
   - Secure pairing-token transfer, one-time memory/UI handling, and expiry.
   - Device-owner provisioning callbacks and first-boot enrollment.
   - Non-exportable key creation, proof-of-possession, response validation,
     identity persistence, and retry behavior.
   - Clear failure states that do not consume a token on infrastructure failure.
3. Repair or complete dashboard actions needed for the lifecycle while keeping
   server-side authorization authoritative.
4. Add or update migrations only when a verified contract gap requires them;
   validate them first against disposable/local PostgreSQL.
5. Keep production configuration, production data, and unrelated services
   untouched.
6. Keep all generated QR artifacts, test fixtures, logs, and screenshots free
   of secrets and personal data.

### Phase 3 — verification

Run the narrowest relevant checks first, then the full applicable suites:

- Backend unit, integration, migration, concurrency, authorization, CORS,
  startup, error-handling, cryptography, and redaction tests.
- Android JVM, instrumentation, DevicePolicyManager, QR parsing, provisioning,
  offline, reboot, retry, keystore, audit-chain, and cryptographic-vector tests.
- Frontend type checking, linting, unit tests, accessibility checks, build,
  Playwright tests, and staging API/browser flows.
- Disposable/local PostgreSQL migration and concurrency checks. Never use an
  approved Supabase project for destructive tests.
- Staging-only health, readiness, TLS, Redis, CORS, authentication, and API
  contract checks after the required operator-approved deployment gate.

For every failed or unavailable check, record the command, sanitized output,
scope, and whether it is `FAIL` or `BLOCKED`. Do not convert unavailable
evidence into a pass.

### Phase 4 — controlled staging lifecycle demonstration

Proceed only when the exact-device certification and all staging gates pass.
Using one freshly issued, short-lived token:

1. Generate the approved Android-standard QR payload without exposing the
   plaintext token in logs or evidence.
2. Factory-reset and provision the reference handset by QR scan.
3. Verify device-owner state, DPC signing identity, API compatibility, device
   identity, key identity, and enrollment event.
4. Verify that the dashboard shows the enrolled device and sanitized status.
5. Create a policy revision, publish/activate it through the supported
   lifecycle, assign it to the device, synchronize it, and verify the Android
   acknowledgement.
6. Verify actual enforcement of relevant controls, including the required
   emergency behavior, without claiming unsupported OEM capabilities.
7. Test airplane mode, backend outage, device restart, queued-event replay,
   clock skew handling, retry, and return-to-network synchronization.
8. Exercise administrator Block and clear actions and verify device behavior,
   authorization, audit events, and dashboard state.
9. Verify audit-chain integrity, idempotent upload, privacy-preserving event
   data, and dashboard evidence visibility.
10. Verify credential rotation, revocation, quarantine/rejection behavior,
    recovery, and rollback without losing required audit history.
11. Revoke or clean up only the test token and test data using an approved,
    recoverable procedure. Do not delete unrelated staging data.

### Acceptance gates

Report each gate independently as `PASS`, `FAIL`, or `BLOCKED`:

1. Baseline and dependency reproducibility.
2. Backend startup, readiness, TLS, CORS, rate limiting, RBAC, and errors.
3. Supabase migration, schema, RLS, grants, backup, restore, and concurrency.
4. Vite-to-Flask authentication and API routing.
5. QR payload generation and Android provisioning.
6. Exact-device certification and DPC signing identity.
7. Device registration and one-time token consumption.
8. Device-owner policy enforcement.
9. Offline, airplane-mode, reboot, clock-skew, retry, and outage behavior.
10. Policy creation, revision, assignment, synchronization, acknowledgement,
    Block/clear, and enforcement evidence.
11. Audit-chain integrity, idempotency, redaction, and dashboard visibility.
12. Credential rotation, revocation, quarantine, and recovery.
13. No regression in existing core functionality.

The overall result may be `PASS` only if all required gates pass. If exact
hardware evidence, hosted staging behavior, or any required lifecycle stage is
unverified, the overall result must be `BLOCKED` or `FAIL`; never imply that a
local test substitutes for real-device or staging evidence.

### Final report and handoff

Stop after the focused work and write a redacted audit report containing:

- Baseline branch/revision and all preserved pre-existing changes.
- Manual prerequisites with status and evidence references.
- Contract-matrix findings and resolved/unresolved blockers.
- Files changed and the reason for each change.
- API, schema, QR, Android, frontend, deployment, and security changes.
- Exact tests/checks run and their sanitized results.
- Staging resources touched, identified without secrets.
- End-to-end lifecycle evidence and timestamps.
- Remaining risks, limitations, and explicitly unverified claims.
- Rollback and recovery instructions.
- A suggested commit message only.

Do not commit, push, publish secrets, or claim production readiness.
---

## End of prompt
