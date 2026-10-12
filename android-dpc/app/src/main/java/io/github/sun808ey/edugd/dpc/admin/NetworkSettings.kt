package io.github.sun808ey.edugd.dpc.admin

import android.os.UserManager
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.jsonObject
import org.json.JSONObject

data class NetworkSettings(
    val allowWifi: Boolean,
    val allowMobileData: Boolean,
    val allowBluetooth: Boolean,
    val allowHotspotCreation: Boolean,
    val allowVpnChanges: Boolean,
    val allowNetworkReset: Boolean,
) {
    fun validateForApi(apiLevel: Int) {
        require(allowMobileData) { "mobile_data_blocking_unsupported" }
        require(allowWifi || apiLevel >= 33) { "wifi_blocking_requires_android_13" }
    }

    fun restrictions(apiLevel: Int): Map<String, Boolean> = buildMap {
        put(UserManager.DISALLOW_BLUETOOTH, !allowBluetooth)
        put(UserManager.DISALLOW_CONFIG_TETHERING, !allowHotspotCreation)
        if (apiLevel >= 33) put(UserManager.DISALLOW_WIFI_TETHERING, !allowHotspotCreation)
        put(UserManager.DISALLOW_CONFIG_VPN, !allowVpnChanges)
        put(UserManager.DISALLOW_NETWORK_RESET, !allowNetworkReset)
        if (apiLevel >= 33) put(UserManager.DISALLOW_CHANGE_WIFI_STATE, !allowWifi)
    }

    companion object {
        private val keys = setOf("allow_wifi", "allow_mobile_data", "allow_bluetooth",
            "allow_hotspot_creation", "allow_vpn_changes", "allow_network_reset")

        fun fromPayload(payload: JSONObject): NetworkSettings? = fromPayloadJson(payload.toString())

        fun fromPayloadJson(payload: String): NetworkSettings? {
            val root = Json.parseToJsonElement(payload).jsonObject
            val value = root["network_settings"]?.jsonObject ?: return null
            require(value.keys == keys) { "invalid_network_settings_keys" }
            fun flag(key: String): Boolean {
                val item = value[key] as? JsonPrimitive
                require(item != null && !item.isString && item.booleanOrNull != null) {
                    "invalid_network_setting_boolean"
                }
                return item.booleanOrNull!!
            }
            return NetworkSettings(flag("allow_wifi"), flag("allow_mobile_data"),
                flag("allow_bluetooth"), flag("allow_hotspot_creation"),
                flag("allow_vpn_changes"), flag("allow_network_reset"))
        }
    }
}
