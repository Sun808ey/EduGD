package io.github.sun808ey.edugd.dpc.sync

import android.util.Base64
import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentProtocol
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentResponse
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom

class EnrollmentClient(private val serverBaseUrl: String, private val deviceUuid: String, private val identity: DeviceSigningIdentity) {
    fun register(pairingToken: String, androidVersion: String, apiLevel: Int): EnrollmentResponse? = try {
        val tokenUuid = pairingToken.substringBefore('.')
        val nonceBytes = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val nonce = Base64.encodeToString(nonceBytes, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
        val proof = DeviceAuthSigner.signEnrollment(identity, deviceUuid, tokenUuid, androidVersion, apiLevel, identity.publicKeyFingerprintHex, nonce)
        val publicKey = Base64.encodeToString(identity.publicKeySpki, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
        val body = JSONObject().apply {
            put("device_uuid", deviceUuid); put("android_version", androidVersion); put("api_level", apiLevel); put("pairing_token", pairingToken)
            put("credential", JSONObject().apply { put("algorithm", "ECDSA_P256_SHA256"); put("public_key", publicKey); put("nonce", nonce); put("proof", proof) })
        }.toString()
        val connection = URL("$serverBaseUrl/api/v1/devices/register").openConnection() as HttpURLConnection
        connection.requestMethod = "POST"; connection.setRequestProperty("Content-Type", "application/json"); connection.doOutput = true
        connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        if (connection.responseCode == HttpURLConnection.HTTP_CREATED) connection.inputStream.bufferedReader().use { EnrollmentProtocol.parseEnrollmentResponse(it.readText()) } else null
    } catch (_: Exception) { null }
}
