package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.admin.NetworkSettings

object SyncNetworkPolicy {
    fun permits(payload: String?, wifi: Boolean, cellular: Boolean, metered: Boolean): Boolean {
        val settings = payload?.let { NetworkSettings.fromPayloadJson(it) }
        // A new device has no active payload yet; allow the server fetch over
        // cellular so the first network policy can be installed there.
        if (settings == null) return (wifi && !metered) || cellular
        return (wifi && settings.allowWifi) || (cellular && settings.allowMobileData)
    }
}
