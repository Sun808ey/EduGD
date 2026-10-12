package io.github.sun808ey.edugd.dpc.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import io.github.sun808ey.edugd.dpc.policy.AtomicPolicyActivator

class ScheduleWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = runCatching {
        AtomicPolicyActivator(applicationContext).reconcileScheduledMode()
        Result.success()
    }.getOrElse { Result.retry() }
}
