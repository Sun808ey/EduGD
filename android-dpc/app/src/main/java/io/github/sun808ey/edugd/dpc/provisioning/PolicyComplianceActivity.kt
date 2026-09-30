package io.github.sun808ey.edugd.dpc.provisioning

import android.app.Activity
import android.os.Bundle
import io.github.sun808ey.edugd.dpc.policy.PolicyApplicationCoordinator

class PolicyComplianceActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val applied = PolicyApplicationCoordinator.from(this)
            .applyBootstrapOrQuarantine()
        setResult(if (applied) RESULT_OK else RESULT_CANCELED)
        finish()
    }
}
