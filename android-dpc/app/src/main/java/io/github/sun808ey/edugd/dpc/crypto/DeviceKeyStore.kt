package io.github.sun808ey.edugd.dpc.crypto

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.spec.ECGenParameterSpec

data class DeviceSigningIdentity(
    val alias: String,
    val keyPair: KeyPair,
    val publicKeySpki: ByteArray,
    val publicKeyFingerprintHex: String,
    val hardwareBacked: Boolean,
)

class DeviceKeyStore {
    private val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    fun getOrCreate(alias: String = "edugd-device-auth-v1"):
        DeviceSigningIdentity {
        if (!store.containsAlias(alias)) {
            val generator = KeyPairGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_EC,
                "AndroidKeyStore",
            )
            generator.initialize(
                KeyGenParameterSpec.Builder(
                    alias,
                    KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY,
                )
                    .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                    .setDigests(KeyProperties.DIGEST_SHA256)
                    .setUserAuthenticationRequired(false)
                    .build(),
            )
            generator.generateKeyPair()
        }

        val certificate = store.getCertificate(alias)
            ?: error("Device key certificate is missing")
        val publicKey = certificate.publicKey
        val spki = publicKey.encoded
        val fingerprint = MessageDigest.getInstance("SHA-256")
            .digest(spki)
            .joinToString("") { "%02x".format(it) }
        val privateKey = store.getKey(alias, null)
        val keyInfo = java.security.KeyFactory
            .getInstance(privateKey.algorithm, "AndroidKeyStore")
            .getKeySpec(privateKey, KeyInfo::class.java)

        return DeviceSigningIdentity(
            alias,
            KeyPair(publicKey, privateKey as java.security.PrivateKey),
            spki,
            fingerprint,
            keyInfo.isInsideSecureHardware,
        )
    }
}
