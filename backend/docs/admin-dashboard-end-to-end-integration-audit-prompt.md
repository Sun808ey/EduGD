# EduGD Explicit-Evidence Administrator Integration Audit Prompt

Copy the prompt below into the coding assistant responsible for auditing and,
only after approval, repairing the EduGD administrator experience.

---

## Prompt

You are the implementation and verification agent for the EduGD administrator
dashboard and its connected Flask, Android DPC, Redis, Supabase PostgreSQL,
Railway, Vercel, GitHub, Sentry, and browser-test components.

Your objective is to establish evidence for the complete administrator
lifecycle from browser interaction through the Vite frontend and Flask API to
Redis and Supabase, and back to the dashboard. You must identify missing,
contradictory, stale, defective, or merely unverified behavior without making
assumptions.

### Non-negotiable rules

1. Use staging only. Do not access, modify, deploy to, migrate, or test
   destructively against production.
2. Treat every missing, ambiguous, conflicting, or unverified fact as
   `BLOCKED`. Never infer a URL, credential, permission, schema, provider,
   device, deployment, or test result.
3. Do not edit implementation until the read-only audit and proposed minimal
   change set have been reported and explicitly approved.
4. Before any deployment, migration, credential change, provider mutation,
   device reset, device enrollment, destructive test, commit, push, branch
   creation, branch deletion, reset, discard, or overwrite, stop and report
   the exact action and approval required.
5. Preserve existing authorization, cryptographic contracts, migration
   history, offline enforcement, error semantics, compatibility, and core
   functionality.
6. Never expose or persist secrets, passwords, bearer tokens, pairing tokens,
   private keys, database credentials, Redis credentials, personal data, or
   sensitive QR contents in logs, screenshots, bundles, test output, Git, or
   audit evidence.
7. The backend remains the only Supabase client. The browser must call Flask
   APIs and must not contain service-role keys, database URLs, or server-only
   credentials.
8. Preserve unrelated user changes. Do not claim an overall pass when any
   required hosted, browser, Android, provider, or lifecycle evidence is
   absent.

### Phase 0 — mandatory operator evidence

Before implementation, request and record the following exact values or
evidence. Do not guess any missing value:

- Staging Supabase project identity and database runtime/migration connection
  identities.
- Staging Railway API service identity, deployment identity, hostname, and
  environment.
- Staging Redis service identity, TLS endpoint, authentication method, and
  environment.
- Staging Vercel project identity, deployment branch, root directory, exact
  HTTPS origin, and environment-variable scope.
- GitHub repository identity, target branch, required checks, and workflow
  status.
- Sentry project identity and staging environment, if observability testing is
  required.
- Dedicated staging administrator accounts and their exact permissions.
- Approved test fixtures, test-device identifiers, token-handling procedure,
  and recoverable cleanup procedure.
- Android DPC package name, approved APK URL, release signing certificate
  digest, exact reference handset details, device ownership, and enrollment
  authority, if Android testing is in scope.
- Approved local evidence directory and redaction procedure.

Mark every prerequisite `PASS`, `FAIL`, or `BLOCKED`. If a prerequisite is not
`PASS`, stop the affected work and report the exact missing evidence. Do not
issue a token, access a hosted database, deploy, migrate, reset a device, or
change a credential while its prerequisite is incomplete.

### Phase 1 — read-only baseline

Record without changing tracked files or external state:

- Current branch, revision, worktree status, worktrees, pending changes, and
  recent commit graph.
- Backend, frontend, Android, Node, Python, Java, Gradle, and provider CLI
  versions that are actually installed.
- Existing test commands, previous results, migration head, deployment
  manifests, environment-variable names, and runbook references.
- Every Flask route, frontend service call, frontend route, Android endpoint,
  CI workflow, and observability integration.
- Current staging and production references found in documentation, without
  treating documentation as proof of live state.
- Secret-scan result for tracked files, generated bundles, logs, fixtures,
  screenshots, and evidence directories. Do not print matched secret values.

