package io.github.sun808ey.edugd.dpc.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "device_identity")
data class DeviceIdentityEntity(
    @PrimaryKey val deviceUuid: String,
    val credentialUuid: String,
    val keyAlias: String,
    val enrolledAt: Long,
    val state: String
)

@Entity(tableName = "policy_envelope")
data class PolicyEnvelopeEntity(
    @PrimaryKey val policyUuid: String,
    val revisionUuid: String,
    val payloadJson: String,
    val payloadSha256: String,
    val signature: String,
    val signingKeyId: String,
    val issuedAt: Long,
    val verifiedAt: Long,
    val status: String
)

@Entity(tableName = "policy_state")
data class PolicyStateEntity(
    @PrimaryKey val id: Int = 1,
    val currentModeId: String,
    val activePolicyUuid: String?,
    val activeRevisionUuid: String?,
    val desiredHash: String,
    val appliedHash: String,
    val applyState: String,
    val lastServerTime: Long
)

@Entity(tableName = "suspension_journal", primaryKeys = ["policyRevisionUuid", "packageName"])
data class SuspensionJournalEntity(
    val policyRevisionUuid: String,
    val packageName: String,
    val suspendedByRevision: String,
    val observedSuspended: Boolean,
    val lastError: String?
)

@Entity(tableName = "outbox")
data class OutboxEntity(
    @PrimaryKey val eventUuid: String,
    val eventType: String,
    val bodyJson: String,
    val idempotencyUuid: String,
    val attemptCount: Int,
    val nextAttemptAt: Long,
    val status: String
)

@Entity(tableName = "audit_event")
data class AuditEventEntity(
    @PrimaryKey(autoGenerate = true) val sequence: Long = 0,
    val eventUuid: String,
    val observedAt: Long,
    val elapsedRealtimeMs: Long,
    val bootCount: Int,
    val eventCode: String,
    val metadataJson: String,
    val previousHash: String,
    val eventHash: String
)

@Entity(tableName = "capability_report")
data class CapabilityReportEntity(
    @PrimaryKey val reportUuid: String,
    val observedAt: Long,
    val apiLevel: Int,
    val buildFingerprint: String,
    val securityPatch: String,
    val capabilitiesJson: String,
    val reportStatus: String
)
