package io.github.sun808ey.edugd.dpc.crypto

import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import org.bouncycastle.util.encoders.Hex

object Ed25519Verifier {

    fun verify(publicKeyHex: String, messageBytes: ByteArray, signatureHex: String): Boolean {
        return try {
            val pubKeyBytes = Hex.decode(publicKeyHex)
            val sigBytes = Hex.decode(signatureHex)

            if (pubKeyBytes.size != 32 || sigBytes.size != 64) {
                return false
            }

            val pubKeyParam = Ed25519PublicKeyParameters(pubKeyBytes, 0)
            val verifier = Ed25519Signer()
            verifier.init(false, pubKeyParam)
            verifier.update(messageBytes, 0, messageBytes.size)
            verifier.verifySignature(sigBytes)
        } catch (e: Exception) {
            false
        }
    }

    fun verifyCanonicalJson(publicKeyHex: String, canonicalJson: String, signatureHex: String): Boolean {
        return verify(publicKeyHex, canonicalJson.toByteArray(Charsets.UTF_8), signatureHex)
    }
}
