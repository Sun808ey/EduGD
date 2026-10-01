package io.github.sun808ey.edugd.dpc.enrollment

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class EnrollmentProtocolTest {
    @Test fun `accepts canonical HTTPS origin`() { assertEquals("https://api.school.example", EnrollmentProtocol.validateApiOrigin("https://api.school.example/")) }
    @Test fun `rejects origins with credentials paths or insecure schemes`() {
        listOf("http://api.school.example", "https://user@api.school.example", "https://api.school.example/v1", "https://api.school.example?x=1").forEach {
            try { EnrollmentProtocol.validateApiOrigin(it); throw AssertionError("accepted $it") } catch (_: IllegalArgumentException) { }
        }
    }
    @Test fun `generates canonical distinct v4 identities`() {
        val first = EnrollmentProtocol.generateDeviceUuid(); val second = EnrollmentProtocol.generateDeviceUuid()
        assertTrue(first.matches(Regex("[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"))); assertNotEquals(first, second)
    }
    @Test fun `parses exact enrollment response`() {
        val result = EnrollmentProtocol.parseEnrollmentResponse("""{"device_uuid":"550e8400-e29b-41d4-a716-446655440000","credential_uuid":"00000000-0000-4000-8000-000000000001","credential_algorithm":"ECDSA_P256_SHA256","server_time":"2026-09-30T12:00:00Z"}""")
        assertEquals("550e8400-e29b-41d4-a716-446655440000", result.deviceUuid); assertEquals("00000000-0000-4000-8000-000000000001", result.credentialUuid)
    }
}
