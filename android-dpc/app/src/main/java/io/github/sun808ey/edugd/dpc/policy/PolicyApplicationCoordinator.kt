package io.github.sun808ey.edugd.dpc.policy

import android.content.Context
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController
import io.github.sun808ey.edugd.dpc.audit.AuditChain

data class PolicyData(
    val version: Long,
    val suspendedPackages: List<String>,
    val lockTaskPackages: List<String>
)

class PolicyApplicationCoordinator(private val context: Context) {
    private val dpc = DevicePolicyController(context)
    private val repository = PolicyRepository(context)
    private val auditChain = AuditChain(context)

    fun applyPolicy(policyData: PolicyData): Boolean {
        try {
            dpc.setPackagesSuspended(policyData.suspendedPackages, true)
            dpc.setLockTaskPackages(policyData.lockTaskPackages)

            repository.lastPolicyVersion = policyData.version

            auditChain.appendEvent(eventCode = "policy_applied", metadata = mapOf("version" to policyData.version))
            return true
        } catch (e: Exception) {
            e.printStackTrace()
            auditChain.appendEvent(eventCode = "policy_rejected", metadata = mapOf("error" to (e.message ?: "unknown")))
            return false
        }
    }

    fun recordAdminEnabled() {
        auditChain.appendEvent(eventCode = "check_in", metadata = mapOf("admin_status" to "enabled"))
    }

    fun recordAdminDisabled() {
        auditChain.appendEvent(eventCode = "check_in", metadata = mapOf("admin_status" to "disabled"))
    }

    fun applyBootstrapOrQuarantine(): Boolean {
        return applyPolicy(PolicyData(1L, emptyList(), emptyList()))
    }

    companion object {
        @Volatile
        private var instance: PolicyApplicationCoordinator? = null

        fun from(context: Context): PolicyApplicationCoordinator {
            return instance ?: synchronized(this) {
                instance ?: PolicyApplicationCoordinator(context.applicationContext).also { instance = it }
            }
        }
    }
}
