package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.audit.AuditChain
import io.github.sun808ey.edugd.dpc.crypto.CanonicalJson
import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.db.OutboxEntity
import java.security.MessageDigest
import java.security.Signature
import java.util.UUID
import kotlin.math.min
import org.json.JSONArray
import org.json.JSONObject

class AuditOutbox(
    private val database: DpcDatabase,
    private val auditChain: AuditChain,
    private val deviceUuid: String,
    private val credentialUuid: String,
    private val identity: DeviceSigningIdentity,
) {
    private val dao = database.dpcDao()

    suspend fun flush(client: BackendIntegrationClient): Boolean {
        enqueuePending()
        var success = true
        while (true) {
            val outbox = dao.getDueOutbox(System.currentTimeMillis()) ?: break
            if (client.uploadAuditBatch(outbox.bodyJson)) {
                val body = JSONObject(outbox.bodyJson)
                auditChain.markUploaded(body.getLong("last_sequence") - 1L, body.getString("final_head"))
                dao.deleteOutbox(outbox.eventUuid)
            } else {
                val attempts = outbox.attemptCount + 1
                val delay = min(6 * 60 * 60 * 1000L, 60_000L * (1L shl min(attempts, 8)))
                dao.deferOutbox(outbox.eventUuid, attempts, System.currentTimeMillis() + delay)
                success = false
                break
            }
        }
        return success && !dao.hasPendingOutbox()
    }

    private suspend fun enqueuePending() {
        if (dao.hasPendingOutbox()) return
        val uploaded = auditChain.uploadedSequence()
        val events = auditChain.eventsAfter(uploaded, MAX_EVENTS_PER_BATCH)
        if (events.isEmpty()) return
        val batchUuid = UUID.randomUUID().toString()
        var previousHead = auditChain.uploadedHead()
        val converted = events.mapIndexed { index, event ->
            val convertedEvent = convertEvent(event, uploaded + index + 2L, previousHead)
            previousHead = convertedEvent.getString("event_hash")
            convertedEvent
        }
        val unsigned = JSONObject().apply {
            put("protocol_version", 3)
            put("batch_uuid", batchUuid)
            put("device_uuid", deviceUuid)
            put("credential_uuid", credentialUuid)
            put("first_sequence", converted.first().getLong("sequence"))
            put("last_sequence", converted.last().getLong("sequence"))
            put("previous_head", auditChain.uploadedHead())
            put("final_head", previousHead)
            put("signature_algorithm", "ECDSA_P256_SHA256")
            put("events", JSONArray().apply { converted.forEach { put(it) } })
        }
        val canonical = CanonicalJson.canonicalize(unsigned.toString())
        val signer = Signature.getInstance("SHA256withECDSA")
        signer.initSign(identity.keyPair.private)
        signer.update(canonical.toByteArray(Charsets.UTF_8))
        val signature = android.util.Base64.encodeToString(
            signer.sign(), android.util.Base64.URL_SAFE or android.util.Base64.NO_WRAP or android.util.Base64.NO_PADDING
        )
        val signed = JSONObject(canonical).apply { put("signature", signature) }
        val signedCanonical = CanonicalJson.canonicalize(signed.toString())
        dao.insertOutbox(OutboxEntity(batchUuid, "audit_batch", signedCanonical, batchUuid, 0, System.currentTimeMillis(), "PENDING"))
    }

    private fun convertEvent(source: JSONObject, sequence: Long, previousHead: String): JSONObject {
        val sourceCode = source.getString("event_code")
        val eventCode = when (sourceCode) {
            "blocked_domain" -> "web_filter_blocked"
            "vpn_started" -> "configuration_changed"
            "vpn_lockdown_failed" -> "enforcement_failure"
            "check_in" -> "boot_observed"
            "sync_failure" -> "sync_failed"
            "quarantine_entered" -> "enforcement_failure"
            "admin_override_observed" -> "block_override_applied"
            "package_suspended", "package_unsuspended" -> "policy_block"
            "setting_restricted" -> "configuration_changed"
            else -> sourceCode
        }
        val outcome = when (sourceCode) {
            "blocked_domain", "screen_time_exhausted", "package_suspended" -> "blocked"
            "vpn_lockdown_failed", "policy_rejected", "sync_failure" -> "failed"
            "clock_anomaly", "admin_override_observed", "quarantine_entered" -> "detected"
            else -> "succeeded"
        }
        val metadata = if (sourceCode == "blocked_domain") JSONObject().apply {
            put("domain_hash", source.getJSONObject("metadata").getString("domain_hash"))
        } else source.getJSONObject("metadata")
        val policyUuid = source.optString("policy_uuid").takeIf { it.isNotBlank() && it != "null" }
        val revisionUuid = source.optString("revision_uuid").takeIf { it.isNotBlank() && it != "null" }
        val pairedPolicyUuid = policyUuid?.takeIf { revisionUuid != null }
        val pairedRevisionUuid = revisionUuid?.takeIf { policyUuid != null }
        val ruleId = source.getJSONObject("metadata").optString("rule_id").takeIf { it.isNotBlank() }
        val event = JSONObject().apply {
            put("event_uuid", source.getString("event_uuid"))
            put("sequence", sequence)
            put("occurred_at", source.getString("observed_at"))
            put("elapsed_realtime_ms", source.getLong("elapsed_realtime_ms"))
            put("boot_count", source.getInt("boot_count"))
            put("event_code", eventCode)
            put("outcome", outcome)
            put("policy_uuid", pairedPolicyUuid ?: JSONObject.NULL)
            put("revision_uuid", pairedRevisionUuid ?: JSONObject.NULL)
            put("rule_id", ruleId ?: JSONObject.NULL)
            put("metadata", metadata)
            put("previous_event_hash", previousHead)
        }
        val hash = sha256(CanonicalJson.canonicalize(event.toString()).toByteArray(Charsets.UTF_8))
        event.put("event_hash", hash)
        return event
    }

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

    companion object { private const val MAX_EVENTS_PER_BATCH = 200 }
}
