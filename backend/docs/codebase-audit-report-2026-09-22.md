# EduG requested-feature audit

Date: 2026-09-22
Repository state audited: `main` at `132267b`

## Result

The requested Android device-management features cannot be confirmed as existing or flawless. EduG has a well-tested **server-side policy protocol**, an authenticated administration portal for assigning existing immutable policy revisions, and an authenticated audit-ingestion contract. It does not contain an Android Device Policy Controller (DPC), Android build files, or an Android runtime implementation that could enforce these policies on a school-managed phone or tablet.

The protocol document itself confirms this boundary: it is a wire specification, not a claim that an Android client is present.

| Requested capability | Audit status | Evidence and finding |
| --- | --- | --- |
| Daily Screen Time limit | **Not implemented** | The policy schema supports day/time schedules that select a mode, but has no cumulative usage counter, daily allowance, usage-reporting event, or enforcement action for a daily device-time quota. Schedules are time windows, not Screen Time limits. |
| Admin-configured device-use amount | **Not implemented** | No data model or API accepts a per-student/per-device daily duration. The portal can assign or clear a pre-existing policy revision, but it has no policy-authoring control for a duration limit. |
| Web filtering and browsing control | **Not implemented** | No URL/domain/category filter schema, browser policy, proxy/VPN/DNS enforcement integration, browsing-event type, or browsing-report UI exists. The only `browser` references concern the web administration application. |
| Browsing tracking | **Not implemented** | The device audit protocol records policy and device-enforcement events, but its fixed event codes contain no URL, domain, browser, or browsing-history event. The admin audit screen exposes only administrative, enrollment, assignment, and synchronization event categories. |
| Hide/show selected apps | **Partially specified; not implemented end-to-end** | Policy modes require an application allowlist and permit an explicit blocked-package list. Schedules can select different modes at times of day. This is a sound server contract for an eventual DPC, but there is no Android code to hide, suspend, enable, disable, or otherwise apply it; nor is there an admin UI to create or edit these modes. |
| Remote device lock / immediate Block mode | **Not implemented** | There is no remote command, lock-now route, block-mode field, device-lock audit event, or Android DPC receiver. `lock_task_packages` is a package allowlist for Android lock task mode; it is not a remotely triggered lock-device command. |

## Evidence inspected

- [`policy_contract.py`](/E:/EduG/backend/app/policy_contract.py) defines a signed policy v2 with named modes, package allowlists/blocklists, lock-task packages, boolean device controls, and weekly minute-of-day schedules. It validates those structures, including schedule overlap rules.
- [`device_capability_profile.py`](/E:/EduG/backend/app/device_capability_profile.py) resolves a policy for a verified device profile and preserves essential/emergency packages. It is server-side validation, not enforcement.
- [`dpc-policy-protocol-v2.md`](/E:/EduG/backend/docs/dpc-policy-protocol-v2.md) explicitly labels the material as a backend contract for an Android DPC that “must implement” it and states that the Android client is not claimed to be in this repository. It also lists enrollment, profile persistence, signed-policy synchronization, and other production activation work as remaining.
- [`device_audit_contract.py`](/E:/EduG/backend/app/device_audit_contract.py) defines tamper-evident audit batches for policy/device events. Its fixed event set has no web-access or device-lock event.
- [`device_audit.py`](/E:/EduG/backend/app/routes/device_audit.py) exposes authenticated audit, check-in, and policy-acknowledgement ingestion routes. No remote-control route was found.
- [`devices.tsx`](/E:/EduG/frontend/school-policy-admin/src/pages/devices.tsx) permits an authorized administrator to assign or clear an existing revision. [`PolicyDetailPage.tsx`](/E:/EduG/frontend/school-policy-admin/src/pages/PolicyDetailPage.tsx) displays a revision payload read-only. The frontend README also states that browser screens for policy creation do not exist.
- A repository-wide filename search found no `AndroidManifest.xml`, Gradle build/settings files, `gradlew`, Kotlin, or Java source. A focused terminology search found no implementation of web filtering, URL allow/block lists, browsing tracking, remote lock, Block mode, or Screen Time.

## Verification performed

Focused backend contract tests were run locally:

```text
125 passed, 1 warning in 23.13s
```

The passing tests cover policy normalization and signature verification, schedule validation, fail-closed device-capability resolution, authenticated policy synchronization, status contracts, and tamper-evident audit ingestion. They validate the backend contract only; they do not prove Android enforcement, browser filtering, app hiding, time accounting, or device locking.

## Conclusion

EduG currently provides foundations for a future managed-Android product, most directly the scheduled app-policy contract and secure device-policy/audit APIs. None of the requested user-facing management features can be represented as flawless in the audited codebase. The only partially present capability is the server-side specification for scheduled app allow/block policies, which remains unenforced until an Android DPC and the related management workflows are built and tested on physical managed devices.
