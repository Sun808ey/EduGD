package io.github.sun808ey.edugd.dpc.admin

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.ApplicationInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.UserManager
import android.provider.Settings
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.json.JSONObject

data class SuspensionResult(
    val requested: Set<String>,
    val applied: Set<String>,
    val rejectedByAndroid: Set<String>,
)

data class DeviceUseSettings(
    val mode: String = "normal_managed",
    val kioskModeEnabled: Boolean = false,
    val displaySchoolName: Boolean = false,
    val schoolName: String? = null,
    val supportMessage: String? = null,
) {
    companion object {
        fun fromPayload(payload: JSONObject): DeviceUseSettings {
            return fromPayloadJson(payload.toString())
        }

        fun fromPayloadJson(payload: String): DeviceUseSettings {
            val value = runCatching {
                Json.parseToJsonElement(payload).jsonObject["device_use"]?.jsonObject
            }.getOrNull() ?: return DeviceUseSettings()
            return DeviceUseSettings(
                mode = value.stringValue("mode") ?: "normal_managed",
                kioskModeEnabled = value.booleanValue("kiosk_mode_enabled") ?: false,
                displaySchoolName = value.booleanValue("display_school_name") ?: false,
                schoolName = value.stringValue("school_name"),
                supportMessage = value.stringValue("support_message"),
            )
        }

        private fun JsonObject.stringValue(key: String): String? =
            this[key]?.jsonPrimitive?.contentOrNull?.takeIf { it.isNotBlank() }

        private fun JsonObject.booleanValue(key: String): Boolean? =
            this[key]?.jsonPrimitive?.booleanOrNull
    }
}

data class ApplicationRestrictionSettings(
    val allowInstallationOfOtherApplications: Boolean,
    val allowInstallationFromUnknownSources: Boolean,
    val allowUninstallOfApprovedApplications: Boolean,
    val allowDisableOfApprovedApplications: Boolean,
    val allowGooglePlayStore: Boolean,
    val allowFileSharingApplications: Boolean,
    val fileSharingPackages: Set<String> = emptySet(),
    val approvedApplicationPackages: Set<String> = emptySet(),
) {
    companion object {
        fun fromPayload(payload: JSONObject): ApplicationRestrictionSettings? {
            return fromPayloadJson(payload.toString())
        }

        fun fromPayloadJson(payload: String): ApplicationRestrictionSettings? {
            val root = runCatching { Json.parseToJsonElement(payload).jsonObject }.getOrNull()
                ?: return null
            val controls = root["application_controls"]?.jsonObject ?: return null
            val approvedPackages = root["approved_applications"]?.jsonArray
                ?.mapNotNull { it.jsonObject["package_name"]?.jsonPrimitive?.contentOrNull }
                ?.filter { it.isNotBlank() }
                ?.toSet()
                ?: emptySet()
            val fileSharingPackages = controls["file_sharing_packages"]?.jsonArray
                ?.mapNotNull { it.jsonPrimitive.contentOrNull }
                ?.filter { it.isNotBlank() }
                ?.toSet()
                ?: emptySet()
            return ApplicationRestrictionSettings(
                allowInstallationOfOtherApplications = controls.booleanValue("allow_installation_of_other_applications") ?: false,
                allowInstallationFromUnknownSources = controls.booleanValue("allow_installation_from_unknown_sources") ?: false,
                allowUninstallOfApprovedApplications = controls.booleanValue("allow_uninstall_of_approved_applications") ?: false,
                allowDisableOfApprovedApplications = controls.booleanValue("allow_disable_of_approved_applications") ?: false,
                allowGooglePlayStore = controls.booleanValue("allow_google_play_store") ?: false,
                allowFileSharingApplications = controls.booleanValue("allow_file_sharing_applications") ?: false,
                fileSharingPackages = fileSharingPackages,
                approvedApplicationPackages = approvedPackages,
            )
        }

        private fun JsonObject.booleanValue(key: String): Boolean? =
            this[key]?.jsonPrimitive?.booleanOrNull
    }
}

