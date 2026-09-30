package io.github.sun808ey.edugd.dpc.crypto

object Ed25519Verifier {
    fun verify(publicKeyHex: String, messageBytes: ByteArray, signatureHex: String): Boolean {
        // Pending backend contract review and approved dependency selection
        return false
    }

    fun verifyCanonicalJson(publicKeyHex: String, canonicalJson: String, signatureHex: String): Boolean {
        return verify(publicKeyHex, canonicalJson.toByteArray(Charsets.UTF_8), signatureHex)
    }
}
