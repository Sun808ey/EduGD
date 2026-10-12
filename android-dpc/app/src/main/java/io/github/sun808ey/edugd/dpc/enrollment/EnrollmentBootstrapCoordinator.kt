package io.github.sun808ey.edugd.dpc.enrollment

import android.app.admin.DevicePolicyManager
import android.annotation.SuppressLint
import android.content.Context
import android.os.Bundle
import io.github.sun808ey.edugd.dpc.audit.AuditChain
import io.github.sun808ey.edugd.dpc.crypto.DeviceKeyStore
import io.github.sun808ey.edugd.dpc.db.DeviceIdentityEntity
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.sync.EnrollmentClient
import io.github.sun808ey.edugd.dpc.sync.SyncScheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class EnrollmentBootstrapCoordinator(private val context: Context) {
    private val enrollmentPrefs = context.getSharedPreferences("edugd_enrollment_state", Context.MODE_PRIVATE)

    suspend fun enroll(extras: Bundle): Boolean = withContext(Dispatchers.IO) {
        val origin = extras.getString("api_origin")
        val token = extras.getString("pairing_token")
        val keyId = extras.getString("server_signing_key_id")
        val publicKey = extras.getString("server_signing_public_key")
        val fingerprint = extras.getString("server_signing_key_fingerprint")
        if (origin.isNullOrBlank() || token.isNullOrBlank() || keyId.isNullOrBlank() || publicKey.isNullOrBlank() || fingerprint.isNullOrBlank()) return@withContext quarantine("missing_provisioning_extras")
        val configuration = try {
            val trustAnchor = EnrollmentProtocol.validateTrustAnchor(keyId, publicKey, fingerprint)
            EnrollmentConfiguration(EnrollmentProtocol.validateApiOrigin(origin), token, trustAnchor.first, trustAnchor.second, trustAnchor.third)
        } catch (_: Exception) {
            return@withContext quarantine("invalid_provisioning_extras")
        }
        try {
            val identity = DeviceKeyStore().getOrCreate()
            val provisionalUuid = enrollmentPrefs.getString(PROVISIONAL_UUID, null)
                ?: EnrollmentProtocol.generateDeviceUuid().also {
                    enrollmentPrefs.edit().putString(PROVISIONAL_UUID, it).apply()
                }
            val serial = readDeviceSerial()
            val response = EnrollmentClient(configuration.apiOrigin, provisionalUuid, identity).register(token, android.os.Build.VERSION.RELEASE, android.os.Build.VERSION.SDK_INT, android.os.Build.MANUFACTURER, android.os.Build.MODEL, serial)
                ?: return@withContext quarantine("enrollment_unavailable")
            require(response.deviceUuid == provisionalUuid) { "server identity mismatch" }
            DpcDatabase.getDatabase(context).dpcDao().replaceActiveDeviceIdentity(
                DeviceIdentityEntity(response.deviceUuid, response.credentialUuid, response.credentialAlgorithm, configuration.apiOrigin, identity.alias, System.currentTimeMillis(), response.serverTime, configuration.serverSigningKeyId, configuration.serverSigningPublicKey, configuration.serverSigningKeyFingerprint, 0L, "ACTIVE")
            )
            enrollmentPrefs.edit().remove(PROVISIONAL_UUID).putString(STATE, STATE_ENROLLED).remove(REASON).apply()
            SyncScheduler.schedule(context)
            true
        } catch (_: Exception) {
            quarantine("enrollment_failed")
        }
    }

    suspend fun rescheduleIfEnrolled() = withContext(Dispatchers.IO) {
        if (DpcDatabase.getDatabase(context).dpcDao().getActiveDeviceIdentity() != null) SyncScheduler.schedule(context)
    }

    private fun quarantine(reason: String): Boolean {
        enrollmentPrefs.edit().putString(STATE, STATE_QUARANTINED).putString(REASON, reason).apply()
        AuditChain(context).appendEvent("quarantine_entered", metadata = mapOf("reason" to reason))
        return false
    }

    @SuppressLint("MissingPermission")
    @Suppress("DEPRECATION")
    private fun readDeviceSerial(): String {
        if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.O) {
            return android.os.Build.SERIAL
        }
        val privilegedPhoneStateGranted = context.checkSelfPermission(
            "android.permission.READ_PRIVILEGED_PHONE_STATE"
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        if (!privilegedPhoneStateGranted) return android.os.Build.SERIAL
        return try {
            android.os.Build.getSerial()
        } catch (_: SecurityException) {
            android.os.Build.SERIAL
        }
    }

    companion object {
        private const val PROVISIONAL_UUID = "provisional_device_uuid"
        private const val STATE = "state"
        private const val REASON = "reason"
        const val STATE_ENROLLED = "ENROLLED"
        const val STATE_QUARANTINED = "QUARANTINED"
        const val STATE_PENDING = "PENDING"

        fun provisioningExtras(extras: Bundle?): Bundle? = extras?.getBundle(DevicePolicyManager.EXTRA_PROVISIONING_ADMIN_EXTRAS_BUNDLE)
        fun state(context: Context): String = context.getSharedPreferences("edugd_enrollment_state", Context.MODE_PRIVATE).getString(STATE, STATE_PENDING) ?: STATE_PENDING
    }
}
