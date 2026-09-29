package io.github.sun808ey.edugd.dpc.admin

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.os.UserManager

class DevicePolicyController(private val context: Context) {
    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val adminComponent: ComponentName = AdminReceiver.getComponentName(context)

    fun isDeviceOwner(): Boolean {
        return dpm.isDeviceOwnerApp(context.packageName)
    }

    fun setPackagesSuspended(packageNames: List<String>, suspended: Boolean): Array<String> {
        if (!isDeviceOwner()) return packageNames.toTypedArray()
        return dpm.setPackagesSuspended(adminComponent, packageNames.toTypedArray(), suspended)
    }

    fun setUserRestriction(restriction: String, enabled: Boolean) {
        if (!isDeviceOwner()) return
        if (enabled) {
            dpm.addUserRestriction(adminComponent, restriction)
        } else {
            dpm.clearUserRestriction(adminComponent, restriction)
        }
    }

    fun setLockTaskPackages(packages: List<String>) {
        if (!isDeviceOwner()) return
        dpm.setLockTaskPackages(adminComponent, packages.toTypedArray())
    }

    fun setLockTaskFeatures(features: Int) {
        if (!isDeviceOwner()) return
        try {
            dpm.setLockTaskFeatures(adminComponent, features)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun applyDefaultRestrictions() {
        if (!isDeviceOwner()) return
        setUserRestriction(UserManager.DISALLOW_OUTGOING_CALLS, true)
        setUserRestriction(UserManager.DISALLOW_SMS, true)
        setUserRestriction(UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES, true)
        setUserRestriction(UserManager.DISALLOW_FACTORY_RESET, true)
    }
}
