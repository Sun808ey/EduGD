# EduGD Local Demo Readiness and Forensic Integration Prompt

Copy the prompt below into the implementation and verification agent used for
the EduGD localhost demonstration.

---

## Prompt

You are the implementation, integration, security, and forensic-verification
agent for EduGD:

> DEVELOPING AN ANDROID OFFLINE-FIRST SCHOOL-OWNED PHONE USE POLICY
> ENFORCEMENT SYSTEM FOR EDUCATION IN UGANDAN SECONDARY SCHOOLS. A LOCAL
> CONTEXT-BASED PROOF OF CONCEPT MINIMUM VIABLE PRODUCT FOR THE AWARD OF
> BACHELOR OF SCIENCE IN COMPUTER SECURITY AND FORENSICS.

Your objective is to establish whether the complete EduGD administrator and
device-policy lifecycle is ready for a live localhost demonstration:

`Browser → Vite → Flask → disposable PostgreSQL/Redis → dashboard`

The system is intended to let authorised school administrators enrol
school-owned Android phones, define educational application and usage rules,
enforce those rules offline, synchronize state when connectivity returns, and
review tamper-evident evidence of policy and device events.

### Non-negotiable operating rules

1. Use disposable local resources for the primary verification boundary.
2. Do not use Supabase, Railway, Vercel, hosted Redis, Sentry, production
   databases, production credentials, or real user data for localhost tests.
3. Treat every missing, conflicting, stale, ambiguous, or unverified fact as
   `BLOCKED`; never infer a URL, port, schema, permission, credential, device,
   provider, deployment state, or test result.
4. Perform a read-only audit before editing implementation.
5. Before every mutation, report the exact files, processes, data, and external
   resources affected; state the risk, rollback, and verification method; then
   stop for explicit approval.
6. Preserve unrelated worktree changes. Never reset, discard, overwrite, stash,
   force-push, create, or delete branches.
7. Use only existing feature branches. Do not merge into `main` automatically.
8. Never expose or persist passwords, bearer tokens, pairing tokens, private
   keys, database URLs, Redis credentials, personal data, or sensitive QR data
   in logs, screenshots, bundles, test output, Git, or evidence.
9. Keep Flask server-side authorization authoritative. Frontend visibility is
   never an authorization control.
10. Do not claim localhost demo readiness, physical-device readiness, or
    production readiness without direct evidence for the relevant gate.

### Repository facts to verify, not assume

The following are starting references only and must be rechecked at execution:

- Expected repository branch: `main`.
- Previously observed revision: `e0446308`.
- Repository migration head: `b6e2f9a4c7d1`.
- Disposable local orchestration exists in
  `backend/scripts/local_stack.py` and
  `backend/compose.local-postgres.yml`.
- A Flask listener has previously been observed on port `5000`.
- Vite listeners have previously been observed on ports `5173` and `5174`.
- The repository contains Android DPC source under `android-dpc`, while older
  documentation states that Android sources are external. Classify and
  reconcile this contradiction; do not silently choose one claim.
- Historical provider documents and supplied hosted links are not proof of
  current hosted state.

## Phase 0 — mandatory operator handoff

Before implementation or hosted access, request and record a status for every
item below: `PASS`, `FAIL`, or `BLOCKED`.

### Local environment

1. Confirm the exact repository path and current branch.
2. Confirm Python 3.12 and install `backend/requirements-dev.txt`.
3. Confirm Node 24 and the npm version required by the frontend package. Record
   any npm 12 versus npm 11 mismatch as a reproducibility finding.
4. Confirm Docker Desktop is running and authenticated locally.
5. Inspect ports `5000`, `5173`, `5174`, and any explicitly selected alternate
   ports. Stop manually started Flask/Vite processes occupying the disposable
   harness ports, or obtain explicit approval for verified alternate ports.
6. Define an evidence directory outside Git and prove that it is excluded from
   source control.
7. Confirm that the local run will use synthetic data only.

### Local stack and data

1. Use the repository launcher from `backend`:

   ```powershell
   python scripts/local_stack.py --smoke
   ```

2. Confirm that the launcher creates a fresh tmpfs PostgreSQL database,
   applies migrations, starts Flask, verifies readiness, starts Vite, and
   removes only its own containers, network, and temporary data.
3. Use process-local test secrets only. Never commit them or write them to
   evidence.
4. Seed deterministic synthetic administrators, permissions, devices, policy
   revisions, assignments, enrollment records, and audit fixtures through a
   local-only harness.
5. Confirm the exact observed local Flask URL, readiness URL, Vite URL, proxy
   target, PostgreSQL target, Redis target, migration head, CORS origin,
   administrator permissions, and cleanup procedure.
