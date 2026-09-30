package io.github.sun808ey.edugd.dpc.db

import androidx.room.*

@Dao
interface DpcDao {
    @Query("SELECT * FROM policy_state WHERE id = 1")
    suspend fun getPolicyState(): PolicyStateEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPolicyState(state: PolicyStateEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPolicyEnvelope(envelope: PolicyEnvelopeEntity)

    @Query("SELECT * FROM policy_envelope WHERE policyUuid = :policyUuid")
    suspend fun getPolicyEnvelope(policyUuid: String): PolicyEnvelopeEntity?

    @Query("UPDATE policy_state SET applyState = :applyState, desiredHash = :desiredHash WHERE id = 1")
    suspend fun markPending(applyState: String, desiredHash: String)

    @Query("UPDATE policy_state SET applyState = :applyState, appliedHash = :appliedHash, activePolicyUuid = :policyUuid, activeRevisionUuid = :revisionUuid WHERE id = 1")
    suspend fun markActive(applyState: String, appliedHash: String, policyUuid: String, revisionUuid: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAuditEvent(event: AuditEventEntity)

    @Query("SELECT * FROM audit_event ORDER BY sequence DESC LIMIT 1")
    suspend fun getLastAuditEvent(): AuditEventEntity?
}
