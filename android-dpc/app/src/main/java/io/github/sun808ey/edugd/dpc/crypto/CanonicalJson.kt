package io.github.sun808ey.edugd.dpc.crypto

import com.google.gson.JsonElement
import com.google.gson.JsonParser
import java.text.Normalizer
import java.util.TreeMap

object CanonicalJson {

    fun canonicalize(jsonString: String): String {
        val element = JsonParser.parseString(jsonString)
        return canonicalizeElement(element)
    }

    fun canonicalizeObject(obj: Any): String {
        val gson = com.google.gson.Gson()
        val jsonStr = gson.toJson(obj)
        return canonicalize(jsonStr)
    }

    private fun canonicalizeElement(element: JsonElement): String {
        return when {
            element.isJsonObject -> {
                val obj = element.asJsonObject
                val sortedMap = TreeMap<String, JsonElement>()
                for ((key, value) in obj.entrySet()) {
                    val normalizedKey = Normalizer.normalize(key, Normalizer.Form.NFC)
                    sortedMap[normalizedKey] = value
                }
                val sb = StringBuilder("{")
                var first = true
                for ((key, value) in sortedMap) {
                    if (!first) sb.append(",")
                    first = false
                    sb.append("\"").append(escapeJsonString(key)).append("\":")
                    sb.append(canonicalizeElement(value))
                }
                sb.append("}").toString()
            }
            element.isJsonArray -> {
                val arr = element.asJsonArray
                val sb = StringBuilder("[")
                for (i in 0 until arr.size()) {
                    if (i > 0) sb.append(",")
                    sb.append(canonicalizeElement(arr.get(i)))
                }
                sb.append("]").toString()
            }
            element.isJsonPrimitive -> {
                val prim = element.asJsonPrimitive
                when {
                    prim.isBoolean -> prim.asBoolean.toString()
                    prim.isNumber -> {
                        val num = prim.asNumber
                        val d = num.toDouble()
                        if (d == d.toLong().toDouble() && !d.isInfinite() && !d.isNaN()) {
                            d.toLong().toString()
                        } else {
                            num.toString()
                        }
                    }
                    prim.isString -> {
                        val normalized = Normalizer.normalize(prim.asString, Normalizer.Form.NFC)
                        "\"" + escapeJsonString(normalized) + "\""
                    }
                    else -> prim.toString()
                }
            }
            element.isJsonNull -> "null"
            else -> element.toString()
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
