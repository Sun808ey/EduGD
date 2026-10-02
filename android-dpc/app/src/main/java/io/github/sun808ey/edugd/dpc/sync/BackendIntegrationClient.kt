package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import io.github.sun808ey.edugd.dpc.crypto.CanonicalJson
import io.github.sun808ey.edugd.dpc.crypto.Ed25519Verifier
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.UUID
import kotlin.math.abs

data class V3StateResponse(
    val protocolVersion: Int,
    val deviceUuid: String,
    val serverTime: String,
    val signingKeyId: String,
    val operation: String,
    val policy: JSONObject?,
    val overrideState: JSONObject?,
    val signature: String,
    val serverEpochSeconds: Long,
)

class BackendIntegrationClient(
    private val serverBaseUrl: String,
    private val deviceUuid: String,
    private val credentialUuid: String,
    private val identity: DeviceSigningIdentity,
    private val trustedSigningKeyId: String,
    private val trustedSigningPublicKey: String,
    private val lastAcceptedServerTimeEpochSeconds: Long,
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

            if (conn.responseCode == HttpURLConnection.HTTP_UNAUTHORIZED || conn.responseCode == HttpURLConnection.HTTP_FORBIDDEN) {
                throw CredentialRevokedException()
            }
            if (conn.responseCode == HttpURLConnection.HTTP_OK) {
                val rawJson = conn.inputStream.bufferedReader().use { it.readText() }
                val obj = JSONObject(rawJson)

                val protocolVersion = obj.getInt("protocol_version")
                require(protocolVersion == 3) { "Unsupported protocol version: $protocolVersion" }

                val respDeviceUuid = obj.getString("device_uuid")
                require(respDeviceUuid == deviceUuid) { "Device UUID mismatch" }

                val serverTime = obj.getString("server_time")
                val serverEpoch = Instant.parse(serverTime).epochSecond
                require(abs(serverEpoch - System.currentTimeMillis() / 1000) <= MAX_CLOCK_SKEW_SECONDS) { "server time outside allowed skew" }
                val signingKeyId = obj.getString("signing_key_id")
                require(signingKeyId == trustedSigningKeyId) { "untrusted signing key" }
                require(serverEpoch >= lastAcceptedServerTimeEpochSeconds) { "stale server state" }
                val operation = obj.getString("operation")
                require(operation in setOf("apply", "no_change", "clear", "rollback", "blocked")) {
                    "Invalid operation: $operation"
                }

                val policy = obj.optJSONObject("policy")
                val overrideState = obj.optJSONObject("override_state")
                val signature = obj.getString("signature")
                require(signature.isNotBlank()) { "Missing state signature" }
                val root = Json.parseToJsonElement(rawJson) as? JsonObject ?: error("invalid state")
                val unsigned = JsonObject(root.filterKeys { it != "signature" })
                require(Ed25519Verifier.verify(trustedSigningPublicKey, CanonicalJson.bytes(unsigned), signature)) { "invalid state signature" }
                policy?.let {
                    val policyJson = Json.parseToJsonElement(it.toString()) as? JsonObject ?: error("invalid policy")
                    val policySignature = policyJson["signature"]?.jsonPrimitive?.content ?: error("missing policy signature")
                    val policyUnsigned = JsonObject(policyJson.filterKeys { key -> key != "signature" })
                    require(Ed25519Verifier.verify(trustedSigningPublicKey, CanonicalJson.bytes(policyUnsigned), policySignature)) { "invalid policy signature" }
                }
                overrideState?.let {
                    val overrideJson = Json.parseToJsonElement(it.toString()) as? JsonObject ?: error("invalid override")
                    val overrideSignature = overrideJson["signature"]?.jsonPrimitive?.content ?: error("missing override signature")
                    val overrideUnsigned = JsonObject(overrideJson.filterKeys { key -> key != "signature" })
                    require(Ed25519Verifier.verify(trustedSigningPublicKey, CanonicalJson.bytes(overrideUnsigned), overrideSignature)) { "invalid override signature" }
                }

                V3StateResponse(
                    protocolVersion = protocolVersion,
                    deviceUuid = respDeviceUuid,
                    serverTime = serverTime,
                    signingKeyId = signingKeyId,
                    operation = operation,
                    policy = policy,
                    overrideState = overrideState,
                    signature = signature,
                    serverEpochSeconds = serverEpoch
                )
            } else if (conn.responseCode >= 500) {
                throw TransientSyncException("server_unavailable", "v3 state service unavailable")
            } else {
                throw PermanentSyncException("sync_rejected", "v3 state request rejected")
            }
        } catch (e: CredentialRevokedException) {
            throw e
        } catch (e: PermanentSyncException) {
            throw e
        } catch (e: IllegalArgumentException) {
            throw PermanentSyncException("invalid_signed_state", e.message ?: "invalid signed v3 state")
        } catch (_: Exception) {
            throw TransientSyncException("transport_failure", "v3 state request failed")
        }
    }

    fun uploadAuditBatch(batchUuid: String, canonicalBatch: String, signatureBase64: String): Boolean {
        return try {
            val path = "/api/v1/devices/$deviceUuid/audit-batches"
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
        } catch (_: Exception) {
            false
        }
    }

    fun uploadPolicyAcknowledgement(policyUuid: String?, revisionUuid: String?, outcome: String, errorCode: String? = null): Boolean {
        return try {
            val body = JSONObject().apply {
                put("protocol_version", 3)
                put("acknowledgement_uuid", UUID.randomUUID().toString())
                put("observed_at", DateTimeFormatter.ISO_INSTANT.format(Instant.now().atOffset(ZoneOffset.UTC)))
                put("elapsed_realtime_ms", 0)
                put("boot_count", 0)
                put("policy_uuid", policyUuid)
                put("revision_uuid", revisionUuid)
                put("outcome", outcome)
                put("error_code", errorCode)
            }.toString().toByteArray(Charsets.UTF_8)
            val path = "/api/v1/devices/$deviceUuid/policy-acknowledgements"
            val conn = URL("$serverBaseUrl$path").openConnection() as HttpURLConnection
            val headers = DeviceAuthSigner(identity, credentialUuid, deviceUuid).sign("POST", path, "", body, System.currentTimeMillis() / 1000)
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("X-Device-Timestamp", headers.timestamp)
            conn.setRequestProperty("X-Device-Nonce", headers.nonce)
            conn.setRequestProperty("X-Device-Body-SHA256", headers.bodySha256)
            conn.setRequestProperty("X-Device-Signature", headers.signature)
            conn.outputStream.use { it.write(body) }
            conn.responseCode == HttpURLConnection.HTTP_OK
        } catch (_: Exception) { false }
    }

    companion object { private const val MAX_CLOCK_SKEW_SECONDS = 300L }
}
