package io.github.sun808ey.edugd.dpc.policy

import android.content.Context
import android.content.SharedPreferences

class PolicyRepository(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("edugd_policy_prefs", Context.MODE_PRIVATE)

    var currentPolicyJson: String
        get() = prefs.getString("current_policy_json", "{}") ?: "{}"
        set(value) = prefs.edit().putString("current_policy_json", value).apply()

    var lastPolicyVersion: Long
        get() = prefs.getLong("last_policy_version", 0L)
        set(value) = prefs.edit().putLong("last_policy_version", value).apply()
}
