package io.github.sun808ey.edugd.dpc.admin

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.assertThrows
import org.junit.Test

class ScreenLockSettingsTest {
    @Test
    fun parsesRecommendedSharedDeviceSettings() {
        val settings = ScreenLockSettings.fromPayloadJson(
            """
            {
              "screen_lock": {
                "require_screen_lock": true,
                "automatic_lock_after_minutes": 5,
                "allow_biometric_unlock": false,
                "allow_learner_change_lock_method": false
              }
            }
            """.trimIndent()
        )

        requireNotNull(settings)
        assertTrue(settings.requireScreenLock)
        assertEquals(5 * 60_000L, settings.automaticLockAfterMillis())
        assertFalse(settings.allowBiometricUnlock)
        assertFalse(settings.allowLearnerChangeLockMethod)
    }

    @Test
    fun invalidTimeoutIsRejectedBeforeApplication() {
        assertThrows(IllegalArgumentException::class.java) {
            ScreenLockSettings.fromPayloadJson(
                """
                {
                  "screen_lock": {
                    "require_screen_lock": true,
                    "automatic_lock_after_minutes": 2,
                    "allow_biometric_unlock": false,
                    "allow_learner_change_lock_method": false
                  }
                }
                """.trimIndent()
            )
        }
    }

    @Test
    fun legacyPayloadDoesNotAddScreenLockPolicy() {
        assertNull(ScreenLockSettings.fromPayloadJson("{}"))
    }
}
