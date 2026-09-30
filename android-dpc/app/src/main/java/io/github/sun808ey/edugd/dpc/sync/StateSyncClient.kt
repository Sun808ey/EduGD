package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import java.net.HttpURLConnection
import java.net.URL

class StateSyncClient(private val serverBaseUrl: String, private val deviceUuid: String, private val credentialUuid: String, private val identity: DeviceSigningIdentity) {
    fun fetchState(): String? {
        val path = "/sync/v3/devices/$deviceUuid/state"
        try {
            val body = ByteArray(0); val headers = DeviceAuthSigner(identity, credentialUuid, deviceUuid).sign("GET", path, "", body, System.currentTimeMillis() / 1000)
            val connection = URL("$serverBaseUrl$path").openConnection() as HttpURLConnection
            connection.requestMethod = "GET"; connection.setRequestProperty("Authorization", "DeviceCredential $credentialUuid")
            connection.setRequestProperty("X-Device-Timestamp", headers.timestamp); connection.setRequestProperty("X-Device-Nonce", headers.nonce); connection.setRequestProperty("X-Device-Body-SHA256", headers.bodySha256); connection.setRequestProperty("X-Device-Signature", headers.signature)
            return when (connection.responseCode) {
                HttpURLConnection.HTTP_OK -> connection.inputStream.bufferedReader().use { it.readText() }
                HttpURLConnection.HTTP_UNAUTHORIZED, HttpURLConnection.HTTP_FORBIDDEN -> throw CredentialRevokedException()
                else -> null
            }
        } catch (error: CredentialRevokedException) { throw error } catch (_: Exception) { return null }
    }
}
