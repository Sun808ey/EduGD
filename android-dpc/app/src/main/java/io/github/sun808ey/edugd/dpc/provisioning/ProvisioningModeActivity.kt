package io.github.sun808ey.edugd.dpc.provisioning

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController

class ProvisioningModeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dpc = DevicePolicyController(this)
        if (dpc.isDeviceOwner()) {
            dpc.applyDefaultRestrictions()
            val intent = Intent(this, PolicyComplianceActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
            }
            startActivity(intent)
        } else {
            setResult(RESULT_CANCELED)
        }
        finish()
    }
}
