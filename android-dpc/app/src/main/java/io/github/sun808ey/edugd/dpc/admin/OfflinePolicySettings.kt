package io.github.sun808ey.edugd.dpc.admin

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.jsonObject
import org.json.JSONObject

data class OfflinePolicySettings(
    val enforceLastValidPolicyOffline: Boolean,
    val storeLocalPolicyCopy: Boolean,
    val queueEventsWhileOffline: Boolean,
    val applyPolicyChangesAfterReconnection: Boolean,
    val expirePolicyWhenOffline: Boolean,
) {
    companion object {
        private val keys = setOf(
            "enforce_last_valid_policy_offline",
            "store_local_policy_copy",
            "queue_events_while_offline",
            "apply_policy_changes_after_reconnection",
            "expire_policy_when_offline",
        )

        fun fromPayload(payload: JSONObject): OfflinePolicySettings? {
            return fromPayloadJson(payload.toString())
        }

        fun fromPayloadJson(payload: String): OfflinePolicySettings? {
            val root = Json.parseToJsonElement(payload).jsonObject
            val raw = root["offline_settings"]?.jsonObject ?: return null
            require(raw.keys == keys) { "invalid offline_settings" }
            fun flag(key: String): Boolean {
                val item = raw[key] as? JsonPrimitive
                require(item != null && !item.isString && item.booleanOrNull != null) {
                    "invalid offline setting boolean"
                }
                return item.booleanOrNull!!
            }
            val settings = OfflinePolicySettings(
                enforceLastValidPolicyOffline = flag("enforce_last_valid_policy_offline"),
                storeLocalPolicyCopy = flag("store_local_policy_copy"),
                queueEventsWhileOffline = flag("queue_events_while_offline"),
                applyPolicyChangesAfterReconnection = flag("apply_policy_changes_after_reconnection"),
                expirePolicyWhenOffline = flag("expire_policy_when_offline"),
            )
            require(settings.enforceLastValidPolicyOffline)
            require(settings.storeLocalPolicyCopy)
            require(settings.queueEventsWhileOffline)
            require(settings.applyPolicyChangesAfterReconnection)
            require(!settings.expirePolicyWhenOffline) { "offline policy expiry is not permitted" }
            return settings
        }

    }
}
