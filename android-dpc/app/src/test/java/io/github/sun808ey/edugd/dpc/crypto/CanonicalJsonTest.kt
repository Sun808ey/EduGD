package io.github.sun808ey.edugd.dpc.crypto

import org.junit.Assert.assertEquals
import org.junit.Test

class CanonicalJsonTest {
    @Test
    fun testCanonicalizationSortingAndSpacing() {
        val json = "{\"b\":2,\"a\":1}"
        val canonical = CanonicalJson.canonicalize(json)
        assertEquals("{\"a\":1,\"b\":2}", canonical)
    }

    @Test
    fun testIntegerNormalization() {
        val json = "{\"val\":123.00}"
        val canonical = CanonicalJson.canonicalize(json)
        assertEquals("{\"val\":123}", canonical)
    }
}
