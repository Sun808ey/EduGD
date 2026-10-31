# Android DPC panel demonstration runbook

## Purpose

This runbook demonstrates the implemented Android DPC without claiming physical-device certification. The learner-facing DPC remains intentionally minimal. Policy controls are made in the administrator web dashboard, persisted by the backend/database, signed by the server, synchronized by the DPC, and verified in the debug-only read-back harness.

## Evidence boundary

The demonstration proves:

- the debug APK builds;
- the manifest contains the Device Admin, fully managed provisioning, compliance, boot, and VPN components;
- the DPC can be made device owner in a clean Android emulator;
- dashboard policy assignment reaches the backend control-plane routes and database state;
- the DPC verifies signed state, applies the existing policy path, acknowledges it, and exposes Android `DevicePolicyManager` read-back;
- local policy, identity, audit, and outbox state are persisted.

It does not prove OEM-specific handset behavior, physical emergency-call behavior, hardware attestation, or API 29–35 device coverage.

## Before the panel

Run from `android-dpc`:

```powershell
.\gradlew.bat testDebugUnitTest assembleDebug
```

The resulting APK is:

```text
android-dpc/app/build/outputs/apk/debug/app-debug.apk
```

For the disposable local backend scenario, provide credentials through the
environment rather than storing them in source:

```powershell
Set-Item Env:EDUG_DEMO_ADMIN_PASSWORD (Read-Host 'Enter the disposable demo administrator credential')
Set-Item Env:EDUG_DEMO_READONLY_PASSWORD (Read-Host 'Enter the disposable demo read-only credential')
```

These values are required only when running `backend/scripts/seed_local_demo.py`
or `backend/scripts/local_stack.py --e2e --demo-scenario`. Never reuse them for
hosted, staging, or production environments.

Prepare a clean API 35 Android Studio emulator. The emulator must have no account, work profile, or existing device owner. Keep a screen recording and screenshots as backup because the presentation workstation may not have Android SDK tools installed.

## Live emulator setup

From `android-dpc`:

```powershell
.\scripts\run-panel-demo.ps1
```

The script installs the debug APK, sets the EduGD admin receiver as device owner, verifies ownership, and launches the debug-only harness. To also show the learner-facing status screen:

```powershell
.\scripts\run-panel-demo.ps1 -SkipInstall -OpenLearnerUi
```

Equivalent manual commands are:

```powershell
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell dpm set-device-owner --user current io.github.sun808ey.edugd.dpc/.admin.AdminReceiver
adb shell dpm list-owners
adb shell am start -n io.github.sun808ey.edugd.dpc/.demo.DpcDemoActivity
```

## End-to-end dashboard demonstration

Use local backend/database and the administrator dashboard prepared for the demo. Do not introduce hosted-provider configuration during the panel.

1. Open the administrator dashboard and select the registered emulator device.
2. Create or select an approved policy revision with a visible, reversible control such as a kiosk package list, an application restriction, or a screen-lock timeout.
3. Assign the policy revision from the device policy-assignment workflow.
4. Show the dashboard response and the device detail/evidence view. The dashboard action is not a local Android setting: it persists through the policy-assignment API and database.
5. In the DPC demonstration harness, press **Queue real backend sync**. This schedules the existing `SyncWorker`; it does not create a local policy.
6. Press **Refresh read-back**. Point to the following fields:
   - Device Owner;
   - enrollment state and device UUID;
   - active policy revision, desired hash, and applied hash;
   - default mode and package counts;
   - enabled `DevicePolicyManager` restrictions;
   - camera/screen-capture state;
   - lock-task permission and lock timeout;
   - pending audit outbox;
   - audit-chain validity and last sequence.
7. Return to the dashboard and refresh the device evidence/audit view to show the acknowledgement and reported state.

## Source trace to show on screen

| Panel claim | Implementation evidence |
|---|---|
| Admin policy assignment is server-controlled | [`policies.py`](../backend/app/routes/policies.py:195) |
| DPC state is fetched through the signed v3 state endpoint | [`dpc_controls.py`](../backend/app/routes/dpc_controls.py:358) and [`BackendIntegrationClient.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/sync/BackendIntegrationClient.kt:40) |
| Signed state and policy are verified before use | [`BackendIntegrationClient.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/sync/BackendIntegrationClient.kt:88) |
| The normal worker applies the policy | [`SyncWorker.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/sync/SyncWorker.kt:38) and [`AtomicPolicyActivator.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/policy/AtomicPolicyActivator.kt:52) |
| Android restrictions are applied by the DPC | [`DevicePolicyController.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/admin/DevicePolicyController.kt:236) |
| Acknowledgement returns to the backend | [`StateSyncClient.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/sync/StateSyncClient.kt:15) and [`device_audit.py`](../backend/app/routes/device_audit.py:76) |
| Local policy and evidence are retained | [`DpcDatabase.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/db/DpcDatabase.kt:10) and [`AuditChain.kt`](../android-dpc/app/src/main/java/io/github/sun808ey/edugd/dpc/audit/AuditChain.kt:50) |
| The panel read-back is debug-only | [`DpcDemoActivity.kt`](../android-dpc/app/src/debug/java/io/github/sun808ey/edugd/dpc/demo/DpcDemoActivity.kt:35) |

## Recommended wording

> “This is an emulator-level demonstration of the implemented DPC and its real dashboard-to-backend-to-device control path. The debug harness only reads back state and queues the normal synchronizer; it does not replace the administrator dashboard. Physical-device, OEM, emergency-call, and API 29–35 certification remain separate release gates.”

## Evidence pack

Export this Markdown file to PDF or include it as an appendix with:

- the APK checksum and build result;
- one architecture diagram;
- one dashboard assignment screenshot;
- one emulator device-owner screenshot;
- one DPC harness read-back screenshot;
- one dashboard acknowledgement/audit screenshot;
- the source trace table above;
- the explicit evidence boundary above.