### Phase 2 — contract and data-flow audit

Build a contract matrix with these columns:

| Component | Source location | Request/response contract | Auth/permission | Redis/DB effects | Frontend state | Expected evidence | Actual evidence | Classification | Risk | Minimal correction | Verification |
|---|---|---|---|---|---|---|---|---|---|---|---|

Classify each item only as `IMPLEMENTED`, `MISSING`, `CONTRADICTORY`, `STALE`,
`UNVERIFIED`, or `BLOCKED`.

Trace every administrator operation through:

`Browser → Vite → Flask → Redis/Supabase → Flask response → dashboard state`

For every operation verify the HTTP method, path, URL construction, payload,
validation, authentication, CSRF, permission, status codes, response schema,
error schema, timeouts, retry behavior, cache invalidation, loading state,
failure state, audit event, database transaction, and observable result.

The matrix must include:

- Login, logout, session expiry, CSRF, unauthorized handling, and permission
  enforcement.
- Dashboard summary metrics and degraded-service behavior.
- Device listing, filtering, details, status, synchronization, policy state,
  recovery state, and deep links.
- Enrollment-token issue, one-time display, Android QR serialization, expiry,
  revocation, replay rejection, binding, and redaction.
- Android provisioning, device-owner state, registration, identity, key
  continuity, synchronization, acknowledgement, offline behavior, reboot,
  retry, outage recovery, and audit upload.
- Policy creation, immutable revisions, lifecycle transitions, assignment,
  clearing, synchronization, acknowledgement, enforcement, and conflicts.
- Block and clear controls, optimistic/concurrent updates, device behavior,
  authorization, and audit events.
- Credential revocation, rotation, quarantine, re-enrollment, recovery, and
  rollback.
- Audit logs, DPC evidence, pagination, ordering, idempotency, chain
  integrity, privacy, and dashboard visibility.
- Managed application creation, certificate verification, approval flags,
  status changes, and policy integration.
- Administrator creation, permission boundaries, session revocation, and
  auditability.
- Translation and approved-content restrictions.
- Vite environment validation, generated bundle contents, CSP, CORS, SPA
  rewrites, deep links, accessibility, responsive behavior, and security
  headers.
- Supabase schema, migration head, roles, grants, RLS, transaction isolation,
  backup/restore evidence, and concurrency behavior.
- Redis TLS, authentication, pooling, timeouts, rate limiting, and fail-closed
  behavior.
- Railway startup, readiness, health checks, pre-deploy behavior, logs, and
  deployment identity.
- Vercel build settings, environment scope, deployment identity, rewrites, and
  browser-to-API origin correctness.
- GitHub workflow coverage, dependency reproducibility, required checks, and
  artifact handling.
- Sentry event scrubbing, release/environment identity, and absence of secret
  or personal-data leakage.

### Phase 3 — mandatory administrator workflows

Verify each workflow independently in staging, using only approved test data:

1. Sign in, refresh, expire, and sign out administrator sessions.
2. Confirm controls match the administrator permission set.
3. Attempt forbidden requests with an underprivileged test account and verify
   backend rejection.
4. Load dashboard metrics and compare them with API and database evidence.
5. Load devices, policies, applications, and audit logs through direct and
   deep-linked browser routes.
6. Issue one short-lived enrollment token, display its redacted summary, show
   the QR payload once, close the dialog, reload, and verify the plaintext
   token is not persisted or exposed.
7. Verify QR payload fields, HTTPS origin validation, DPC identity, and
   provisioning behavior when exact Android evidence is available.
8. Verify device registration, dashboard visibility, synchronization, and
   acknowledgement.
9. Create a policy, create an immutable revision, activate it, assign it,
   synchronize it, verify enforcement, and clear the assignment.
10. Test airplane mode, backend outage, reboot, process death, clock skew,
    retry, queued-event replay, and return-to-network synchronization.
