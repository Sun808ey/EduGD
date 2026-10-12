package io.github.sun808ey.edugd.dpc

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.lifecycleScope
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentBootstrapCoordinator
import io.github.sun808ey.edugd.dpc.db.DpcDatabase
import io.github.sun808ey.edugd.dpc.admin.DeviceUseSettings
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = when (EnrollmentBootstrapCoordinator.state(this@MainActivity)) {
                                EnrollmentBootstrapCoordinator.STATE_QUARANTINED -> "Enrollment incomplete. This device is quarantined pending administrator recovery."
                                EnrollmentBootstrapCoordinator.STATE_ENROLLED -> "This device is enrolled and managed by EduGD."
                                else -> "Attempt restricted. This application is under EduGD management."
                            },
                            style = MaterialTheme.typography.headlineSmall,
                            textAlign = TextAlign.Center
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        lifecycleScope.launch {
            val kioskEnabled = withContext(Dispatchers.IO) {
                val envelope = DpcDatabase.getDatabase(applicationContext).dpcDao().getActivePolicyEnvelope()
                envelope?.let { DeviceUseSettings.fromPayload(JSONObject(it.payloadJson)).kioskModeEnabled } ?: false
            }
            if (kioskEnabled) {
                runCatching { startLockTask() }
            } else {
                runCatching { stopLockTask() }
            }
        }
    }
}
