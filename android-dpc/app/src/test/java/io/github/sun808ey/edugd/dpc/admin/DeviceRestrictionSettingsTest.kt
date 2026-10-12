package io.github.sun808ey.edugd.dpc.admin

import android.os.UserManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceRestrictionSettingsTest {
    @Test
    fun parsesSecurityAndPrivacyControls() {
        val settings = DeviceRestrictionSettings.fromPayloadJson(
            """
            {
              "device_restrictions": {
                "block_factory_reset": true,
                "block_safe_mode": true,
                "block_developer_options_and_debugging": true,
                "block_usb_file_transfer": true,
                "block_account_changes": true,
                "block_user_switching": true,
                "block_network_reset": false,
                "block_wifi_changes": false,
                "disable_screenshots": true,
                "disable_screen_recording": false,
                "disable_camera": true,
                "disable_microphone": true,
                "disable_location": true
              }
            }
            """.trimIndent()
        )

        requireNotNull(settings)
        assertTrue(settings.blockFactoryReset)
        assertTrue(settings.blockDeveloperOptionsAndDebugging)
        assertTrue(settings.disableCamera)
        assertTrue(settings.disableMicrophone)
        assertTrue(settings.disableLocation)
        assertTrue(settings.screenCaptureDisabled())
        assertEquals(
            setOf(
                UserManager.DISALLOW_FACTORY_RESET,
                UserManager.DISALLOW_SAFE_BOOT,
                UserManager.DISALLOW_DEBUGGING_FEATURES,
                UserManager.DISALLOW_USB_FILE_TRANSFER,
                UserManager.DISALLOW_MODIFY_ACCOUNTS,
                UserManager.DISALLOW_USER_SWITCH,
                UserManager.DISALLOW_UNMUTE_MICROPHONE,
                UserManager.DISALLOW_CONFIG_LOCATION,
            ),
            settings.userRestrictions(),
        )
    }

    @Test
    fun keepsNetworkRecoveryAndCaptureAllowedByRecommendedDefaults() {
        val settings = DeviceRestrictionSettings.fromPayloadJson(
            """
            {
              "device_restrictions": {
                "block_factory_reset": true,
                "block_safe_mode": true,
                "block_developer_options_and_debugging": true,
                "block_usb_file_transfer": true,
                "block_account_changes": true,
                "block_user_switching": true,
                "block_network_reset": false,
                "block_wifi_changes": false,
                "disable_screenshots": false,
                "disable_screen_recording": false,
                "disable_camera": false,
                "disable_microphone": false,
                "disable_location": false
              }
            }
            """.trimIndent()
        )

        requireNotNull(settings)
        assertFalse(settings.blockNetworkReset)
        assertFalse(settings.blockWifiChanges)
        assertFalse(settings.screenCaptureDisabled())
        assertTrue(UserManager.DISALLOW_CONFIG_WIFI !in settings.userRestrictions())
    }

    @Test
    fun legacyPayloadDoesNotAddDeviceRestrictions() {
        assertNull(DeviceRestrictionSettings.fromPayloadJson("{}"))
    }
}
