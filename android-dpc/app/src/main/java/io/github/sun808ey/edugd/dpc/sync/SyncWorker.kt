package io.github.sun808ey.edugd.dpc.sync

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters

class SyncWorker(appContext: Context, workerParams: WorkerParameters) : Worker(appContext, workerParams) {
    override fun doWork(): Result {
        val client = StateSyncClient("https://api.edugd.example.com", "device_001")
        val response = client.syncState("{\"status\":\"active\"}")
        return if (response != null) Result.success() else Result.retry()
    }
}
