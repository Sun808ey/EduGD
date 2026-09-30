package io.github.sun808ey.edugd.dpc.enrollment

import android.app.admin.DevicePolicyManager
import android.content.Context
import android.os.Bundle
import io.github.sun808ey.edugd.dpc.crypto.DeviceKeyStore
import io.github.sun808ey.edugd.dpc.db.DeviceIdentityEntity
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.sync.EnrollmentClient
import io.github.sun808ey.edugd.dpc.sync.SyncScheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class EnrollmentBootstrapCoordinator(private val context: Context) {
    suspend fun enroll(extras: Bundle): Boolean = withContext(Dispatchers.IO) {
        val origin = extras.getString("api_origin") ?: return@withContext false
        val token = extras.getString("pairing_token") ?: return@withContext false
        val configuration = try { EnrollmentConfiguration(EnrollmentProtocol.validateApiOrigin(origin), token) } catch (_: Exception) { return@withContext false }
        try {
            val identity = DeviceKeyStore().getOrCreate()
            val provisionalUuid = EnrollmentProtocol.generateDeviceUuid()
            val response = EnrollmentClient(configuration.apiOrigin, provisionalUuid, identity).register(token, android.os.Build.VERSION.RELEASE, android.os.Build.VERSION.SDK_INT) ?: return@withContext false
            require(response.deviceUuid == provisionalUuid) { "server identity mismatch" }
            DpcDatabase.getDatabase(context).dpcDao().replaceActiveDeviceIdentity(
                DeviceIdentityEntity(response.deviceUuid, response.credentialUuid, response.credentialAlgorithm, configuration.apiOrigin, identity.alias, System.currentTimeMillis(), response.serverTime, "ACTIVE")
            )
            SyncScheduler.schedule(context)
            true
        } catch (_: Exception) { false }
    }

    suspend fun rescheduleIfEnrolled() = withContext(Dispatchers.IO) {
        if (DpcDatabase.getDatabase(context).dpcDao().getActiveDeviceIdentity() != null) SyncScheduler.schedule(context)
    }

    companion object {
        fun provisioningExtras(extras: Bundle?): Bundle? = extras?.getBundle(DevicePolicyManager.EXTRA_PROVISIONING_ADMIN_EXTRAS_BUNDLE)
    }
}
