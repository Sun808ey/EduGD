package io.github.sun808ey.edugd.dpc.admin

import android.os.UserManager
import io.github.sun808ey.edugd.dpc.sync.SyncNetworkPolicy
import org.junit.Assert.*
import org.junit.Test

class NetworkSettingsTest {
    private val payload = """{"network_settings":{
        "allow_wifi":true,"allow_mobile_data":true,"allow_bluetooth":false,
        "allow_hotspot_creation":false,"allow_vpn_changes":false,"allow_network_reset":false
    }}"""

    @Test fun defaultsBlockOnlyTheRequestedControls() {
        val settings = NetworkSettings.fromPayloadJson(payload)!!
        settings.validateForApi(29)
        val restrictions = settings.restrictions(29)
        assertTrue(restrictions[UserManager.DISALLOW_BLUETOOTH]!!)
        assertTrue(restrictions[UserManager.DISALLOW_CONFIG_TETHERING]!!)
        assertTrue(restrictions[UserManager.DISALLOW_CONFIG_VPN]!!)
        assertTrue(restrictions[UserManager.DISALLOW_NETWORK_RESET]!!)
        assertFalse(restrictions.containsKey(UserManager.DISALLOW_CHANGE_WIFI_STATE))
    }

    @Test fun relaxedSettingsClearAllManagedRestrictions() {
        val settings = NetworkSettings(true, true, true, true, true, true)
        assertTrue(settings.restrictions(35).values.none { it })
    }

    @Test fun unsupportedBlockingIsRejectedBeforeActivation() {
        val settings = NetworkSettings.fromPayloadJson(payload)!!
        assertThrows(IllegalArgumentException::class.java) { settings.copy(allowMobileData = false).validateForApi(35) }
        assertThrows(IllegalArgumentException::class.java) { settings.copy(allowWifi = false).validateForApi(32) }
        settings.copy(allowWifi = false).validateForApi(33)
    }

    @Test fun malformedSectionsAreNotTreatedAsLegacyPolicies() {
        assertNull(NetworkSettings.fromPayloadJson("{}"))
        for (bad in listOf("null", "{}", "[]")) {
            assertThrows(IllegalArgumentException::class.java) { NetworkSettings.fromPayloadJson("""{"network_settings":$bad}""") }
        }
        assertThrows(IllegalArgumentException::class.java) {
            NetworkSettings.fromPayloadJson(payload.replace("\"allow_wifi\":true", "\"allow_wifi\":\"true\""))
        }
    }

    @Test fun newPolicySyncsOnCellularAndMeteredWifiWhileLegacyBehaviorIsPreserved() {
        assertTrue(SyncNetworkPolicy.permits(payload, false, true, true))
        assertTrue(SyncNetworkPolicy.permits(payload, true, false, true))
        assertTrue(SyncNetworkPolicy.permits(null, false, true, true))
        assertFalse(SyncNetworkPolicy.permits("{}", true, false, true))
        assertTrue(SyncNetworkPolicy.permits("{}", true, false, false))
        assertFalse(SyncNetworkPolicy.permits(payload.replace("\"allow_wifi\":true", "\"allow_wifi\":false"), true, false, false))
        assertTrue(SyncNetworkPolicy.permits(payload.replace("\"allow_wifi\":true", "\"allow_wifi\":false"), true, true, true))
    }
}
