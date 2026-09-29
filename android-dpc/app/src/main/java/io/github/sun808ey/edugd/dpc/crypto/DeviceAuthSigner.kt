package io.github.sun808ey.edugd.dpc.crypto

import android.util.Base64
import java.util.UUID

object DeviceAuthSigner {

    data class AuthHeader(
        val authorizationHeader: String,
        val timestamp: Long,
        val nonce: String,
        val signatureBase64: String
    )

    fun createAuthHeader(deviceId: String, payloadBytes: ByteArray): AuthHeader {
        val timestamp = System.currentTimeMillis() / 1000
        val nonce = UUID.randomUUID().toString()

        val digest = java.security.MessageDigest.getInstance("SHA-256")
        val payloadHash = digest.digest(payloadBytes)

        val sb = StringBuilder()
            .append(deviceId)
            .append(":")
            .append(timestamp)
            .append(":")
            .append(nonce)
            .append(":")
            .append(Base64.encodeToString(payloadHash, Base64.NO_WRAP))

        val signatureBytes = DeviceKeyStore.signData(sb.toString().toByteArray(Charsets.UTF_8))
        val sigBase64 = Base64.encodeToString(signatureBytes, Base64.NO_WRAP)

        val headerValue = "DEVICE-AUTH-V1 deviceId=\"$deviceId\",timestamp=\"$timestamp\",nonce=\"$nonce\",signature=\"$sigBase64\""

        return AuthHeader(
            authorizationHeader = headerValue,
            timestamp = timestamp,
            nonce = nonce,
            signatureBase64 = sigBase64
        )
    }
}
