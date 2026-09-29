package io.github.sun808ey.edugd.dpc.policy

import android.content.Context
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController
import io.github.sun808ey.edugd.dpc.audit.AuditChain

class PolicyApplicationCoordinator(private val context: Context) {
    private val dpc = DevicePolicyController(context)
    private val repository = PolicyRepository(context)
    private val auditChain = AuditChain(context)

    fun applyPolicy(policyData: PolicyData): Boolean {
        try {
            dpc.setPackagesSuspended(policyData.suspendedPackages, true)
            dpc.setLockTaskPackages(policyData.lockTaskPackages)

            repository.currentPolicyVersion = policyData.version
            repository.lastPolicyVersion = policyData.version

            auditChain.appendEvent("POLICY_APPLIED", mapOf("version" to policyData.version))
            return true
        } catch (e: Exception) {
            e.printStackTrace()
            auditChain.appendEvent("POLICY_APPLY_FAILED", mapOf("error" to (e.message ?: "unknown")))
            return false
        }
    }
}
