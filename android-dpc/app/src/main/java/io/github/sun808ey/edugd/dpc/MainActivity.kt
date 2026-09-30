package io.github.sun808ey.edugd.dpc

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentBootstrapCoordinator

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
}
