package io.github.sun808ey.edugd.dpc.crypto

import android.util.Base64
import java.security.MessageDigest
import java.security.SecureRandom
import java.security.Signature

class DeviceAuthSigner(
    private val identity: DeviceSigningIdentity,
    private val credentialUuid: String,
    private val deviceUuid: String,
) {
    private val random = SecureRandom()

    data class SignedHeaders(
        val timestamp: String,
        val nonce: String,
        val bodySha256: String,
        val signature: String,
    )

    fun sign(
        method: String,
        canonicalPath: String,
        canonicalQuery: String,
        body: ByteArray,
        unixTimestamp: Long,
    ): SignedHeaders {
        require(method == method.uppercase())
        val timestamp = unixTimestamp.toString()
        val nonceBytes = ByteArray(16).also(random::nextBytes)
        val nonce = Base64.encodeToString(
            nonceBytes,
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING,
        )
        val bodyHash = MessageDigest.getInstance("SHA-256")
            .digest(body)
            .joinToString("") { "%02x".format(it) }
        val message = listOf(
            "DEVICE-AUTH-V1",
            method,
            canonicalPath,
            canonicalQuery,
            bodyHash,
            timestamp,
            nonce,
            credentialUuid,
            deviceUuid,
        ).joinToString("\n").toByteArray(Charsets.UTF_8)

        val signer = Signature.getInstance("SHA256withECDSA")
        signer.initSign(identity.keyPair.private)
        signer.update(message)
        val signature = Base64.encodeToString(
            signer.sign(),
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING,
        )
        return SignedHeaders(timestamp, nonce, bodyHash, signature)
    }

    companion object {
        fun signEnrollment(
            identity: DeviceSigningIdentity,
            deviceUuid: String,
            tokenUuid: String,
            androidVersion: String,
            apiLevel: Int,
            publicKeySpkiHex: String,
            nonceBase64: String
        ): String {
            val message = listOf(
                "DEVICE-ENROLL-V1",
                deviceUuid.lowercase(),
                tokenUuid.lowercase(),
                "ECDSA_P256_SHA256",
                publicKeySpkiHex.lowercase(),
                androidVersion,
                apiLevel.toString(),
                nonceBase64
            ).joinToString("\n").toByteArray(Charsets.UTF_8)

            val signer = Signature.getInstance("SHA256withECDSA")
            signer.initSign(identity.keyPair.private)
            signer.update(message)
            return Base64.encodeToString(
                signer.sign(),
                Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
            )
        }
    }
}
