package io.github.sun808ey.edugd.dpc.provisioning

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import io.github.sun808ey.edugd.dpc.MainActivity
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController

class PolicyComplianceActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dpc = DevicePolicyController(this)
        if (dpc.isDeviceOwner()) {
            dpc.applyDefaultRestrictions()
            Toast.makeText(this, "EduGD Policy Compliance Complete", Toast.LENGTH_LONG).show()
        }
        val intent = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        }
        startActivity(intent)
        finish()
    }
}
