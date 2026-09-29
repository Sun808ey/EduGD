package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import java.net.HttpURLConnection
import java.net.URL

class StateSyncClient(private val serverUrl: String, private val deviceId: String) {
    fun syncState(stateJson: String): String? {
        try {
            val payload = stateJson.toByteArray(Charsets.UTF_8)
            val auth = DeviceAuthSigner.createAuthHeader(deviceId, payload)

            val url = URL("$serverUrl/api/v1/dpc/sync")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Authorization", auth.authorizationHeader)
            conn.doOutput = true
            conn.outputStream.write(payload)

            if (conn.responseCode == HttpURLConnection.HTTP_OK) {
                return conn.inputStream.bufferedReader().use { it.readText() }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return null
    }
}
