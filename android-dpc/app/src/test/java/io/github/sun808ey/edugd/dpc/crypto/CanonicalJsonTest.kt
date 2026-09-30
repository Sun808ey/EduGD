package io.github.sun808ey.edugd.dpc.crypto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test
import java.security.MessageDigest

class CanonicalJsonTest {
    @Test
    fun testCanonicalizationSortingAndSpacing() {
        val jsonStr = "{\"b\": 2, \"a\": 1}"
        val element = Json.parseToJsonElement(jsonStr)
        val canonical = CanonicalJson.text(element)
        assertEquals("{\"a\":1,\"b\":2}", canonical)
    }

    @Test
    fun testIntegerNormalization() {
        val jsonStr = "{\"val\": 42}"
        val element = Json.parseToJsonElement(jsonStr)
        val canonical = CanonicalJson.text(element)
        assertEquals("{\"val\":42}", canonical)
    }

    @Test
    fun testGoldenVectorBytesAndHash() {
        val jsonStr = "{\"timezone\":\"Africa/Kampala\",\"schema_version\":3}"
        val element = Json.parseToJsonElement(jsonStr)
        val bytes = CanonicalJson.bytes(element)
        val text = CanonicalJson.text(element)
        assertEquals("{\"schema_version\":3,\"timezone\":\"Africa/Kampala\"}", text)

        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
        val hex = digest.joinToString("") { "%02x".format(it) }
        assertEquals(64, hex.length)
    }
}
