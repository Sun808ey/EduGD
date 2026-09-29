package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import java.net.HttpURLConnection
import java.net.URL

class EnrollmentClient(private val serverUrl: String, private val deviceId: String) {
    fun enroll(enrollmentToken: String): Boolean {
        try {
            val payload = "{\"enrollmentToken\":\"$enrollmentToken\"}".toByteArray(Charsets.UTF_8)
            val auth = DeviceAuthSigner.createAuthHeader(deviceId, payload)

            val url = URL("$serverUrl/api/v1/dpc/enroll")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Authorization", auth.authorizationHeader)
            conn.doOutput = true
            conn.outputStream.write(payload)

            return conn.responseCode == HttpURLConnection.HTTP_OK
        } catch (e: Exception) {
            e.printStackTrace()
            return false
        }
    }
}
