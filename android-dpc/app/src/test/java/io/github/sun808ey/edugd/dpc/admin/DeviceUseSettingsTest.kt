package io.github.sun808ey.edugd.dpc.admin

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceUseSettingsTest {
    @Test
    fun `parses iteration one settings`() {
        val settings = DeviceUseSettings.fromPayloadJson("""
            {"device_use":{"mode":"dedicated_learning","kiosk_mode_enabled":true,"display_school_name":true,"school_name":"Example School","support_message":"Contact the ICT office"}}
        """.trimIndent())

        assertEquals("dedicated_learning", settings.mode)
        assertTrue(settings.kioskModeEnabled)
        assertTrue(settings.displaySchoolName)
        assertEquals("Example School", settings.schoolName)
        assertEquals("Contact the ICT office", settings.supportMessage)
    }

    @Test
    fun `legacy payloads default to non-kiosk settings`() {
        val settings = DeviceUseSettings.fromPayloadJson("{}")

        assertEquals("normal_managed", settings.mode)
        assertFalse(settings.kioskModeEnabled)
        assertFalse(settings.displaySchoolName)
        assertEquals(null, settings.schoolName)
        assertEquals(null, settings.supportMessage)
    }
}
