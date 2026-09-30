package io.github.sun808ey.edugd.dpc.sync

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.NetworkType
import androidx.work.WorkerParameters
import io.github.sun808ey.edugd.dpc.crypto.DeviceKeyStore
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import io.github.sun808ey.edugd.dpc.policy.PolicyRepository

class TransientSyncException(val safeCode: String, message: String) : Exception(message)
class PermanentSyncException(val safeCode: String, message: String) : Exception(message)

class DpcGraph(
    val context: Context,
    val repository: PolicyRepository,
    val stateSyncClient: StateSyncClient
) {
    companion object {
        fun from(context: Context): DpcGraph {
            val appCtx = context.applicationContext
            val identity = DeviceKeyStore().getOrCreate()
            return DpcGraph(
                context = appCtx,
                repository = PolicyRepository(appCtx),
                stateSyncClient = StateSyncClient("https://api.edugd.example.com", "device_001", "credential_001", identity)
            )
        }
    }
}

class SyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val cm = applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork
        val caps = cm.getNetworkCapabilities(network)
        val isWifi = caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true

        if (!isWifi) {
            return Result.retry()
        }

        val graph = DpcGraph.from(applicationContext)
        return try {
            graph.stateSyncClient.fetchState()
            Result.success()
        } catch (error: TransientSyncException) {
            graph.repository.lastPolicyVersion = -1L
            Result.retry()
        } catch (error: PermanentSyncException) {
            graph.repository.lastPolicyVersion = -99L
            Result.failure()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    companion object {
        fun constraints() = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.UNMETERED)
            .build()
    }
}
