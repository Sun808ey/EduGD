package io.github.sun808ey.edugd.dpc.admin

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OfflinePolicySettingsTest {
    @Test
    fun `accepts fail-safe offline settings`() {
        val settings = OfflinePolicySettings.fromPayloadJson(
            """{"offline_settings":{"enforce_last_valid_policy_offline":true,"store_local_policy_copy":true,"queue_events_while_offline":true,"apply_policy_changes_after_reconnection":true,"expire_policy_when_offline":false}}"""
        )

        assertTrue(settings!!.enforceLastValidPolicyOffline)
        assertTrue(settings.storeLocalPolicyCopy)
        assertTrue(settings.queueEventsWhileOffline)
        assertTrue(settings.applyPolicyChangesAfterReconnection)
        assertFalse(settings.expirePolicyWhenOffline)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `rejects offline expiry`() {
        OfflinePolicySettings.fromPayloadJson(
            """{"offline_settings":{"enforce_last_valid_policy_offline":true,"store_local_policy_copy":true,"queue_events_while_offline":true,"apply_policy_changes_after_reconnection":true,"expire_policy_when_offline":true}}"""
        )
    }
}