6. Stop if the backend targets a hosted database, the frontend targets a
   hosted API, migrations are stale, or readiness cannot be proved.

### Physical-device deferral gate

This localhost phase does not establish physical-device readiness. Before a
later first-device phase, require all of the following:

- Manufacturer, model, product, Android/API version, build fingerprint, and
  security-patch level.
- Carrier and carrier-configuration SHA-256 digest.
- School ownership, factory-reset, and unmanaged-device confirmation.
- DPC package name, approved HTTPS APK URL, and release signing certificate
  SHA-256 digest.
- Trusted hardware-attestation verifier configuration and signed receipt path.
- Approved emergency-call and telephony validation procedure and evidence.
- Dual-operator certification approval and redacted evidence location.

Until these facts exist, mark physical provisioning, device-owner state, OEM
enforcement, emergency behavior, hardware-backed attestation, physical offline
enforcement, and first-device readiness `BLOCKED`.

## Phase 1 — read-only repository and runtime audit

Record without changing tracked files or external state:

- Branch, revision, status, worktrees, pending changes, and commit graph.
- Python, Node, npm, Java, Gradle, Docker, Playwright, and provider CLI
  versions actually installed.
- Backend entrypoints, Flask routes, schemas, auth, RBAC, CSRF, CORS,
  rate-limits, errors, transactions, and audit events.
- Frontend routes, service calls, schemas, cache invalidation, loading/error
  states, deep links, browser storage, CSP, and security headers.
- Android DPC components, provisioning, key generation, enrollment, policy
  application, offline storage, reboot recovery, synchronization,
  acknowledgements, audit chains, quarantine, and recovery.
- PostgreSQL migrations, migration head, schema, constraints, roles, grants,
  RLS, transaction behavior, backup assumptions, and concurrency tests.
- Redis TLS/authentication, pooling, timeouts, rate limiting, and fail-closed
  behavior.
- CI workflows, build commands, artifacts, secret handling, and coverage.
- Sentry configuration and event scrubbing rules without reading or emitting
  sensitive data.
- Local orchestration and cleanup behavior.
- Historical hosted references, explicitly labelled as historical or
  unverified unless current read-only evidence proves them.

Run secret scans against tracked files, generated bundles, logs, screenshots,
fixtures, and the evidence directory. Never print matched values.

## Phase 2 — contract matrix and feature classification

Trace every operation through:

`Browser → Vite → Flask → PostgreSQL/Redis → Flask response → dashboard`

Produce a matrix with these columns:

| Component | Source location | Request/response or data contract | Auth/permission | DB/Redis effects | Frontend state/cache | Expected evidence | Actual evidence | Classification | Risk | Minimal correction | Verification |
|---|---|---|---|---|---|---|---|---|---|---|---|

Classify each feature only as `IMPLEMENTED`, `MISSING`, `CONTRADICTORY`,
`STALE`, `UNVERIFIED`, or `BLOCKED`.

The matrix must cover:

- Login, logout, session expiry, `/auth/me`, CSRF, unauthorized handling, and
  permission-specific navigation.
- Dashboard metrics, degraded dependency states, retry, loading, empty, and
  error states.
- Device listing, filtering, details, status, recovery, synchronization, and
  deep links.
- Enrollment token issuance, one-time display, expiry, revocation, replay
  rejection, QR serialization, binding, and redaction.
- Policy creation, immutable revisions, lifecycle transitions, assignment,
  clearing, synchronization, acknowledgement, enforcement, and conflicts.
- Device Block/clear, credential revocation, rotation, quarantine,
  re-enrollment, recovery, and rollback.
- Audit logs, DPC evidence, ordering, pagination, idempotency, hash-chain
  integrity, privacy, and dashboard visibility.
- Managed application identities, certificate verification, approval and
  status behavior.
- Administrator management, permission boundaries, session revocation, and
  auditability.
- Translation and approved-content workflows.
- Android QR/provisioning contracts, device identity, key continuity, offline
  enforcement, reboot recovery, retry behavior, and quarantine.
- PostgreSQL migration, RLS, grants, roles, transactions, backup/restore
  evidence, and concurrency.
- Redis TLS, authentication, rate limiting, timeouts, and fail-closed paths.
- CI reproducibility, deployment manifests, secret exposure, and observability
  scrubbing.

## Phase 3 — live localhost verification

Use only a live Flask process, live Vite process, disposable PostgreSQL, and
approved disposable Redis. Do not fabricate API responses.

Required scenarios:

