package io.github.sun808ey.edugd.dpc.policy

import android.content.Context
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController
import io.github.sun808ey.edugd.dpc.admin.ApplicationRestrictionSettings
import io.github.sun808ey.edugd.dpc.admin.DeviceRestrictionSettings
import io.github.sun808ey.edugd.dpc.admin.ScreenLockSettings
import io.github.sun808ey.edugd.dpc.admin.NetworkSettings
import io.github.sun808ey.edugd.dpc.admin.OfflinePolicySettings
import io.github.sun808ey.edugd.dpc.admin.DeviceUseSettings
import io.github.sun808ey.edugd.dpc.audit.AuditChain
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.db.PolicyEnvelopeEntity
import io.github.sun808ey.edugd.dpc.db.PolicyStateEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class SignedEnvelope(
    val policyUuid: String,
    val revisionUuid: String,
    val payloadJson: String,
    val payloadSha256: String,
    val signature: String,
    val signingKeyId: String,
    val issuedAt: Long,
    val suspendedPackages: List<String>,
    val lockTaskPackages: List<String>,
    val deviceUse: DeviceUseSettings = DeviceUseSettings(),
    val applicationRestrictions: ApplicationRestrictionSettings? = null,
    val deviceRestrictions: DeviceRestrictionSettings? = null,
    val screenLock: ScreenLockSettings? = null,
    val networkSettings: NetworkSettings? = null,
    val offlineSettings: OfflinePolicySettings? = null,
)

sealed class ApplyResult {
    object Active : ApplyResult()
    data class Quarantined(val reason: String) : ApplyResult()
}

class AtomicPolicyActivator(private val context: Context) {
    private val db = DpcDatabase.getDatabase(context)
    private val dao = db.dpcDao()
    private val dpc = DevicePolicyController(context)
    private val auditChain = AuditChain(context)

    suspend fun activate(envelope: SignedEnvelope): ApplyResult = withContext(Dispatchers.IO) {
        try {
            envelope.offlineSettings?.let { require(!it.expirePolicyWhenOffline) }
            envelope.networkSettings?.let { dpc.validateNetworkSettings(it) }
            val previous = dao.getActivePolicyEnvelope()
            dao.getActivePolicyEnvelope()?.let { dao.updatePolicyStatus(it.policyUuid, "SUPERSEDED") }
            dao.insertPolicyEnvelope(
                PolicyEnvelopeEntity(
                    policyUuid = envelope.policyUuid,
                    revisionUuid = envelope.revisionUuid,
                    payloadJson = envelope.payloadJson,
                    payloadSha256 = envelope.payloadSha256,
                    signature = envelope.signature,
                    signingKeyId = envelope.signingKeyId,
                    issuedAt = envelope.issuedAt,
                    verifiedAt = System.currentTimeMillis(),
                    status = "PENDING"
                )
            )
            dao.insertPolicyState(
                PolicyStateEntity(
                    currentModeId = ScheduleResolver.resolveModeId(JSONObject(envelope.payloadJson)),
                    activePolicyUuid = null,
                    activeRevisionUuid = null,
                    desiredHash = envelope.payloadSha256,
                    appliedHash = "",
                    applyState = "PENDING_APPLY",
                    lastServerTime = System.currentTimeMillis()
                )
            )

            dpc.setPackagesSuspended(envelope.suspendedPackages, true)
            dpc.setLockTaskPackages(envelope.lockTaskPackages)
            dpc.applyDeviceUseSettings(envelope.deviceUse)
            dpc.clearApplicationRestrictions(
                previous?.let { ApplicationRestrictionSettings.fromPayload(JSONObject(it.payloadJson)) }
            )
            dpc.clearNetworkSettings()
            dpc.clearDeviceRestrictions()
            envelope.applicationRestrictions?.let { dpc.applyApplicationRestrictions(it) }
            envelope.deviceRestrictions?.let { dpc.applyDeviceRestrictions(it) }
            dpc.clearScreenLock()
            envelope.screenLock?.let { dpc.applyScreenLock(it) }
            envelope.networkSettings?.let { dpc.applyNetworkSettings(it) }

            auditChain.appendEvent(
                eventCode = "policy_applied",
                policyUuid = envelope.policyUuid,
                revisionUuid = envelope.revisionUuid
            )

            dao.markActive(
                applyState = "ACTIVE",
                appliedHash = envelope.payloadSha256,
                policyUuid = envelope.policyUuid,
                revisionUuid = envelope.revisionUuid
            )

            ApplyResult.Active
        } catch (e: Exception) {
            e.printStackTrace()
            ApplyResult.Quarantined(e.message ?: "activation_failed")
        }
    }

