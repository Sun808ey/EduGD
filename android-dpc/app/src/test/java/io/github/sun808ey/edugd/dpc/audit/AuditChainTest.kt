package io.github.sun808ey.edugd.dpc.audit

import org.junit.Assert.assertEquals
import org.junit.Test

class AuditChainTest {
    @Test
    fun testGenesisHashConstant() {
        assertEquals("0000000000000000000000000000000000000000000000000000000000000000", AuditChain.GENESIS_HASH)
    }
}