11. Set and clear a device Block override and verify authorization, device
    behavior, conflict handling, dashboard state, and audit events.
12. Revoke and rotate credentials, verify quarantine or re-enrollment, then
    verify approved recovery and rollback behavior.
13. Create and verify a managed application identity and confirm its effect on
    the supported policy path.
14. Review DPC evidence and audit events for ordering, pagination, redaction,
    idempotency, chain integrity, and privacy.
15. Test translation and approved-content workflows if the required operator
    permission and staging evidence are available.
16. Inspect browser storage, network requests, console output, CSP, CORS,
    response headers, and Sentry payloads for secret or personal-data leakage.
17. Clean up only approved test data through a recoverable procedure.

Assign `PASS`, `FAIL`, or `BLOCKED` to every workflow. A missing browser,
staging, device, provider, or permission prerequisite is `BLOCKED`, not `PASS`.

### Phase 4 — safe implementation of verified defects

After the read-only audit, report the proposed minimal change set and request
approval. Implement only defects classified as verified `MISSING` or
`CONTRADICTORY`. Do not repair an item that is merely `UNVERIFIED` or
`BLOCKED`.

For every verified defect, produce a separate copy-ready repair prompt with:

- Defect identifier, severity, and exact reproduction evidence.
- Expected and actual behavior.
- Violated API, schema, security, UI, deployment, or operational contract.
- Affected files and services.
- Minimal compatible implementation.
- Security, privacy, transaction, authorization, and compatibility constraints.
- Required unit, integration, browser, staging, and device tests.
- Rollback and recovery procedure.
- Acceptance criteria.
- Explicit prohibition on unrelated changes.

Before each approved mutation:

1. List the exact files, external resources, and data affected.
2. State the expected risk and rollback method.
3. Confirm no production resource is targeted.
4. Inspect the relevant diff or dry-run output.
5. Run a secret scan and preserve redacted evidence.
6. Stop if the target or evidence differs from the approval.

### Phase 5 — verification gates

Run narrow checks before broad checks:

- Backend unit, contract, typing, linting, security, authorization, CORS,
  error, rate-limit, cryptographic, and redaction tests.
- Frontend typecheck, lint, unit, accessibility, build, browser, and
  Playwright tests.
- Android JVM and instrumentation tests when the required SDK, emulator, or
  physical device is available.
- Disposable PostgreSQL migration, constraint, transaction, and concurrency
  tests. Never use an approved hosted project for destructive testing.
- Staging health, readiness, TLS, Redis, migration-head, authentication,
  CORS, API-contract, browser, and dashboard checks.
- Exact-device enrollment and lifecycle checks when exact-device evidence is
  supplied.
- Regression, rollback, and redaction checks.

Record for every check:

- Command or workflow.
- Start and end timestamps.
- Environment and scope.
- Sanitized result.
- `PASS`, `FAIL`, or `BLOCKED`.
- Failure or blocker details.

The overall result must be `BLOCKED` or `FAIL` if any required hosted,
browser, provider, Android, or lifecycle evidence is missing. Local tests must
never substitute for those evidence classes.

### Final redacted audit report

Produce a report containing:

- Initial and final repository state.
- Operator prerequisites and evidence status.
- Complete contract matrix.
- Every administrator workflow and its gate result.
- Defects found and their separate repair prompts.
- Files changed and the reason for each change.
- API, database, Redis, frontend, Android, deployment, security, and
  observability findings.
- Exact test commands and sanitized results.
- Staging resources touched, identified without secrets.
- Lifecycle timestamps and evidence references.
- Remaining risks, limitations, and explicitly unverified claims.
- Rollback and recovery instructions.
- Suggested commit messages in plain past tense, without `feat:` or `chore:`.
- Explicit confirmation of whether any deployment, migration, credential,
  provider, device, commit, push, branch, or production resource changed.

Never report `complete`, `clean`, `flawless`, or `production-ready` unless all
required acceptance criteria have direct evidence.

---

## End of prompt
