package io.github.sun808ey.edugd.dpc.sync

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.NetworkType
import androidx.work.WorkerParameters
import io.github.sun808ey.edugd.dpc.crypto.DeviceKeyStore
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.policy.PolicyRepository
import io.github.sun808ey.edugd.dpc.policy.AtomicPolicyActivator
import io.github.sun808ey.edugd.dpc.policy.SignedEnvelope

class TransientSyncException(val safeCode: String, message: String) : Exception(message)
class PermanentSyncException(val safeCode: String, message: String) : Exception(message)
class CredentialRevokedException : Exception()

class DpcGraph(val context: Context, val repository: PolicyRepository, val stateSyncClient: StateSyncClient, val trustedSigningKeyId: String) {
    companion object {
        suspend fun from(context: Context): DpcGraph? {
            val appContext = context.applicationContext
            val enrollment = DpcDatabase.getDatabase(appContext).dpcDao().getActiveDeviceIdentity() ?: return null
            val identity = DeviceKeyStore().getOrCreate(enrollment.keyAlias)
            return DpcGraph(appContext, PolicyRepository(appContext), StateSyncClient(enrollment.apiOrigin, enrollment.deviceUuid, enrollment.credentialUuid, identity, enrollment.serverSigningKeyId, enrollment.serverSigningPublicKey, enrollment.lastAcceptedServerTimeEpochSeconds), enrollment.serverSigningKeyId)
        }
    }
}

class SyncWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val manager = applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = manager.getNetworkCapabilities(manager.activeNetwork)
        if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) != true) return Result.retry()
        val graph = DpcGraph.from(applicationContext) ?: return Result.success()
        return try {
            val state = graph.stateSyncClient.fetchState()
            if (state == null) throw TransientSyncException("empty_state", "v3 state response was empty")
            when (state.operation) {
                "apply" -> {
                    val policy = state.policy ?: throw PermanentSyncException("missing_policy", "apply response had no policy")
                    if (policy.optString("signing_key_id") != graph.trustedSigningKeyId) throw PermanentSyncException("policy_key_mismatch", "policy signing key mismatch")
                    val payload = policy.optJSONObject("payload") ?: throw PermanentSyncException("missing_policy_payload", "apply response had no payload")
                    val defaultMode = payload.optString("default_mode")
                    val modes = payload.optJSONArray("modes") ?: throw PermanentSyncException("missing_policy_mode", "policy has no modes")
                    val mode = (0 until modes.length()).asSequence().map { modes.getJSONObject(it) }.firstOrNull { it.optString("mode_id") == defaultMode }
                        ?: throw PermanentSyncException("missing_policy_mode", "default policy mode is missing")
                    val blocked = (0 until (mode.optJSONArray("blocked_packages")?.length() ?: 0)).map { mode.getJSONArray("blocked_packages").getString(it) }
                    val lockTask = (0 until (mode.optJSONArray("lock_task_packages")?.length() ?: 0)).map { mode.getJSONArray("lock_task_packages").getString(it) }
                    val result = AtomicPolicyActivator(applicationContext).activate(SignedEnvelope(policy.getString("policy_uuid"), policy.getString("revision_uuid"), payload.toString(), policy.getString("payload_hash"), policy.getString("signature"), policy.getString("signing_key_id"), System.currentTimeMillis(), blocked, lockTask))
                    when (result) {
                        is io.github.sun808ey.edugd.dpc.policy.ApplyResult.Active -> Unit
                        is io.github.sun808ey.edugd.dpc.policy.ApplyResult.Quarantined -> throw PermanentSyncException("policy_quarantined", "policy application quarantined")
                    }
                    if (!graph.stateSyncClient.acknowledge(policy.getString("policy_uuid"), policy.getString("revision_uuid"), "applied")) throw TransientSyncException("acknowledgement_unavailable", "policy acknowledgement was not accepted")
                }
                "no_change" -> if (!graph.stateSyncClient.acknowledge(null, null, "verified")) throw TransientSyncException("acknowledgement_unavailable", "no-change acknowledgement was not accepted")
                "blocked" -> if (!graph.stateSyncClient.acknowledge(null, null, "rejected", "device_blocked")) throw TransientSyncException("acknowledgement_unavailable", "blocked acknowledgement was not accepted")
                "clear" -> {
                    when (AtomicPolicyActivator(applicationContext).clear()) {
                        is io.github.sun808ey.edugd.dpc.policy.ApplyResult.Active -> if (!graph.stateSyncClient.acknowledge(null, null, "cleared")) throw TransientSyncException("acknowledgement_unavailable", "clear acknowledgement was not accepted")
                        is io.github.sun808ey.edugd.dpc.policy.ApplyResult.Quarantined -> throw PermanentSyncException("clear_failed", "policy clear failed")
                    }
                }
                "rollback" -> {
                    when (AtomicPolicyActivator(applicationContext).rollback()) {
                        is io.github.sun808ey.edugd.dpc.policy.ApplyResult.Active -> if (!graph.stateSyncClient.acknowledge(state.policy?.optString("policy_uuid"), state.policy?.optString("revision_uuid"), "rolled_back")) throw TransientSyncException("acknowledgement_unavailable", "rollback acknowledgement was not accepted")
                        is io.github.sun808ey.edugd.dpc.policy.ApplyResult.Quarantined -> throw PermanentSyncException("rollback_failed", "policy rollback failed")
                    }
                }
                else -> throw PermanentSyncException("unsupported_operation", "unsupported state operation")
            }
            DpcDatabase.getDatabase(applicationContext).dpcDao().updateAcceptedServerTime(state.deviceUuid, state.serverEpochSeconds)
            Result.success()
        } catch (_: CredentialRevokedException) {
            DpcDatabase.getDatabase(applicationContext).dpcDao().markIdentityRevoked()
            SyncScheduler.cancel(applicationContext)
            Result.failure()
        } catch (_: TransientSyncException) { graph.repository.lastPolicyVersion = -1L; Result.retry()
        } catch (_: PermanentSyncException) { graph.repository.lastPolicyVersion = -99L; Result.failure()
        } catch (_: Exception) { Result.retry() }
    }
    companion object { fun constraints() = Constraints.Builder().setRequiredNetworkType(NetworkType.UNMETERED).build() }
}
