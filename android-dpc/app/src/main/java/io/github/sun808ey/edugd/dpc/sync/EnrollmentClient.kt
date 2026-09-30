package io.github.sun808ey.edugd.dpc.sync

import android.util.Base64
import io.github.sun808ey.edugd.dpc.crypto.DeviceAuthSigner
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom

class EnrollmentClient(
    private val serverBaseUrl: String,
    private val deviceUuid: String,
    private val credentialUuid: String,
    private val identity: DeviceSigningIdentity
) {
    fun register(pairingToken: String, androidVersion: String, apiLevel: Int): Boolean {
        return try {
            val parts = pairingToken.split(".")
            val tokenUuid = if (parts.isNotEmpty()) parts[0] else pairingToken

            val nonceBytes = ByteArray(16).also { SecureRandom().nextBytes(it) }
            val nonce = Base64.encodeToString(nonceBytes, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)

            val spkiHex = identity.publicKeyFingerprintHex

            val proof = DeviceAuthSigner.signEnrollment(
                identity = identity,
                deviceUuid = deviceUuid,
                tokenUuid = tokenUuid,
                androidVersion = androidVersion,
                apiLevel = apiLevel,
                publicKeySpkiHex = spkiHex,
                nonceBase64 = nonce
            )

            val publicKeyBase64Url = Base64.encodeToString(identity.publicKeySpki, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)

            val bodyJson = JSONObject().apply {
                put("device_uuid", deviceUuid)
                put("android_version", androidVersion)
                put("api_level", apiLevel)
                put("pairing_token", pairingToken)
                put("credential", JSONObject().apply {
                    put("algorithm", "ECDSA_P256_SHA256")
                    put("public_key", publicKeyBase64Url)
                    put("nonce", nonce)
                    put("proof", proof)
                })
            }.toString()

            val url = URL("$serverBaseUrl/api/v1/devices/register")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.doOutput = true
            conn.outputStream.write(bodyJson.toByteArray(Charsets.UTF_8))

            conn.responseCode == HttpURLConnection.HTTP_OK || conn.responseCode == HttpURLConnection.HTTP_CREATED
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }
}
