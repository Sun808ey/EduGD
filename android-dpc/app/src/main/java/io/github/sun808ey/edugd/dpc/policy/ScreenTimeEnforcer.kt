package io.github.sun808ey.edugd.dpc.policy

import android.app.AppOpsManager
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.Process
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController
import io.github.sun808ey.edugd.dpc.audit.AuditChain
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.db.ScreenTimeStateEntity
import io.github.sun808ey.edugd.dpc.db.ScreenTimeUsageEntity
import java.time.ZonedDateTime
import org.json.JSONObject

class ScreenTimeEnforcer(private val context: Context) {
    private val database = DpcDatabase.getDatabase(context)
    private val dao = database.dpcDao()
    private val dpc = DevicePolicyController(context)
    private val auditChain = AuditChain(context)
    private val usageStats = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager

    suspend fun reconcile(
        payload: JSONObject,
        policyRevisionUuid: String,
        blockedPackages: Set<String> = emptySet(),
        now: ZonedDateTime = ZonedDateTime.now(),
    ) {
        val settings = ScreenTimeSettings.fromPayload(payload) ?: return
        val zone = ScheduleResolver.zoneFor(payload)
        val window = ScreenTimeWindowResolver.current(settings, zone, now)
        val targets = settings.targetPackages
        if (targets.isEmpty()) return
        if (!hasUsageStatsAccess()) {
            auditChain.appendEvent(
                eventCode = "sync_failure",
                policyUuid = payload.optString("policy_uuid").takeIf(String::isNotBlank),
                revisionUuid = policyRevisionUuid,
                metadata = mapOf("reason" to "screen_time_usage_access_unavailable"),
            )
            return
        }

        val usage = usageStats.queryAndAggregateUsageStats(
            window.start.toInstant().toEpochMilli(),
            window.end.toInstant().toEpochMilli(),
        ).mapValues { (_, stats) -> stats.totalTimeInForeground }
        val minutesByPackage = targets.associateWith { packageName ->
            ScreenTimeUsageCalculator.activeMinutes(usage[packageName] ?: 0L)
        }
        minutesByPackage.forEach { (packageName, activeMinutes) ->
            dao.insertScreenTimeUsage(
                ScreenTimeUsageEntity(
                    policyRevisionUuid,
                    window.usageDate.toString(),
                    packageName,
                    activeMinutes,
                    System.currentTimeMillis(),
                ),
            )
        }
        val totalMinutes = minutesByPackage.values.sum()
        val exhausted = totalMinutes >= settings.dailyLimitMinutes
        val previous = dao.getScreenTimeState(policyRevisionUuid, window.usageDate.toString())
        val manageableTargets = targets - blockedPackages - context.packageName
        dpc.setScreenTimePackagesSuspended(
            manageableTargets,
            exhausted,
            blockedPackages + context.packageName,
        )
        dao.insertScreenTimeState(
            ScreenTimeStateEntity(
                policyRevisionUuid,
                window.usageDate.toString(),
                totalMinutes,
                exhausted,
                System.currentTimeMillis(),
            ),
        )
        if (exhausted && previous?.exhausted != true) {
            auditChain.appendEvent(
                eventCode = "screen_time_exhausted",
                policyUuid = payload.optString("policy_uuid").takeIf(String::isNotBlank),
                revisionUuid = policyRevisionUuid,
                metadata = mapOf(
                    "active_minutes" to totalMinutes.toString(),
                    "target_count" to targets.size.toString(),
                ),
            )
        }
    }

    suspend fun clear(payload: JSONObject, policyRevisionUuid: String) {
        val settings = ScreenTimeSettings.fromPayload(payload) ?: return
        if (settings.targetPackages.isNotEmpty()) {
            dpc.setScreenTimePackagesSuspended(
                settings.targetPackages - context.packageName,
                false,
                setOf(context.packageName),
            )
        }
        dao.deleteScreenTimeUsage(policyRevisionUuid)
        dao.deleteScreenTimeState(policyRevisionUuid)
    }

    private fun hasUsageStatsAccess(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            Process.myUid(),
            context.packageName,
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }
}
