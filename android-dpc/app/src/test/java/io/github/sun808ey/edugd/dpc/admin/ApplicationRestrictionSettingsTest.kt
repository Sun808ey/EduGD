package io.github.sun808ey.edugd.dpc.admin

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class ApplicationRestrictionSettingsTest {
    @Test
    fun `parses iteration three application restrictions and package evidence`() {
        val settings = ApplicationRestrictionSettings.fromPayloadJson(
            """
                {
                  "approved_applications": [
                    {"package_name": "org.example.learning"}
                  ],
                  "application_controls": {
                    "allow_installation_of_other_applications": false,
                    "allow_installation_from_unknown_sources": false,
                    "allow_uninstall_of_approved_applications": false,
                    "allow_disable_of_approved_applications": false,
                    "allow_google_play_store": false,
                    "allow_file_sharing_applications": false,
                    "file_sharing_packages": ["com.example.fileshare"]
                  }
                }
                """.trimIndent(),
        )

        requireNotNull(settings)
        assertFalse(settings.allowInstallationOfOtherApplications)
        assertFalse(settings.allowInstallationFromUnknownSources)
        assertFalse(settings.allowUninstallOfApprovedApplications)
        assertFalse(settings.allowDisableOfApprovedApplications)
        assertFalse(settings.allowGooglePlayStore)
        assertFalse(settings.allowFileSharingApplications)
        assertEquals(setOf("org.example.learning"), settings.approvedApplicationPackages)
        assertEquals(setOf("com.example.fileshare"), settings.fileSharingPackages)
    }

    @Test
    fun `legacy payloads do not activate iteration three restrictions`() {
        assertNull(ApplicationRestrictionSettings.fromPayloadJson("{}"))
    }
}
