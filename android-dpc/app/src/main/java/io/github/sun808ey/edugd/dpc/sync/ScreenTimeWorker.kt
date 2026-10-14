package io.github.sun808ey.edugd.dpc.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.policy.ScreenTimeEnforcer
import org.json.JSONObject

class ScreenTimeWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = runCatching {
        val dao = DpcDatabase.getDatabase(applicationContext).dpcDao()
        val active = dao.getActivePolicyEnvelope() ?: return Result.success()
        val state = dao.getPolicyState()
        val payload = JSONObject(active.payloadJson)
        val modes = payload.optJSONArray("modes")
        val mode = (0 until (modes?.length() ?: 0))
            .mapNotNull { modes?.optJSONObject(it) }
            .firstOrNull { it.optString("mode_id") == state?.currentModeId }
        val blocked = (0 until (mode?.optJSONArray("blocked_packages")?.length() ?: 0))
            .map { mode!!.getJSONArray("blocked_packages").getString(it) }
            .toSet()
        ScreenTimeEnforcer(applicationContext).reconcile(payload, active.revisionUuid, blocked)
        Result.success()
    }.getOrElse { Result.retry() }
}
