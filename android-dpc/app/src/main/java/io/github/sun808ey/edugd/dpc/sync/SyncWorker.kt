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

class TransientSyncException(val safeCode: String, message: String) : Exception(message)
class PermanentSyncException(val safeCode: String, message: String) : Exception(message)
class CredentialRevokedException : Exception()

class DpcGraph(val context: Context, val repository: PolicyRepository, val stateSyncClient: StateSyncClient) {
    companion object {
        suspend fun from(context: Context): DpcGraph? {
            val appContext = context.applicationContext
            val enrollment = DpcDatabase.getDatabase(appContext).dpcDao().getActiveDeviceIdentity() ?: return null
            val identity = DeviceKeyStore().getOrCreate(enrollment.keyAlias)
            return DpcGraph(appContext, PolicyRepository(appContext), StateSyncClient(enrollment.apiOrigin, enrollment.deviceUuid, enrollment.credentialUuid, identity))
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
            graph.stateSyncClient.fetchState()
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
