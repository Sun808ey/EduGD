package io.github.sun808ey.edugd.dpc.provisioning

import android.app.Activity
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentBootstrapCoordinator
import io.github.sun808ey.edugd.dpc.policy.PolicyApplicationCoordinator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class PolicyComplianceActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        lifecycleScope.launch {
            val applied = withContext(Dispatchers.IO) {
                PolicyApplicationCoordinator.from(this@PolicyComplianceActivity).applyBootstrapOrQuarantine()
            }
            val extras = EnrollmentBootstrapCoordinator.provisioningExtras(intent.extras)
            val enrolled = if (extras != null) {
                withContext(Dispatchers.IO) { EnrollmentBootstrapCoordinator(applicationContext).enroll(extras) }
            } else {
                true
            }
            setResult(if (applied && enrolled) RESULT_OK else RESULT_CANCELED)
            finish()
        }
    }
}
