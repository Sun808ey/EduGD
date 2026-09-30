package io.github.sun808ey.edugd.dpc.admin

import android.app.admin.DeviceAdminReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import io.github.sun808ey.edugd.dpc.policy.PolicyApplicationCoordinator

class AdminReceiver : DeviceAdminReceiver() {
    override fun onEnabled(context: Context, intent: Intent) {
        PolicyApplicationCoordinator.from(context).recordAdminEnabled()
    }

    override fun onDisabled(context: Context, intent: Intent) {
        PolicyApplicationCoordinator.from(context).recordAdminDisabled()
    }

    override fun onProfileProvisioningComplete(context: Context, intent: Intent) {
        PolicyApplicationCoordinator.from(context).applyBootstrapOrQuarantine()
    }

    companion object {
        fun getComponentName(context: Context): ComponentName {
            return ComponentName(context, AdminReceiver::class.java)
        }
    }
}
