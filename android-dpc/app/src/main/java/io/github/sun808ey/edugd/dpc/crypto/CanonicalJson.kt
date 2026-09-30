package io.github.sun808ey.edugd.dpc.crypto

import java.text.Normalizer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

object CanonicalJson {
    fun bytes(value: JsonElement): ByteArray =
        text(value).toByteArray(Charsets.UTF_8)

    fun text(value: JsonElement): String = buildString { write(value) }

    fun canonicalize(jsonString: String): String {
        return try {
            val element = Json.parseToJsonElement(jsonString)
            text(element)
        } catch (e: Exception) {
            jsonString
        }
    }

    private fun StringBuilder.write(value: JsonElement) {
        when (value) {
            JsonNull -> append("null")
            is JsonArray -> {
                append('[')
                value.forEachIndexed { index, item ->
                    if (index > 0) append(',')
                    write(item)
                }
                append(']')
            }
            is JsonObject -> {
                append('{')
                value.entries.sortedBy { it.key }
                    .forEachIndexed { index, entry ->
                        if (index > 0) append(',')
                        append('"').append(escapeJsonString(entry.key)).append('"')
                        append(':')
                        write(entry.value)
                    }
                append('}')
            }
            is JsonPrimitive -> {
                if (value.isString) {
                    val nfc = Normalizer.normalize(
                        value.content,
                        Normalizer.Form.NFC,
                    )
                    append('"').append(escapeJsonString(nfc)).append('"')
                } else {
                    val raw = value.content
                    require(
                        raw == "true" ||
                            raw == "false" ||
                            raw == "null" ||
                            raw.matches(Regex("-?(0|[1-9][0-9]*)")),
                    ) { "Only JSON booleans, null and integers are permitted" }
                    append(raw)
                }
            }
        }
    }

    private fun escapeJsonString(s: String): String {
        val sb = StringBuilder()
        for (c in s) {
            when (c) {
                '"' -> sb.append("\\\"")
                '\\' -> sb.append("\\\\")
                '\b' -> sb.append("\\b")
                '\u000c' -> sb.append("\\f")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                else -> {
                    if (c.code < 32) {
                        sb.append(String.format("\\u%04x", c.code))
                    } else {
                        sb.append(c)
                    }
                }
            }
        }
        return sb.toString()
    }
}
