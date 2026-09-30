package io.github.sun808ey.edugd.dpc.admin

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.telephony.TelephonyManager
import org.json.JSONArray
import org.json.JSONObject

data class CapabilityReportData(
    val activeTransports: List<String>,
    val mobileDataEnabled: Boolean,
    val simState: Int,
    val diallerHandler: String?,
    val emergencyHandler: String?,
    val handlersJson: String
)

class CapabilityCollector(private val context: Context) {
    fun collect(): CapabilityReportData {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.activeNetwork?.let { cm.getNetworkCapabilities(it) }

        val transports = mutableListOf<String>()
        if (caps != null) {
            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) transports.add("WIFI")
            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) transports.add("CELLULAR")
            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) transports.add("ETHERNET")
        }

        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        val mobileDataEnabled = tm.isDataEnabled
        val simState = tm.simState

        val pm = context.packageManager
        val dialIntent = Intent(Intent.ACTION_DIAL)
        val dialResolve = pm.resolveActivity(dialIntent, PackageManager.MATCH_DEFAULT_ONLY)
        val diallerHandler = dialResolve?.activityInfo?.packageName

        val emergencyIntent = Intent("android.intent.action.CALL_EMERGENCY")
        val emergencyResolve = pm.resolveActivity(emergencyIntent, PackageManager.MATCH_DEFAULT_ONLY)
        val emergencyHandler = emergencyResolve?.activityInfo?.packageName

        val handlersArray = JSONArray()
        diallerHandler?.let {
            handlersArray.put(JSONObject().apply {
                put("role", "dialler")
                put("package", it)
            })
        }
        emergencyHandler?.let {
            handlersArray.put(JSONObject().apply {
                put("role", "emergency")
                put("package", it)
            })
        }

        return CapabilityReportData(
            activeTransports = transports,
            mobileDataEnabled = mobileDataEnabled,
            simState = simState,
            diallerHandler = diallerHandler,
            emergencyHandler = emergencyHandler,
            handlersJson = handlersArray.toString()
        )
    }
}
