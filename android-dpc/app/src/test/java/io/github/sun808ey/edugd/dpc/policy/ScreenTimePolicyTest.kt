package io.github.sun808ey.edugd.dpc.policy

import java.time.ZoneId
import java.time.ZonedDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenTimePolicyTest {
    @Test
    fun `stores explicit target packages and preserves legacy empty targets`() {
        val settings = ScreenTimeSettings(120, 30, "restricted", setOf("com.example.social", "com.example.games"))

        assertEquals(setOf("com.example.social", "com.example.games"), settings.targetPackages)
        assertEquals(emptySet<String>(), ScreenTimeSettings(120, 0, "restricted", emptySet()).targetPackages)
    }

    @Test
    fun `resolves reset window before and after reset minute`() {
        val settings = ScreenTimeSettings(120, 30, "restricted", emptySet())
        val zone = ZoneId.of("Africa/Kampala")
        val before = ScreenTimeWindowResolver.current(settings, zone, ZonedDateTime.of(2026, 10, 14, 0, 20, 0, 0, zone))
        val after = ScreenTimeWindowResolver.current(settings, zone, ZonedDateTime.of(2026, 10, 14, 0, 31, 0, 0, zone))

        assertEquals("2026-10-13", before.usageDate.toString())
        assertEquals("2026-10-14", after.usageDate.toString())
    }

    @Test
    fun `rounds foreground usage conservatively and totals only targets`() {
        assertEquals(1, ScreenTimeUsageCalculator.activeMinutes(1))
        assertEquals(2, ScreenTimeUsageCalculator.activeMinutes(60_001))
        assertEquals(3, ScreenTimeUsageCalculator.totalTargetMinutes(mapOf("a" to 60_000L, "b" to 120_000L), setOf("a", "b")))
        assertTrue(ScreenTimeUsageCalculator.totalTargetMinutes(mapOf("other" to 600_000L), setOf("a")) == 0)
    }
}
