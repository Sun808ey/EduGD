package io.github.sun808ey.edugd.dpc.enrollment

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.net.URI
import java.util.UUID

data class EnrollmentConfiguration(val apiOrigin: String, val pairingToken: String)
data class EnrollmentResponse(val deviceUuid: String, val credentialUuid: String, val credentialAlgorithm: String, val serverTime: String)

object EnrollmentProtocol {
    fun validateApiOrigin(value: String): String {
        val uri = URI(value.trim())
        require(uri.scheme == "https" && !uri.host.isNullOrBlank()) { "api_origin must be an HTTPS origin" }
        require(uri.userInfo == null && uri.query == null && uri.fragment == null && (uri.path.isNullOrEmpty() || uri.path == "/")) { "api_origin must be an origin without credentials, path, query, or fragment" }
        return uri.toString().removeSuffix("/")
    }
    fun generateDeviceUuid(): String = UUID.randomUUID().toString()
    fun parseEnrollmentResponse(body: String): EnrollmentResponse {
        val json = Json.parseToJsonElement(body).jsonObject
        val deviceUuid = canonicalUuid(json.getValue("device_uuid").jsonPrimitive.content)
        val credentialUuid = canonicalUuid(json.getValue("credential_uuid").jsonPrimitive.content)
        val algorithm = json.getValue("credential_algorithm").jsonPrimitive.content
        require(algorithm == "ECDSA_P256_SHA256") { "unsupported credential algorithm" }
        val serverTime = json.getValue("server_time").jsonPrimitive.content
        require(serverTime.endsWith("Z")) { "invalid server_time" }
        return EnrollmentResponse(deviceUuid, credentialUuid, algorithm, serverTime)
    }
    private fun canonicalUuid(value: String): String {
        val uuid = UUID.fromString(value)
        require(uuid.version() == 4 && uuid.toString() == value) { "invalid UUIDv4" }
        return value
    }
}
