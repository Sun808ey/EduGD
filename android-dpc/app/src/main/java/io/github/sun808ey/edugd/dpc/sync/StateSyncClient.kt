package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import java.net.HttpURLConnection
import java.net.URL

class StateSyncClient(
    private val serverBaseUrl: String,
    private val deviceUuid: String,
    private val credentialUuid: String,
    private val identity: DeviceSigningIdentity
) {
    fun fetchState(): String? {
        return try {
            val path = "/sync/v3/devices/$deviceUuid/state"
            val url = URL("$serverBaseUrl$path")
            val bodyBytes = ByteArray(0)
            val timestamp = System.currentTimeMillis() / 1000

            val signer = DeviceAuthSigner(identity, credentialUuid, deviceUuid)
            val headers = signer.sign("GET", path, "", bodyBytes, timestamp)

            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("Authorization", "DeviceCredential $credentialUuid")
            conn.setRequestProperty("X-Device-Timestamp", headers.timestamp)
            conn.setRequestProperty("X-Device-Nonce", headers.nonce)
            conn.setRequestProperty("X-Device-Body-SHA256", headers.bodySha256)
            conn.setRequestProperty("X-Device-Signature", headers.signature)

            if (conn.responseCode == HttpURLConnection.HTTP_OK) {
                conn.inputStream.bufferedReader().use { it.readText() }
            } else {
                null
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}
