package io.github.sun808ey.edugd.dpc.policy

import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime
import org.json.JSONObject

data class ScreenTimeSettings(
    val dailyLimitMinutes: Int,
    val resetMinute: Int,
    val exhaustedModeId: String,
    val targetPackages: Set<String>,
) {
    companion object {
        fun fromPayload(payload: JSONObject): ScreenTimeSettings? {
            val value = if (payload.has("screen_time")) payload.getJSONObject("screen_time") else return null
            val targets = if (value.has("target_packages")) value.getJSONArray("target_packages").let { packages ->
                (0 until packages.length())
                    .mapNotNull { packages.optString(it).takeIf(String::isNotBlank) }
                    .toSet()
            } else emptySet()
            val limit = value.optInt("daily_limit_minutes", -1)
            val reset = value.optInt("reset_minute", -1)
            val exhausted = value.optString("exhausted_mode_id")
            require(limit in 1..1440) { "invalid daily screen-time limit" }
            require(reset in 0..1439) { "invalid screen-time reset minute" }
            require(exhausted.isNotBlank()) { "missing screen-time exhausted mode" }
            return ScreenTimeSettings(limit, reset, exhausted, targets)
        }
    }
}

data class ScreenTimeWindow(
    val usageDate: LocalDate,
    val start: ZonedDateTime,
    val end: ZonedDateTime,
)

object ScreenTimeWindowResolver {
    fun current(settings: ScreenTimeSettings, zone: ZoneId, now: ZonedDateTime): ScreenTimeWindow {
        val localNow = now.withZoneSameInstant(zone)
        val todayReset = localNow.toLocalDate().atStartOfDay(zone)
            .plusMinutes(settings.resetMinute.toLong())
        val start = if (localNow >= todayReset) todayReset else todayReset.minusDays(1)
        return ScreenTimeWindow(start.toLocalDate(), start, localNow)
    }
}

object ScreenTimeUsageCalculator {
    fun activeMinutes(totalForegroundMillis: Long): Int {
        require(totalForegroundMillis >= 0) { "foreground usage cannot be negative" }
        if (totalForegroundMillis == 0L) return 0
        return ((totalForegroundMillis + 59_999L) / 60_000L)
            .coerceAtMost(Int.MAX_VALUE.toLong())
            .toInt()
    }

    fun totalTargetMinutes(
        foregroundMillisByPackage: Map<String, Long>,
        targets: Set<String>,
    ): Int = targets.sumOf { activeMinutes(foregroundMillisByPackage[it] ?: 0L) }
}
