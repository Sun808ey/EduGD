package io.github.sun808ey.edugd.dpc.provisioning

import android.app.Activity
import android.os.Bundle
import io.github.sun808ey.edugd.dpc.enrollment.EnrollmentBootstrapCoordinator
import io.github.sun808ey.edugd.dpc.policy.PolicyApplicationCoordinator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class PolicyComplianceActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val applied = PolicyApplicationCoordinator.from(this).applyBootstrapOrQuarantine()
        val extras = EnrollmentBootstrapCoordinator.provisioningExtras(intent.extras)
        if (extras != null) {
            CoroutineScope(Dispatchers.IO).launch { EnrollmentBootstrapCoordinator(applicationContext).enroll(extras) }
        }
        setResult(if (applied) RESULT_OK else RESULT_CANCELED)
        finish()
    }
}
