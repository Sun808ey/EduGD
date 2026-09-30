package io.github.sun808ey.edugd.dpc.enrollment

import android.app.admin.DevicePolicyManager
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
        if (origin.isNullOrBlank() || token.isNullOrBlank()) return@withContext quarantine("missing_provisioning_extras")
        val configuration = try {
            EnrollmentConfiguration(EnrollmentProtocol.validateApiOrigin(origin), token)
        } catch (_: Exception) {
            return@withContext quarantine("invalid_provisioning_extras")
        }
        try {
            val identity = DeviceKeyStore().getOrCreate()
            val provisionalUuid = enrollmentPrefs.getString(PROVISIONAL_UUID, null)
                ?: EnrollmentProtocol.generateDeviceUuid().also {
                    enrollmentPrefs.edit().putString(PROVISIONAL_UUID, it).apply()
                }
            val response = EnrollmentClient(configuration.apiOrigin, provisionalUuid, identity).register(token, android.os.Build.VERSION.RELEASE, android.os.Build.VERSION.SDK_INT)
                ?: return@withContext quarantine("enrollment_unavailable")
            require(response.deviceUuid == provisionalUuid) { "server identity mismatch" }
            DpcDatabase.getDatabase(context).dpcDao().replaceActiveDeviceIdentity(
                DeviceIdentityEntity(response.deviceUuid, response.credentialUuid, response.credentialAlgorithm, configuration.apiOrigin, identity.alias, System.currentTimeMillis(), response.serverTime, "ACTIVE")
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