    suspend fun clear(): ApplyResult = withContext(Dispatchers.IO) {
        try {
            dpc.clearNetworkSettings()
            val active = dao.getActivePolicyEnvelope()
            if (active != null) {
                val payload = JSONObject(active.payloadJson)
                val mode = payload.optJSONArray("modes")?.let { modes ->
                    (0 until modes.length()).map { modes.getJSONObject(it) }
                        .firstOrNull { it.optString("mode_id") == payload.optString("default_mode") }
                }
                val blocked = (0 until (mode?.optJSONArray("blocked_packages")?.length() ?: 0)).map { mode!!.getJSONArray("blocked_packages").getString(it) }
                dpc.clearManagedPackages(blocked)
                dpc.clearDeviceUseSettings()
                dpc.clearApplicationRestrictions(ApplicationRestrictionSettings.fromPayload(payload))
                dpc.clearDeviceRestrictions()
                dpc.clearScreenLock()
                dao.updatePolicyStatus(active.policyUuid, "CLEARED")
            } else {
                dpc.clearManagedPackages(emptyList())
                dpc.clearDeviceUseSettings()
                dpc.clearApplicationRestrictions()
                dpc.clearDeviceRestrictions()
                dpc.clearScreenLock()
            }
            dao.insertPolicyState(PolicyStateEntity(currentModeId = "none", activePolicyUuid = null, activeRevisionUuid = null, desiredHash = "", appliedHash = "", applyState = "CLEARED", lastServerTime = System.currentTimeMillis()))
            ApplyResult.Active
        } catch (e: Exception) { ApplyResult.Quarantined(e.message ?: "clear_failed") }
    }

    suspend fun rollback(): ApplyResult = withContext(Dispatchers.IO) {
        val active = dao.getActivePolicyEnvelope() ?: return@withContext clear()
        val previous = dao.getRollbackEnvelope(active.policyUuid) ?: return@withContext clear()
        activate(envelopeFrom(previous))
    }

    private fun envelopeFrom(envelope: PolicyEnvelopeEntity): SignedEnvelope {
        val payload = JSONObject(envelope.payloadJson)
        val mode = payload.optJSONArray("modes")?.let { modes ->
            (0 until modes.length()).map { modes.getJSONObject(it) }
                .firstOrNull { it.optString("mode_id") == payload.optString("default_mode") }
        }
        val blocked = (0 until (mode?.optJSONArray("blocked_packages")?.length() ?: 0)).map { mode!!.getJSONArray("blocked_packages").getString(it) }
        val lockTask = (0 until (mode?.optJSONArray("lock_task_packages")?.length() ?: 0)).map { mode!!.getJSONArray("lock_task_packages").getString(it) }
        return SignedEnvelope(
            envelope.policyUuid,
            envelope.revisionUuid,
            envelope.payloadJson,
            envelope.payloadSha256,
            envelope.signature,
            envelope.signingKeyId,
            envelope.issuedAt,
            blocked,
            lockTask,
            DeviceUseSettings.fromPayload(payload),
            ApplicationRestrictionSettings.fromPayload(payload),
            DeviceRestrictionSettings.fromPayload(payload),
            ScreenLockSettings.fromPayload(payload),
            NetworkSettings.fromPayload(payload),
            OfflinePolicySettings.fromPayload(payload),
        )
    }

    suspend fun reconcilePendingApplyAtBoot() = withContext(Dispatchers.IO) {
        val state = dao.getPolicyState()
        if (state != null && state.applyState == "PENDING_APPLY") {
            auditChain.appendEvent(eventCode = "check_in", metadata = mapOf("desired_hash" to state.desiredHash))
        }
    }

    suspend fun reconcileScheduledMode() = withContext(Dispatchers.IO) {
        val active = dao.getActivePolicyEnvelope() ?: return@withContext
        val payload = JSONObject(active.payloadJson)
        val desiredModeId = ScheduleResolver.resolveModeId(payload)
        val currentState = dao.getPolicyState() ?: return@withContext
        if (currentState.currentModeId == desiredModeId) return@withContext
        val modes = payload.optJSONArray("modes") ?: return@withContext
        val currentMode = modeFor(modes, currentState.currentModeId)
        val desiredMode = modeFor(modes, desiredModeId) ?: return@withContext
        val previousBlocked = packagesFrom(currentMode, "blocked_packages")
        val desiredBlocked = packagesFrom(desiredMode, "blocked_packages")
        dpc.setPackagesSuspended(previousBlocked, false)
        dpc.setPackagesSuspended(desiredBlocked, true)
        dpc.setLockTaskPackages(packagesFrom(desiredMode, "lock_task_packages"))
        dao.insertPolicyState(currentState.copy(currentModeId = desiredModeId, lastServerTime = System.currentTimeMillis()))
        auditChain.appendEvent(
            eventCode = "policy_applied",
            policyUuid = active.policyUuid,
            revisionUuid = active.revisionUuid,
            metadata = mapOf("mode_id" to desiredModeId),
        )
    }

    private fun modeFor(modes: org.json.JSONArray, modeId: String): org.json.JSONObject? =
        (0 until modes.length()).mapNotNull { modes.optJSONObject(it) }.firstOrNull { it.optString("mode_id") == modeId }

    private fun packagesFrom(mode: org.json.JSONObject?, key: String): List<String> {
        val packages = mode?.optJSONArray(key) ?: return emptyList()
        return (0 until packages.length()).mapNotNull { packages.optString(it).takeIf(String::isNotBlank) }
    }
}
