package io.github.sun808ey.edugd.dpc.crypto

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature

object DeviceKeyStore {
    private const val KEY_ALIAS = "EduGdDeviceAuthKey"
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"

    init {
        ensureKeyExists()
    }

    @Synchronized
    fun ensureKeyExists() {
        try {
            val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
            keyStore.load(null)
            if (!keyStore.containsAlias(KEY_ALIAS)) {
                val kpg = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEYSTORE)
                val parameterSpec = KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_SIGN
                )
                    .setDigests(KeyProperties.DIGEST_SHA256)
                    .setAlgorithmParameterSpec(java.security.spec.ECGenParameterSpec("secp256r1"))
                    .build()
                kpg.initialize(parameterSpec)
                kpg.generateKeyPair()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun signData(data: ByteArray): ByteArray {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        val privateKey = keyStore.getKey(KEY_ALIAS, null) as? PrivateKey
            ?: throw IllegalStateException("Device auth private key not found in Keystore")

        val s = Signature.getInstance("SHA256withECDSA")
        s.initSign(privateKey)
        s.update(data)
        return s.sign()
    }

    fun getPublicKeyBytes(): ByteArray? {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        val cert = keyStore.getCertificate(KEY_ALIAS) ?: return null
        return cert.public.encoded
    }
}
