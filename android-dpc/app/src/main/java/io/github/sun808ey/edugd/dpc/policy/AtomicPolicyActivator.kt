package io.github.sun808ey.edugd.dpc.policy

import android.content.Context
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController
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
    val lockTaskPackages: List<String>
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
                    currentModeId = "school",
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
            val active = dao.getActivePolicyEnvelope()
            if (active != null) {
                val payload = JSONObject(active.payloadJson)
                val mode = payload.optJSONArray("modes")?.let { modes ->
                    (0 until modes.length()).map { modes.getJSONObject(it) }
                        .firstOrNull { it.optString("mode_id") == payload.optString("default_mode") }
                }
                val blocked = (0 until (mode?.optJSONArray("blocked_packages")?.length() ?: 0)).map { mode!!.getJSONArray("blocked_packages").getString(it) }
                dpc.clearManagedPackages(blocked)
                dao.updatePolicyStatus(active.policyUuid, "CLEARED")
            } else dpc.clearManagedPackages(emptyList())
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
        return SignedEnvelope(envelope.policyUuid, envelope.revisionUuid, envelope.payloadJson, envelope.payloadSha256, envelope.signature, envelope.signingKeyId, envelope.issuedAt, blocked, lockTask)
    }

    suspend fun reconcilePendingApplyAtBoot() = withContext(Dispatchers.IO) {
        val state = dao.getPolicyState()
        if (state != null && state.applyState == "PENDING_APPLY") {
            auditChain.appendEvent(eventCode = "check_in", metadata = mapOf("desired_hash" to state.desiredHash))
        }
    }
}
