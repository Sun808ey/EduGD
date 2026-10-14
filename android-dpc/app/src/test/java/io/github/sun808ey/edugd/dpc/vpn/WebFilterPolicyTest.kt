package io.github.sun808ey.edugd.dpc.vpn

import org.junit.Assert.assertEquals
import org.junit.Test

class WebFilterPolicyTest {
    @Test
    fun `matches exact and subdomain rules`() {
        val settings = WebFilterSettings("allow", listOf(
            WebFilterRule("block_social", "social.example", true, "block"),
            WebFilterRule("allow_root", "example.com", false, "allow"),
        ), listOf("com.example.browser"))

        assertEquals("block", settings.decision("WWW.SOCIAL.EXAMPLE.").first)
        assertEquals("allow", settings.decision("child.example.com").first)
        assertEquals(listOf("com.example.browser"), settings.browserPackages)
    }

    @Test
    fun `uses default for unrelated domain and hashes normalized value`() {
        val settings = WebFilterSettings("block", emptyList(), emptyList())

        assertEquals("block", settings.decision("example.net").first)
        assertEquals(64, WebFilterSettings.domainHash("example.net").length)
    }
}
