package io.github.sun808ey.edugd.dpc.vpn

import java.net.IDN
import java.security.MessageDigest
import org.json.JSONObject

data class WebFilterRule(
    val ruleId: String,
    val domain: String,
    val includeSubdomains: Boolean,
    val action: String,
)

data class WebFilterSettings(
    val defaultAction: String,
    val rules: List<WebFilterRule>,
    val browserPackages: List<String>,
) {
    fun decision(domain: String): Pair<String, WebFilterRule?> {
        val normalized = normalizeDomain(domain) ?: return defaultAction to null
        val match = rules
            .filter { normalized == it.domain || (it.includeSubdomains && normalized.endsWith(".${it.domain}")) }
            .maxWithOrNull(compareBy<WebFilterRule> { it.domain.length }.thenBy { it.ruleId })
        return (match?.action ?: defaultAction) to match
    }

    companion object {
        fun fromPayload(payload: JSONObject): WebFilterSettings? {
            val web = payload.optJSONObject("web_filter") ?: return null
            val rules = web.optJSONArray("rules") ?: return null
            val parsedRules = (0 until rules.length()).mapNotNull { index ->
                rules.optJSONObject(index)?.let { rule ->
                    WebFilterRule(
                        rule.getString("rule_id"),
                        normalizeDomain(rule.getString("domain")) ?: return@let null,
                        rule.getBoolean("include_subdomains"),
                        rule.getString("action"),
                    )
                }
            }
            val packages = web.optJSONArray("browser_packages")
                ?.let { array -> (0 until array.length()).mapNotNull(array::optString) }
                ?: emptyList()
            return WebFilterSettings(web.optString("default_action", "allow"), parsedRules, packages)
        }

        fun normalizeDomain(value: String): String? = runCatching {
            val candidate = value.trim().trimEnd('.').lowercase()
            require(candidate.isNotEmpty() && !candidate.contains('/') && !candidate.contains(':'))
            IDN.toASCII(candidate).also { ascii -> require(ascii == candidate && ascii.contains('.')) }
        }.getOrNull()

        fun domainHash(domain: String): String = MessageDigest.getInstance("SHA-256")
            .digest(domain.toByteArray(Charsets.UTF_8))
            .joinToString("") { byte -> "%02x".format(byte) }
    }
}