data class DeviceRestrictionSettings(
    val blockFactoryReset: Boolean,
    val blockSafeMode: Boolean,
    val blockDeveloperOptionsAndDebugging: Boolean,
    val blockUsbFileTransfer: Boolean,
    val blockAccountChanges: Boolean,
    val blockUserSwitching: Boolean,
    val blockNetworkReset: Boolean,
    val blockWifiChanges: Boolean,
    val disableScreenshots: Boolean,
    val disableScreenRecording: Boolean,
    val disableCamera: Boolean,
    val disableMicrophone: Boolean,
    val disableLocation: Boolean,
) {
    fun screenCaptureDisabled(): Boolean = disableScreenshots || disableScreenRecording

    fun userRestrictions(): Set<String> = buildSet {
        if (blockFactoryReset) add(UserManager.DISALLOW_FACTORY_RESET)
        if (blockSafeMode) add(UserManager.DISALLOW_SAFE_BOOT)
        if (blockDeveloperOptionsAndDebugging) add(UserManager.DISALLOW_DEBUGGING_FEATURES)
        if (blockUsbFileTransfer) add(UserManager.DISALLOW_USB_FILE_TRANSFER)
        if (blockAccountChanges) add(UserManager.DISALLOW_MODIFY_ACCOUNTS)
        if (blockUserSwitching) add(UserManager.DISALLOW_USER_SWITCH)
        if (blockNetworkReset) add(UserManager.DISALLOW_NETWORK_RESET)
        if (blockWifiChanges) add(UserManager.DISALLOW_CONFIG_WIFI)
        if (disableMicrophone) add(UserManager.DISALLOW_UNMUTE_MICROPHONE)
        if (disableLocation) add(UserManager.DISALLOW_CONFIG_LOCATION)
    }

    companion object {
        private val managedUserRestrictions = setOf(
            UserManager.DISALLOW_FACTORY_RESET,
            UserManager.DISALLOW_SAFE_BOOT,
            UserManager.DISALLOW_DEBUGGING_FEATURES,
            UserManager.DISALLOW_USB_FILE_TRANSFER,
            UserManager.DISALLOW_MODIFY_ACCOUNTS,
            UserManager.DISALLOW_USER_SWITCH,
            UserManager.DISALLOW_NETWORK_RESET,
            UserManager.DISALLOW_CONFIG_WIFI,
            UserManager.DISALLOW_UNMUTE_MICROPHONE,
            UserManager.DISALLOW_CONFIG_LOCATION,
        )

        fun fromPayload(payload: JSONObject): DeviceRestrictionSettings? {
            return fromPayloadJson(payload.toString())
        }

        fun fromPayloadJson(payload: String): DeviceRestrictionSettings? {
            val root = runCatching { Json.parseToJsonElement(payload).jsonObject }.getOrNull()
                ?: return null
            val restrictions = root["device_restrictions"]?.jsonObject ?: return null
            return DeviceRestrictionSettings(
                blockFactoryReset = restrictions.booleanValue("block_factory_reset") ?: false,
                blockSafeMode = restrictions.booleanValue("block_safe_mode") ?: false,
                blockDeveloperOptionsAndDebugging = restrictions.booleanValue("block_developer_options_and_debugging") ?: false,
                blockUsbFileTransfer = restrictions.booleanValue("block_usb_file_transfer") ?: false,
                blockAccountChanges = restrictions.booleanValue("block_account_changes") ?: false,
                blockUserSwitching = restrictions.booleanValue("block_user_switching") ?: false,
                blockNetworkReset = restrictions.booleanValue("block_network_reset") ?: false,
                blockWifiChanges = restrictions.booleanValue("block_wifi_changes") ?: false,
                disableScreenshots = restrictions.booleanValue("disable_screenshots") ?: false,
                disableScreenRecording = restrictions.booleanValue("disable_screen_recording") ?: false,
                disableCamera = restrictions.booleanValue("disable_camera") ?: false,
                disableMicrophone = restrictions.booleanValue("disable_microphone") ?: false,
                disableLocation = restrictions.booleanValue("disable_location") ?: false,
            )
        }

        fun allUserRestrictions(): Set<String> = managedUserRestrictions

        private fun JsonObject.booleanValue(key: String): Boolean? =
            this[key]?.jsonPrimitive?.booleanOrNull
    }
}

