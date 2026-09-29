package io.github.sun808ey.edugd.dpc.policy

import com.google.gson.Gson
import io.github.sun808ey.edugd.dpc.crypto.CanonicalJson
import io.github.sun808ey.edugd.dpc.crypto.Ed25519Verifier

data class PolicyEnvelope(
    val version: Long,
    val publicKeyHex: String,
    val signatureHex: String,
    val policyData: PolicyData
)

data class PolicyData(
    val version: Long,
    val suspendedPackages: List<String> = emptyList(),
    val restrictions: List<String> = emptyList(),
    val lockTaskPackages: List<String> = emptyList()
)

class PolicyEngine(private val masterPublicKeyHex: String) {
    private val gson = Gson()

    fun evaluateAndVerifyPolicy(signedEnvelopeJson: String): PolicyData? {
        try {
            val envelope = gson.fromJson(signedEnvelopeJson, PolicyEnvelope::class.java)
            val canonicalPolicyJson = CanonicalJson.canonicalizeObject(envelope.policyData)

            val isValid = Ed25519Verifier.verifyCanonicalJson(
                masterPublicKeyHex.ifEmpty { envelope.publicKeyHex },
                canonicalPolicyJson,
                envelope.signatureHex
            )

            if (isValid) {
                return envelope.policyData
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return null
    }
}
