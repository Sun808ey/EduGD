package io.github.sun808ey.edugd.dpc.audit

import org.junit.Assert.assertTrue
import org.junit.Test

class AuditChainTest {
    @Test
    fun testAllowedEventCodes() {
        assertTrue(AuditChain.ALLOWED_EVENT_CODES.contains("policy_applied"))
        assertTrue(AuditChain.ALLOWED_EVENT_CODES.contains("blocked_domain"))
    }
}
