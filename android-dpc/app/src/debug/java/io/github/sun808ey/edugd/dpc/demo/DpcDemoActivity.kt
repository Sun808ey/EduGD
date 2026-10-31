package io.github.sun808ey.edugd.dpc.demo

import android.app.Activity
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.github.sun808ey.edugd.dpc.admin.DeviceRestrictionSettings
import io.github.sun808ey.edugd.dpc.admin.NetworkSettings
import io.github.sun808ey.edugd.dpc.admin.AdminReceiver
import io.github.sun808ey.edugd.dpc.audit.AuditChain
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentBootstrapCoordinator
import io.github.sun808ey.edugd.dpc.sync.SyncScheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Debug-only panel harness.
 *
 * This screen intentionally has no policy-editing controls. The administrator
 * dashboard and backend remain the only policy authority. The harness queues
 * the normal DPC sync worker and displays local database plus Android
 * DevicePolicyManager read-back for an evidence-backed demonstration.
 */
class DpcDemoActivity : ComponentActivity() {
    private var refreshNonce by mutableStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            var snapshot by remember { mutableStateOf<DemoSnapshot?>(null) }
            var loading by remember { mutableStateOf(true) }
            var syncQueuedAt by remember { mutableStateOf<String?>(null) }

            suspend fun refresh() {
                loading = true
                snapshot = withContext(Dispatchers.IO) { DemoSnapshot.load(this@DpcDemoActivity) }
                loading = false
            }

            LaunchedEffect(refreshNonce) { refresh() }

            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Text("EduGD DPC demonstration harness", style = MaterialTheme.typography.headlineSmall)
                        Text(
                            "Debug build only. Policy controls remain in the administrator dashboard and backend.",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Button(
                            modifier = Modifier.fillMaxWidth(),
                            onClick = {
                                SyncScheduler.schedule(this@DpcDemoActivity)
                                syncQueuedAt = java.time.Instant.now().toString()
                            },
                        ) {
                            Text("Queue real backend sync")
                        }
                        Button(
                            modifier = Modifier.fillMaxWidth(),
                            onClick = { refreshNonce++ },
                        ) {
                            Text("Refresh read-back")
                        }
                        syncQueuedAt?.let {
                            Text("Sync queued: $it", style = MaterialTheme.typography.bodySmall)
                        }
                        HorizontalDivider()
                        when {
                            loading -> Text("Reading local DPC state…")
                            snapshot == null -> Text("No DPC snapshot available")
                            else -> LazyColumn(
                                modifier = Modifier.fillMaxSize(),
                                contentPadding = PaddingValues(bottom = 24.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                items(snapshot!!.lines) { line -> Text(line) }
                            }
                        }
                    }
                }
            }
        }
    }
}

private data class DemoSnapshot(val lines: List<String>) {
    companion object {
        suspend fun load(activity: Activity): DemoSnapshot {
            val context = activity.applicationContext
            val database = DpcDatabase.getDatabase(context)
            val dao = database.dpcDao()
            val dpm = context.getSystemService(DevicePolicyManager::class.java)
            val admin = ComponentName(context, AdminReceiver::class.java)
            val identity = dao.getActiveDeviceIdentity()
            val activePolicy = dao.getActivePolicyEnvelope()
            val policyState = dao.getPolicyState()
            val audit = AuditChain(context)
            val restrictions = if (dpm.isDeviceOwnerApp(context.packageName)) {
                dpm.getUserRestrictions(admin)
            } else {
                null
            }
            val policyJson = activePolicy?.payloadJson?.let(::JSONObject)
            val networkRestrictionKeys: Set<String> = policyJson?.let { root ->
                runCatching {
                    NetworkSettings.fromPayload(root)
                        ?.restrictions(android.os.Build.VERSION.SDK_INT)
                        ?.keys
                        ?.toSet()
                }.getOrNull() ?: emptySet()
            } ?: emptySet()
            val enabledRestrictions = restrictions?.let { bundle ->
                (DeviceRestrictionSettings.allUserRestrictions() + networkRestrictionKeys)
                    .filter { bundle.getBoolean(it, false) }
                    .sorted()
            } ?: emptyList()
            val modes = policyJson?.optJSONArray("modes")
            val defaultModeId = policyJson?.optString("default_mode").orEmpty()
            val defaultMode = (0 until (modes?.length() ?: 0))
                .map { modes!!.optJSONObject(it) }
                .firstOrNull { it?.optString("mode_id") == defaultModeId }
            val blockedCount = defaultMode?.optJSONArray("blocked_packages")?.length() ?: 0
            val lockTaskCount = defaultMode?.optJSONArray("lock_task_packages")?.length() ?: 0
            val owner = dpm.isDeviceOwnerApp(context.packageName)
            val alwaysOnVpn = runCatching { dpm.getAlwaysOnVpnPackage(admin) }.getOrNull()

            return DemoSnapshot(
                listOf(
                    "DPC package: ${context.packageName}",
                    "Device Owner: $owner",
                    "Enrollment state: ${EnrollmentBootstrapCoordinator.state(context)}",
                    "Device UUID: ${identity?.deviceUuid ?: "not enrolled"}",
                    "API origin: ${identity?.apiOrigin ?: "not enrolled"}",
                    "Policy state: ${policyState?.applyState ?: "none"}",
                    "Active policy revision: ${policyState?.activeRevisionUuid ?: "none"}",
                    "Desired hash: ${policyState?.desiredHash ?: "none"}",
                    "Applied hash: ${policyState?.appliedHash ?: "none"}",
                    "Default mode: ${defaultModeId.ifBlank { "none" }}",
                    "Blocked packages in mode: $blockedCount",
                    "Lock-task packages in mode: $lockTaskCount",
                    "Enabled DevicePolicyManager restrictions: ${enabledRestrictions.ifEmpty { listOf("none") }.joinToString(", ")}",
                    "Camera disabled: ${if (owner) dpm.getCameraDisabled(admin) else "not readable"}",
                    "Screen capture disabled: ${if (owner) dpm.getScreenCaptureDisabled(admin) else "not readable"}",
                    "Maximum lock timeout (ms): ${if (owner) dpm.getMaximumTimeToLock(admin) else "not readable"}",
                    "This app lock-task permitted: ${if (owner) dpm.isLockTaskPermitted(context.packageName) else "not readable"}",
                    "Always-on VPN package: ${alwaysOnVpn ?: "none or not readable"}",
                    "Pending audit outbox: ${dao.hasPendingOutbox()}",
                    "Audit chain valid: ${audit.verifyChain()}",
                    "Last audit sequence: ${audit.lastSequence()}",
                ),
            )
        }
    }
}