data class ScreenLockSettings(
    val requireScreenLock: Boolean,
    val automaticLockAfterMinutes: Int,
    val allowBiometricUnlock: Boolean,
    val allowLearnerChangeLockMethod: Boolean,
) {
    fun automaticLockAfterMillis(): Long = automaticLockAfterMinutes * 60_000L

    companion object {
        private val allowedTimeouts = setOf(1, 5, 10, 15, 30, 60)

        fun fromPayload(payload: JSONObject): ScreenLockSettings? {
            return fromPayloadJson(payload.toString())
        }

        fun fromPayloadJson(payload: String): ScreenLockSettings? {
            val root = runCatching { Json.parseToJsonElement(payload).jsonObject }.getOrNull()
                ?: return null
            val lock = root["screen_lock"]?.jsonObject ?: return null
            val timeout = lock["automatic_lock_after_minutes"]?.jsonPrimitive?.contentOrNull?.toIntOrNull()
                ?.takeIf { it in allowedTimeouts }
                ?: throw IllegalArgumentException("invalid screen-lock timeout")
            val requireScreenLock = lock.booleanValue("require_screen_lock")
                ?: throw IllegalArgumentException("invalid screen-lock requirement")
            val allowBiometricUnlock = lock.booleanValue("allow_biometric_unlock")
                ?: throw IllegalArgumentException("invalid biometric unlock choice")
            val allowLearnerChangeLockMethod = lock.booleanValue("allow_learner_change_lock_method")
                ?: throw IllegalArgumentException("invalid lock-method change choice")
            return ScreenLockSettings(
                requireScreenLock = requireScreenLock,
                automaticLockAfterMinutes = timeout,
                allowBiometricUnlock = allowBiometricUnlock,
                allowLearnerChangeLockMethod = allowLearnerChangeLockMethod,
            )
        }

        private fun JsonObject.booleanValue(key: String): Boolean? =
            this[key]?.jsonPrimitive?.booleanOrNull
    }
}

class DevicePolicyController(private val context: Context) {
    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val packageManager = context.packageManager
    private val adminComponent: ComponentName = AdminReceiver.getComponentName(context)

    fun isDeviceOwner(): Boolean {
        return dpm.isDeviceOwnerApp(context.packageName)
    }

    fun validateNetworkSettings(settings: NetworkSettings) {
        requireDeviceOwner()
        settings.validateForApi(Build.VERSION.SDK_INT)
    }

    fun applyNetworkSettings(settings: NetworkSettings) {
        validateNetworkSettings(settings)
        val restrictions = settings.restrictions(Build.VERSION.SDK_INT)
        restrictions.forEach { (key, blocked) -> setUserRestriction(key, blocked) }
        val retained = dpm.getUserRestrictions(adminComponent)
        check(restrictions.all { (key, blocked) -> retained.getBoolean(key) == blocked }) {
            "network_restriction_readback_failed"
        }
        if (!settings.allowWifi) {
            val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val prefs = context.getSharedPreferences("edugd_network_state", Context.MODE_PRIVATE)
            if (!prefs.contains("wifi_was_enabled")) {
                check(prefs.edit().putBoolean("wifi_was_enabled", wifi.isWifiEnabled).commit())
            }
            check(wifi.setWifiEnabled(false)) { "wifi_disable_rejected" }
            repeat(50) {
                if (wifi.wifiState == WifiManager.WIFI_STATE_DISABLED) return
                Thread.sleep(100)
            }
            error("wifi_disable_readback_failed")
        }
    }

