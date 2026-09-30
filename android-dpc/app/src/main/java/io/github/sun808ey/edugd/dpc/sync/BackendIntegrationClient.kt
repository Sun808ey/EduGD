package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class V3StateResponse(
    val protocolVersion: Int,
    val deviceUuid: String,
    val serverTime: String,
    val signingKeyId: String,
    val operation: String,
    val policy: JSONObject?,
    val overrideState: JSONObject?
)

class BackendIntegrationClient(
    private val serverBaseUrl: String,
    private val deviceUuid: String,
    private val credentialUuid: String,
    private val identity: DeviceSigningIdentity
) {
    fun fetchV3State(): V3StateResponse? {
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
                val rawJson = conn.inputStream.bufferedReader().use { it.readText() }
                val obj = JSONObject(rawJson)

                val protocolVersion = obj.getInt("protocol_version")
                require(protocolVersion == 3) { "Unsupported protocol version: $protocolVersion" }

                val respDeviceUuid = obj.getString("device_uuid")
                require(respDeviceUuid == deviceUuid) { "Device UUID mismatch" }

                val serverTime = obj.getString("server_time")
                val signingKeyId = obj.getString("signing_key_id")
                val operation = obj.getString("operation")
                require(operation in setOf("apply", "no_change", "clear", "rollback", "blocked")) {
                    "Invalid operation: $operation"
                }

                val policy = obj.optJSONObject("policy")
                val overrideState = obj.optJSONObject("override_state")

                V3StateResponse(
                    protocolVersion = protocolVersion,
                    deviceUuid = respDeviceUuid,
                    serverTime = serverTime,
                    signingKeyId = signingKeyId,
                    operation = operation,
                    policy = policy,
                    overrideState = overrideState
                )
            } else {
                null
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun uploadAuditBatch(batchUuid: String, canonicalBatch: String, signatureBase64: String): Boolean {
        return try {
            val path = "/api/v1/devices/audit-batches"
            val url = URL("$serverBaseUrl$path")
            val bodyBytes = canonicalBatch.toByteArray(Charsets.UTF_8)
            val timestamp = System.currentTimeMillis() / 1000

            val signer = DeviceAuthSigner(identity, credentialUuid, deviceUuid)
            val headers = signer.sign("POST", path, "", bodyBytes, timestamp)

            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Authorization", "DeviceCredential $credentialUuid")
            conn.setRequestProperty("X-Device-Timestamp", headers.timestamp)
            conn.setRequestProperty("X-Device-Nonce", headers.nonce)
            conn.setRequestProperty("X-Device-Body-SHA256", headers.bodySha256)
            conn.setRequestProperty("X-Device-Signature", headers.signature)
            conn.setRequestProperty("Content-Type", "application/json")
            conn.doOutput = true
            conn.outputStream.write(bodyBytes)

            conn.responseCode == HttpURLConnection.HTTP_OK || conn.responseCode == HttpURLConnection.HTTP_CREATED
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}
