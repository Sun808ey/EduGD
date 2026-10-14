package io.github.sun808ey.edugd.dpc.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction

@Dao
interface DpcDao {
    @Query("SELECT * FROM device_identity WHERE state = 'ACTIVE' LIMIT 1")
    suspend fun getActiveDeviceIdentity(): DeviceIdentityEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDeviceIdentity(identity: DeviceIdentityEntity)

    @Query("DELETE FROM device_identity")
    suspend fun deleteDeviceIdentities()

    @Transaction
    suspend fun replaceActiveDeviceIdentity(identity: DeviceIdentityEntity) {
        deleteDeviceIdentities()
        insertDeviceIdentity(identity)
    }

    @Query("UPDATE device_identity SET state = 'REVOKED' WHERE state = 'ACTIVE'")
    suspend fun markIdentityRevoked()

    @Query("UPDATE device_identity SET state = 'QUARANTINED' WHERE state = 'ACTIVE'")
    suspend fun markIdentityQuarantined()

    @Query("UPDATE device_identity SET lastAcceptedServerTimeEpochSeconds = :epochSeconds WHERE deviceUuid = :deviceUuid")
    suspend fun updateAcceptedServerTime(deviceUuid: String, epochSeconds: Long)

    @Query("SELECT * FROM policy_state WHERE id = 1") suspend fun getPolicyState(): PolicyStateEntity?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insertPolicyState(state: PolicyStateEntity)
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insertPolicyEnvelope(envelope: PolicyEnvelopeEntity)
    @Query("SELECT * FROM policy_envelope WHERE policyUuid = :policyUuid") suspend fun getPolicyEnvelope(policyUuid: String): PolicyEnvelopeEntity?
    @Query("SELECT * FROM policy_envelope WHERE policyUuid != :policyUuid AND status IN ('ACTIVE', 'SUPERSEDED') ORDER BY verifiedAt DESC LIMIT 1") suspend fun getRollbackEnvelope(policyUuid: String): PolicyEnvelopeEntity?
    @Query("UPDATE policy_envelope SET status = :status WHERE policyUuid = :policyUuid") suspend fun updatePolicyStatus(policyUuid: String, status: String)
    @Query("SELECT * FROM policy_envelope WHERE status = 'ACTIVE' LIMIT 1") suspend fun getActivePolicyEnvelope(): PolicyEnvelopeEntity?
    @Query("UPDATE policy_state SET applyState = :applyState, desiredHash = :desiredHash WHERE id = 1") suspend fun markPending(applyState: String, desiredHash: String)
    @Query("UPDATE policy_state SET applyState = :applyState, appliedHash = :appliedHash, activePolicyUuid = :policyUuid, activeRevisionUuid = :revisionUuid WHERE id = 1") suspend fun markStateActive(applyState: String, appliedHash: String, policyUuid: String, revisionUuid: String)
    @Transaction
    suspend fun markActive(applyState: String, appliedHash: String, policyUuid: String, revisionUuid: String) {
        updatePolicyStatus(policyUuid, "ACTIVE")
        markStateActive(applyState, appliedHash, policyUuid, revisionUuid)
    }
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insertAuditEvent(event: AuditEventEntity)
    @Query("SELECT * FROM audit_event ORDER BY sequence DESC LIMIT 1") suspend fun getLastAuditEvent(): AuditEventEntity?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insertScreenTimeUsage(usage: ScreenTimeUsageEntity)
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insertScreenTimeState(state: ScreenTimeStateEntity)
    @Query("SELECT * FROM screen_time_state WHERE policyRevisionUuid = :revisionUuid AND usageDate = :usageDate")
    suspend fun getScreenTimeState(revisionUuid: String, usageDate: String): ScreenTimeStateEntity?
    @Query("DELETE FROM screen_time_usage WHERE policyRevisionUuid = :revisionUuid")
    suspend fun deleteScreenTimeUsage(revisionUuid: String)
    @Query("DELETE FROM screen_time_state WHERE policyRevisionUuid = :revisionUuid")
    suspend fun deleteScreenTimeState(revisionUuid: String)
    @Query("SELECT * FROM outbox WHERE status = 'PENDING' AND nextAttemptAt <= :now ORDER BY nextAttemptAt ASC LIMIT 1")
    suspend fun getDueOutbox(now: Long): OutboxEntity?
    @Query("SELECT EXISTS(SELECT 1 FROM outbox WHERE status = 'PENDING')") suspend fun hasPendingOutbox(): Boolean
    @Insert(onConflict = OnConflictStrategy.IGNORE) suspend fun insertOutbox(outbox: OutboxEntity): Long
    @Query("UPDATE outbox SET attemptCount = :attemptCount, nextAttemptAt = :nextAttemptAt WHERE eventUuid = :eventUuid")
    suspend fun deferOutbox(eventUuid: String, attemptCount: Int, nextAttemptAt: Long)
    @Query("DELETE FROM outbox WHERE eventUuid = :eventUuid") suspend fun deleteOutbox(eventUuid: String)
}
