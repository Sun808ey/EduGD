package io.github.sun808ey.edugd.dpc.sync

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.OneTimeWorkRequestBuilder
import java.util.concurrent.TimeUnit

object SyncScheduler {
    const val IMMEDIATE_WORK = "edugd-immediate-sync"
    const val PERIODIC_WORK = "edugd-periodic-sync"

    fun schedule(context: Context) {
        val manager = WorkManager.getInstance(context.applicationContext)
        val immediate = OneTimeWorkRequestBuilder<SyncWorker>().setConstraints(SyncWorker.constraints()).build()
        val periodic = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES).setConstraints(SyncWorker.constraints()).build()
        manager.enqueueUniqueWork(IMMEDIATE_WORK, ExistingWorkPolicy.KEEP, immediate)
        manager.enqueueUniquePeriodicWork(PERIODIC_WORK, ExistingPeriodicWorkPolicy.KEEP, periodic)
    }
    fun cancel(context: Context) {
        val manager = WorkManager.getInstance(context.applicationContext)
        manager.cancelUniqueWork(IMMEDIATE_WORK); manager.cancelUniqueWork(PERIODIC_WORK)
    }
}
