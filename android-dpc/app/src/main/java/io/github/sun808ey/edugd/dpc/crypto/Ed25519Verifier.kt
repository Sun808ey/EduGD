package io.github.sun808ey.edugd.dpc.crypto

import android.util.Base64
import com.google.crypto.tink.subtle.Ed25519Verify
import java.security.MessageDigest

object Ed25519Verifier {
    /** Verifies the backend's unpadded base64url Ed25519 signatures. */
    fun verify(publicKeyBase64Url: String, messageBytes: ByteArray, signatureBase64Url: String): Boolean {
        return try {
            val publicKey = decodeBase64Url(publicKeyBase64Url)
            val signature = decodeBase64Url(signatureBase64Url)
            if (publicKey.size != 32 || signature.size != 64) return false
            Ed25519Verify(publicKey).verify(signature, messageBytes)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun verifyCanonicalJson(publicKeyBase64Url: String, canonicalJson: String, signatureBase64Url: String): Boolean {
        return verify(publicKeyBase64Url, canonicalJson.toByteArray(Charsets.UTF_8), signatureBase64Url)
    }

    fun publicKeyFingerprintHex(publicKeyBase64Url: String): String =
        MessageDigest.getInstance("SHA-256").digest(decodeBase64Url(publicKeyBase64Url))
            .joinToString("") { "%02x".format(it) }

    private fun decodeBase64Url(value: String): ByteArray {
        require(value.matches(Regex("[A-Za-z0-9_-]+"))) { "invalid base64url" }
        return Base64.decode(value, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
    }
}