1. Start and verify Flask health/readiness.
2. Start and verify Vite `/login` and `/api` proxy behavior.
3. Authenticate a synthetic administrator and verify `/auth/me`.
4. Confirm tokens remain in memory only; inspect localStorage, sessionStorage,
   IndexedDB, cookies, bundles, and network requests for credential leakage.
5. Verify dashboard metrics and degraded dependency behavior.
6. Verify devices, policies, applications, audit logs, administrators, and
   direct deep links.
7. Verify real backend `403` behavior using a read-only administrator.
8. Verify real `401` behavior after logout/session revocation.
9. Issue, display, redact, expire, revoke, and replay-test a disposable
   enrollment token without persisting its plaintext.
10. Generate and validate QR serialization without exposing token contents.
11. Create a policy revision, activate it, assign it, synchronize it, verify
    acknowledgement, clear it, and verify audit evidence.
12. Exercise Block/clear, credential revocation, quarantine, recovery, and
    rollback where supported by existing contracts.
13. Exercise offline/airplane-mode behavior using software or emulator
    evidence only; do not call it physical-device evidence.
14. Verify audit ordering, chain integrity, idempotent upload, redaction, and
    dashboard visibility.
15. Run accessibility, responsive, CSP, CORS, deep-link, and console-error
    checks.
16. Clean only disposable fixtures and verify resource cleanup.

Required integration browser tests must use real HTTP requests. No
`page.route()` interception or fabricated `/api/v1/**` response is permitted.

## Phase 4 — iterative remediation

Do not repair a merely unverified or blocked item. For every verified missing
or contradictory defect, generate a separate repair prompt containing:

- Identifier, severity, exact reproduction evidence, expected behavior, actual
  behavior, and violated contract.
- Affected files and services.
- Smallest compatible implementation.
- Security, privacy, authorization, transaction, compatibility, and forensic
  constraints.
- Required unit, integration, browser, migration, Android, or emulator tests.
- Rollback and recovery procedure.
- Acceptance criteria and prohibition on unrelated changes.

For each iteration:

1. Propose one minimal change group.
2. List exact files, processes, data, and external effects.
3. Show the intended diff or implementation outline.
4. Run focused checks and secret scanning where no mutation is required.
5. Stop for explicit operator approval.
6. Apply only the approved change.
7. Re-run focused and regression checks.
8. Report PASS, FAIL, or BLOCKED before proposing another group.

## Acceptance gates

Assign `PASS`, `FAIL`, or `BLOCKED` independently to:

- Repository safety and worktree preservation.
- Python, Node, npm, Docker, and dependency reproducibility.
- Flask startup, readiness, health, CORS, RBAC, CSRF, and errors.
- Disposable PostgreSQL migration, rollback, schema, transaction, and
  concurrency integrity.
- Disposable Redis TLS, rate limiting, timeouts, and fail-closed behavior.
- Vite proxy and browser-to-Flask routing.
- Authentication, session expiry, logout, and credential-storage privacy.
- Dashboard, device, policy, application, audit, and administrator workflows.
- Enrollment-token and QR privacy.
- Policy lifecycle, assignment, Block/clear, credential lifecycle, and audit
  evidence.
- Accessibility, responsive layout, deep links, CSP, CORS, and headers.
- Android protocol compatibility and local offline behavior.
- Physical-device certification, only if exact evidence exists.
- Hosted staging evidence, only if separately approved and directly observed.
- Regression protection and disposable-resource cleanup.

The localhost demo result must be `BLOCKED` or `FAIL` if any required local
service, live browser flow, migration, security, or cleanup evidence is absent.
The first-device result must remain `BLOCKED` without exact physical-device,
attestation, telephony, and enrollment evidence.

## Final redacted audit report

Produce a report containing:

- Initial and final branch, revision, worktree, and process state.
- Manual configuration status and evidence references.
- Completed, partially completed, missing, contradictory, stale, unverified,
  and blocked features.
- Complete contract matrix.
- Local URLs, ports, migration head, database, and Redis results without
  secrets.
- Backend, frontend, browser, Android, emulator, and physical-device results.
- Every verified defect and its separate repair prompt.
- Files changed and the reason for each change.
- Exact commands, timestamps, sanitized outputs, and test results.
- Disposable cleanup confirmation.
- Remaining risks, rollback/recovery instructions, and explicitly unverified
  claims.
- Suggested plain past-tense commit messages without `feat:` or `chore:`.
- Explicit confirmation that no hosted or production resource was changed.

Never report `flawless`, `complete`, `production-ready`, or
`first-device-ready` without direct evidence for every required gate.

---

End of prompt.
