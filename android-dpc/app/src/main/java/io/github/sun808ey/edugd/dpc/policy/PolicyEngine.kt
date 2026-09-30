package io.github.sun808ey.edugd.dpc.policy

import org.json.JSONObject

data class PolicyEnvelope(
    val policyUuid: String,
    val revisionUuid: String,
    val payloadJson: String,
    val publicKeyHex: String,
    val signatureHex: String
)

class PolicyEngine(private val masterPublicKeyHex: String) {
    fun parseAndValidateEnvelope(signedEnvelopeJson: String): PolicyEnvelope {
        val obj = JSONObject(signedEnvelopeJson)
        val policyUuid = obj.optString("policy_uuid", "")
        val revisionUuid = obj.optString("revision_uuid", "")
        val payloadObj = obj.optJSONObject("payload") ?: JSONObject()
        val payloadJson = payloadObj.toString()
        val publicKeyHex = obj.optString("public_key_hex", masterPublicKeyHex)
        val signatureHex = obj.optString("signature", "")

        return PolicyEnvelope(
            policyUuid = policyUuid,
            revisionUuid = revisionUuid,
            payloadJson = payloadJson,
            publicKeyHex = publicKeyHex,
            signatureHex = signatureHex
        )
    }
}
