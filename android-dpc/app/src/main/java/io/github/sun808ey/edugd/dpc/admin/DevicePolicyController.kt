package io.github.sun808ey.edugd.dpc.admin

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.UserManager

data class SuspensionResult(
    val requested: Set<String>,
    val applied: Set<String>,
    val rejectedByAndroid: Set<String>,
)

class DevicePolicyController(private val context: Context) {
    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val packageManager = context.packageManager
    private val adminComponent: ComponentName = AdminReceiver.getComponentName(context)

    fun isDeviceOwner(): Boolean {
        return dpm.isDeviceOwnerApp(context.packageName)
    }

    fun requireDeviceOwner() {
        check(dpm.isDeviceOwnerApp(context.packageName)) {
            "EduGD DPC must be the fully managed device owner"
        }
    }

    fun setPackagesSuspended(packageNames: List<String>, suspended: Boolean): Array<String> {
        if (!isDeviceOwner()) return packageNames.toTypedArray()
        val pkgs: Array<String> = packageNames.toTypedArray()
        val res: Array<String>? = dpm.setPackagesSuspended(adminComponent, pkgs, suspended)
        return res ?: emptyArray()
    }

    fun setLockTaskPackages(packages: List<String>) {
        if (!isDeviceOwner()) return
        val pkgs: Array<String> = packages.toTypedArray()
        dpm.setLockTaskPackages(adminComponent, pkgs)
    }

    fun applyDefaultRestrictions() {
        if (!isDeviceOwner()) return
        setUserRestriction(UserManager.DISALLOW_OUTGOING_CALLS, true)
        setUserRestriction(UserManager.DISALLOW_SMS, true)
        setUserRestriction(UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES, true)
        setUserRestriction(UserManager.DISALLOW_FACTORY_RESET, true)
    }

    fun setUserRestriction(restriction: String, enabled: Boolean) {
        if (!isDeviceOwner()) return
        if (enabled) {
            dpm.addUserRestriction(adminComponent, restriction)
        } else {
            dpm.clearUserRestriction(adminComponent, restriction)
        }
    }

    fun suspendPackages(
        packages: Set<String>,
        preserved: Set<String>,
    ): SuspensionResult {
        requireDeviceOwner()

        val installed = packageManager.getInstalledPackages(0)
            .map { it.packageName }
            .toSet()

        val requested = packages
            .intersect(installed)
            .minus(preserved)
            .minus(context.packageName)

        val pkgs: Array<String> = requested.toTypedArray()
        val suspendedResult: Array<String>? = dpm.setPackagesSuspended(
            adminComponent,
            pkgs,
            true
        )
        val rejected = (suspendedResult ?: emptyArray()).toSet()

        val applied = requested - rejected
        val readBackFailures = applied
            .filterNot { dpm.isPackageSuspended(adminComponent, it) }
            .toSet()

        check(readBackFailures.isEmpty()) {
            "Android did not retain suspension for $readBackFailures"
        }

        return SuspensionResult(requested, applied, rejected)
    }

    fun unsuspendPackages(packages: Set<String>) {
        requireDeviceOwner()
        val installed = packageManager.getInstalledPackages(0)
            .map { it.packageName }
            .toSet()
        val pkgs: Array<String> = packages.intersect(installed).toTypedArray()
        val unsuspendedResult: Array<String>? = dpm.setPackagesSuspended(adminComponent, pkgs, false)
        val rejected = (unsuspendedResult ?: emptyArray()).toSet()
        check(rejected.isEmpty()) { "Android refused to unsuspend $rejected" }
    }

    fun applyRestrictions(
        wifiOnly: Boolean,
        disallowOutgoingCalls: Boolean,
        disallowSms: Boolean,
        disallowUserVpn: Boolean,
    ) {
        requireDeviceOwner()

        val restrictions = buildSet {
            add(UserManager.DISALLOW_FACTORY_RESET)
            add(UserManager.DISALLOW_SAFE_BOOT)
            add(UserManager.DISALLOW_ADD_USER)
            add(UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES)
            add(UserManager.DISALLOW_CONFIG_TETHERING)
            add(UserManager.DISALLOW_WIFI_TETHERING)
            add(UserManager.DISALLOW_CONFIG_PRIVATE_DNS)
            if (wifiOnly) add(UserManager.DISALLOW_CONFIG_MOBILE_NETWORKS)
            if (disallowUserVpn) add(UserManager.DISALLOW_CONFIG_VPN)
            if (disallowOutgoingCalls) add(UserManager.DISALLOW_OUTGOING_CALLS)
            if (disallowSms) add(UserManager.DISALLOW_SMS)
        }
        restrictions.forEach { dpm.addUserRestriction(adminComponent, it) }
    }

    fun configureLockTask(packages: Set<String>) {
        requireDeviceOwner()
        val pkgs: Array<String> = (packages + context.packageName).toTypedArray()
        dpm.setLockTaskPackages(adminComponent, pkgs)
    }

    fun configureAlwaysOnFilteringVpn(vpnPackage: String) {
        requireDeviceOwner()
        check(vpnPackage == context.packageName)
        dpm.setAlwaysOnVpnPackage(adminComponent, vpnPackage, true)
    }

    fun nonSystemThirdPartyPackages(): Set<String> =
        packageManager.getInstalledPackages(0)
            .filter {
                val flags = it.applicationInfo?.flags ?: 0
                flags and ApplicationInfo.FLAG_SYSTEM == 0
            }
            .map { it.packageName }
            .toSet()
}
