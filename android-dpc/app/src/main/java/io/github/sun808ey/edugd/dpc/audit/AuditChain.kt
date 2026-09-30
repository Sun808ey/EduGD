package io.github.sun808ey.edugd.dpc.audit

import android.content.Context
import android.content.SharedPreferences
import io.github.sun808ey.edugd.dpc.crypto.CanonicalJson
import io.github.sun808ey.edugd.dpc.crypto.DeviceKeyStore
import org.json.JSONObject
import java.security.MessageDigest
import java.security.Signature
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.UUID

class AuditChain(
    context: Context,
    private val deviceUuid: String = "00000000-0000-0000-0000-000000000001",
    private val credentialFingerprint: String = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
) {
    private val prefs: SharedPreferences = context.getSharedPreferences("edugd_audit_chain_prefs", Context.MODE_PRIVATE)

    companion object {
        const val GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
        val ALLOWED_EVENT_CODES = setOf(
            "policy_verified", "policy_applied", "policy_rejected",
            "package_suspended", "package_unsuspended", "setting_restricted",
            "vpn_started", "vpn_lockdown_failed", "blocked_domain",
            "screen_time_exhausted", "check_in", "sync_failure",
            "clock_anomaly", "admin_override_observed", "quarantine_entered"
        )
    }

    data class EventRecord(
        val sequence: Long,
        val eventUuid: String,
        val observedAt: String,
        val elapsedRealtimeMs: Long,
        val bootCount: Int,
        val deviceUuid: String,
        val credentialFingerprint: String,
        val policyUuid: String?,
        val revisionUuid: String?,
        val eventCode: String,
        val metadata: JSONObject,
        val previousHash: String,
        val eventHash: String
    )

    @Synchronized
    fun appendEvent(
        eventCode: String,
        policyUuid: String? = null,
        revisionUuid: String? = null,
        metadata: Map<String, Any?> = emptyMap()
    ): EventRecord {
        require(eventCode in ALLOWED_EVENT_CODES) { "Invalid event code: $eventCode" }

        if (eventCode == "blocked_domain") {
            val domainHash = metadata["domain_hash"] as? String
            require(domainHash != null && domainHash.length == 64 && domainHash == domainHash.lowercase() && domainHash.matches(Regex("^[0-9a-f]{64}$"))) {
                "blocked_domain metadata requires valid 64-character lowercase hex domain_hash"
            }
        }

        val lastSequence = prefs.getLong("audit_last_sequence", -1L)
        val sequence = lastSequence + 1L
        val previousHash = prefs.getString("audit_last_hash", GENESIS_HASH) ?: GENESIS_HASH
        val eventUuid = UUID.randomUUID().toString()
        val observedAt = DateTimeFormatter.ISO_INSTANT.format(Instant.now().atOffset(ZoneOffset.UTC))
        val elapsedRealtimeMs = 0L
        val bootCount = 1

        val metaObj = JSONObject(metadata)

        val rawObj = JSONObject().apply {
            put("sequence", sequence)
            put("event_uuid", eventUuid)
            put("observed_at", observedAt)
            put("elapsed_realtime_ms", elapsedRealtimeMs)
            put("boot_count", bootCount)
            put("device_uuid", deviceUuid)
            put("credential_fingerprint", credentialFingerprint)
            if (policyUuid != null) put("policy_uuid", policyUuid)
            if (revisionUuid != null) put("revision_uuid", revisionUuid)
            put("event_code", eventCode)
            put("metadata", metaObj)
            put("previous_hash", previousHash)
        }

        val canonicalText = CanonicalJson.canonicalize(rawObj.toString())
        val eventHash = sha256(canonicalText.toByteArray(Charsets.UTF_8))

        val record = EventRecord(
            sequence = sequence,
            eventUuid = eventUuid,
            observedAt = observedAt,
            elapsedRealtimeMs = elapsedRealtimeMs,
            bootCount = bootCount,
            deviceUuid = deviceUuid,
            credentialFingerprint = credentialFingerprint,
            policyUuid = policyUuid,
            revisionUuid = revisionUuid,
            eventCode = eventCode,
            metadata = metaObj,
            previousHash = previousHash,
            eventHash = eventHash
        )

        val storedObj = JSONObject(rawObj.toString()).apply {
            put("event_hash", eventHash)
        }

        prefs.edit()
            .putLong("audit_last_sequence", sequence)
            .putString("audit_last_hash", eventHash)
            .putString("audit_event_$sequence", storedObj.toString())
            .apply()

        return record
    }

    fun getLastHash(): String {
        return prefs.getString("audit_last_hash", GENESIS_HASH) ?: GENESIS_HASH
    }

    fun verifyChain(): Boolean {
        val lastSequence = prefs.getLong("audit_last_sequence", -1L)
        var expectedPreviousHash = GENESIS_HASH

        for (i in 0..lastSequence) {
            val json = prefs.getString("audit_event_$i", null) ?: return false
            val obj = JSONObject(json)
            val sequence = obj.getLong("sequence")
            val previousHash = obj.getString("previous_hash")
            val eventHash = obj.getString("event_hash")

            if (sequence != i || previousHash != expectedPreviousHash) {
                return false
            }

            obj.remove("event_hash")
            val canonicalText = CanonicalJson.canonicalize(obj.toString())
            val calculatedHash = sha256(canonicalText.toByteArray(Charsets.UTF_8))

            if (calculatedHash != eventHash) {
                return false
            }

            expectedPreviousHash = eventHash
        }
        return true
    }

    fun signBatch(batchUuid: String): Pair<String, String> {
        val lastSequence = prefs.getLong("audit_last_sequence", -1L)
        val firstHash = if (lastSequence >= 0) prefs.getString("audit_event_0", "")?.let { JSONObject(it).getString("previous_hash") } ?: GENESIS_HASH else GENESIS_HASH
        val finalHash = getLastHash()

        val batchSummary = JSONObject().apply {
            put("batch_uuid", batchUuid)
            put("first_sequence", 0)
            put("last_sequence", lastSequence)
            put("previous_head", firstHash)
            put("final_head", finalHash)
        }

        val canonicalBatch = CanonicalJson.canonicalize(batchSummary.toString())
        val identity = DeviceKeyStore().getOrCreate()
        val signer = Signature.getInstance("SHA256withECDSA")
        signer.initSign(identity.keyPair.private)
        signer.update(canonicalBatch.toByteArray(Charsets.UTF_8))
        val signatureBytes = signer.sign()
        val signatureBase64 = android.util.Base64.encodeToString(signatureBytes, android.util.Base64.URL_SAFE or android.util.Base64.NO_WRAP or android.util.Base64.NO_PADDING)

        return Pair(canonicalBatch, signatureBase64)
    }

    private fun sha256(bytes: ByteArray): String {
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(bytes)
        return digest.joinToString("") { "%02x".format(it) }
    }
}
