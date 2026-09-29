package io.github.sun808ey.edugd.dpc.audit

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import io.github.sun808ey.edugd.dpc.crypto.CanonicalJson
import java.security.MessageDigest

data class AuditEntry(
    val index: Long,
    val previousHash: String,
    val timestamp: Long,
    val eventType: String,
    val details: Map<String, Any>,
    val entryHash: String
)

class AuditChain(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("edugd_audit_prefs", Context.MODE_PRIVATE)
    private val gson = Gson()

    companion object {
        const val GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
    }

    @Synchronized
    fun appendEvent(eventType: String, details: Map<String, Any>): AuditEntry {
        val lastIndex = prefs.getLong("audit_last_index", -1L)
        val newIndex = lastIndex + 1L
        val previousHash = prefs.getString("audit_last_hash", GENESIS_HASH) ?: GENESIS_HASH
        val timestamp = System.currentTimeMillis()

        val rawEntryMap = mapOf(
            "index" to newIndex,
            "previousHash" to previousHash,
            "timestamp" to timestamp,
            "eventType" to eventType,
            "details" to details
        )

        val canonicalData = CanonicalJson.canonicalizeObject(rawEntryMap)
        val combined = previousHash + canonicalData + timestamp + eventType
        val entryHash = sha256(combined.toByteArray(Charsets.UTF_8))

        val entry = AuditEntry(newIndex, previousHash, timestamp, eventType, details, entryHash)
        val json = gson.toJson(entry)

        prefs.edit()
            .putLong("audit_last_index", newIndex)
            .putString("audit_last_hash", entryHash)
            .putString("audit_entry_$newIndex", json)
            .apply()

        return entry
    }

    fun getLastHash(): String {
        return prefs.getString("audit_last_hash", GENESIS_HASH) ?: GENESIS_HASH
    }

    fun verifyChain(): Boolean {
        val lastIndex = prefs.getLong("audit_last_index", -1L)
        var expectedPreviousHash = GENESIS_HASH

        for (i in 0..lastIndex) {
            val json = prefs.getString("audit_entry_$i", null) ?: return false
            val entry = gson.fromJson(json, AuditEntry::class.java)

            if (entry.index != i || entry.previousHash != expectedPreviousHash) {
                return false
            }

            val rawEntryMap = mapOf(
                "index" to entry.index,
                "previousHash" to entry.previousHash,
                "timestamp" to entry.timestamp,
                "eventType" to entry.eventType,
                "details" to entry.details
            )
            val canonicalData = CanonicalJson.canonicalizeObject(rawEntryMap)
            val combined = entry.previousHash + canonicalData + entry.timestamp + entry.eventType
            val calculatedHash = sha256(combined.toByteArray(Charsets.UTF_8))

            if (calculatedHash != entry.entryHash) {
                return false
            }

            expectedPreviousHash = entry.entryHash
        }
        return true
    }

    private fun sha256(bytes: ByteArray): String {
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(bytes)
        return digest.joinToString("") { "%02x".format(it) }
    }
}
