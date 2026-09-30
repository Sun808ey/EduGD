package io.github.sun808ey.edugd.dpc.provisioning

import android.app.Activity
import android.app.admin.DevicePolicyManager
import android.content.Intent
import android.os.Bundle
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController

class ProvisioningModeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (intent.action == DevicePolicyManager.ACTION_GET_PROVISIONING_MODE) {
            setResult(
                RESULT_OK,
                Intent().putExtra(
                    DevicePolicyManager.EXTRA_PROVISIONING_MODE,
                    DevicePolicyManager.PROVISIONING_MODE_FULLY_MANAGED_DEVICE,
                ),
            )
            finish()
            return
        }
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
