package io.github.sun808ey.edugd.dpc.policy

import java.time.ZoneId
import java.time.ZonedDateTime
import org.json.JSONArray
import org.json.JSONObject

object ScheduleResolver {
    fun resolveModeId(payload: JSONObject, now: ZonedDateTime = ZonedDateTime.now(zoneFor(payload))): String {
        val defaultMode = payload.optString("default_mode")
        val schedules = payload.optJSONArray("schedules") ?: return defaultMode
        val day = now.dayOfWeek.value
        val minute = now.hour * 60 + now.minute
        var selectedMode = defaultMode
        var selectedPriority = Int.MIN_VALUE
        for (index in 0 until schedules.length()) {
            val schedule = schedules.optJSONObject(index) ?: continue
            val start = schedule.optInt("start_minute", -1)
            val end = schedule.optInt("end_minute", -1)
            val days = schedule.optJSONArray("days") ?: continue
            val matches = if (start <= end) {
                containsDay(days, day) && minute >= start && minute < end
            } else {
                (containsDay(days, day) && minute >= start) ||
                    (containsDay(days, previousDay(day)) && minute < end)
            }
            val priority = schedule.optInt("priority", 0)
            if (matches && priority >= selectedPriority) {
                selectedMode = schedule.optString("mode_id", defaultMode)
                selectedPriority = priority
            }
        }
        return selectedMode
    }

    fun zoneFor(payload: JSONObject): ZoneId = runCatching {
        ZoneId.of(payload.optString("timezone", "Africa/Kampala"))
    }.getOrDefault(ZoneId.of("Africa/Kampala"))

    private fun containsDay(days: JSONArray, day: Int): Boolean =
        (0 until days.length()).any { days.optInt(it, -1) == day }

    private fun previousDay(day: Int): Int = if (day == 1) 7 else day - 1
}