    fun clearNetworkSettings() {
        if (!isDeviceOwner()) return
        NetworkSettings(true, true, true, true, true, true).restrictions(Build.VERSION.SDK_INT)
            .keys.forEach { setUserRestriction(it, false) }
        val prefs = context.getSharedPreferences("edugd_network_state", Context.MODE_PRIVATE)
        if (prefs.contains("wifi_was_enabled")) {
            if (prefs.getBoolean("wifi_was_enabled", false)) {
                val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
                check(wifi.setWifiEnabled(true)) { "wifi_restore_rejected" }
            }
            check(prefs.edit().remove("wifi_was_enabled").commit())
        }
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

    fun applyDeviceUseSettings(settings: DeviceUseSettings) {
        if (!isDeviceOwner()) return
        dpm.setOrganizationName(
            adminComponent,
            if (settings.displaySchoolName) settings.schoolName ?: "EduGD" else null,
        )
        dpm.setDeviceOwnerLockScreenInfo(adminComponent, settings.supportMessage)
    }

    fun clearDeviceUseSettings() {
        if (!isDeviceOwner()) return
        dpm.setOrganizationName(adminComponent, null)
        dpm.setDeviceOwnerLockScreenInfo(adminComponent, null)
    }

    fun applyApplicationRestrictions(settings: ApplicationRestrictionSettings) {
        requireDeviceOwner()
        setUserRestriction(UserManager.DISALLOW_INSTALL_APPS, !settings.allowInstallationOfOtherApplications)
        setUserRestriction(UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES, !settings.allowInstallationFromUnknownSources)
        setUserRestriction(UserManager.DISALLOW_APPS_CONTROL, !settings.allowDisableOfApprovedApplications)
        setUserRestriction(UserManager.DISALLOW_BLUETOOTH_SHARING, !settings.allowFileSharingApplications)

        settings.approvedApplicationPackages.forEach { packageName ->
            dpm.setUninstallBlocked(adminComponent, packageName, !settings.allowUninstallOfApprovedApplications)
        }

        val playStorePackages = setOf("com.android.vending")
        if (settings.allowGooglePlayStore) {
            unsuspendPackages(playStorePackages + settings.fileSharingPackages)
        } else {
            suspendPackages(playStorePackages, preserved = setOf(context.packageName))
        }
        if (settings.allowFileSharingApplications) {
            unsuspendPackages(settings.fileSharingPackages)
        } else {
            suspendPackages(settings.fileSharingPackages, preserved = setOf(context.packageName))
        }
    }

    fun clearApplicationRestrictions(settings: ApplicationRestrictionSettings? = null) {
        if (!isDeviceOwner()) return
        setUserRestriction(UserManager.DISALLOW_INSTALL_APPS, false)
        setUserRestriction(UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES, false)
        setUserRestriction(UserManager.DISALLOW_APPS_CONTROL, false)
        setUserRestriction(UserManager.DISALLOW_BLUETOOTH_SHARING, false)
        settings?.approvedApplicationPackages?.forEach { packageName ->
            dpm.setUninstallBlocked(adminComponent, packageName, false)
        }
        unsuspendPackages(setOf("com.android.vending") + (settings?.fileSharingPackages ?: emptySet()))
    }

    fun applyDeviceRestrictions(settings: DeviceRestrictionSettings) {
        requireDeviceOwner()
        val enabledRestrictions = settings.userRestrictions()
        DeviceRestrictionSettings.allUserRestrictions().forEach { restriction ->
            setUserRestriction(restriction, restriction in enabledRestrictions)
        }
        dpm.setCameraDisabled(adminComponent, settings.disableCamera)
        dpm.setScreenCaptureDisabled(adminComponent, settings.screenCaptureDisabled())
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            dpm.setLocationEnabled(adminComponent, !settings.disableLocation)
        } else if (settings.disableLocation) {
            @Suppress("DEPRECATION")
            dpm.setSecureSetting(adminComponent, Settings.Secure.LOCATION_MODE, "0")
        }
    }

    fun clearDeviceRestrictions() {
        if (!isDeviceOwner()) return
        DeviceRestrictionSettings.allUserRestrictions().forEach { restriction ->
            setUserRestriction(restriction, false)
        }
        dpm.setCameraDisabled(adminComponent, false)
        dpm.setScreenCaptureDisabled(adminComponent, false)
    }

    fun applyScreenLock(settings: ScreenLockSettings) {
        requireDeviceOwner()
        dpm.setMaximumTimeToLock(adminComponent, settings.automaticLockAfterMillis())
        dpm.setPasswordQuality(
            adminComponent,
            if (settings.requireScreenLock) {
                DevicePolicyManager.PASSWORD_QUALITY_SOMETHING
            } else {
                DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED
            },
        )
        dpm.setKeyguardDisabledFeatures(
            adminComponent,
            if (settings.allowBiometricUnlock) {
                DevicePolicyManager.KEYGUARD_DISABLE_FEATURES_NONE
            } else {
                DevicePolicyManager.KEYGUARD_DISABLE_BIOMETRICS
            },
        )
        setUserRestriction(
            UserManager.DISALLOW_CONFIG_CREDENTIALS,
            !settings.allowLearnerChangeLockMethod,
        )
    }

    fun clearScreenLock() {
        if (!isDeviceOwner()) return
        dpm.setMaximumTimeToLock(adminComponent, 0L)
        dpm.setPasswordQuality(adminComponent, DevicePolicyManager.PASSWORD_QUALITY_UNSPECIFIED)
        dpm.setKeyguardDisabledFeatures(adminComponent, DevicePolicyManager.KEYGUARD_DISABLE_FEATURES_NONE)
        setUserRestriction(UserManager.DISALLOW_CONFIG_CREDENTIALS, false)
    }

    fun clearManagedPackages(packages: List<String>) {
        if (!isDeviceOwner()) return
        val installed = packageManager.getInstalledPackages(0).map { it.packageName }.toSet()
        val requested = packages.toSet().intersect(installed).minus(context.packageName)
        if (requested.isNotEmpty()) dpm.setPackagesSuspended(adminComponent, requested.toTypedArray(), false)
        dpm.setLockTaskPackages(adminComponent, arrayOf(context.packageName))
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
