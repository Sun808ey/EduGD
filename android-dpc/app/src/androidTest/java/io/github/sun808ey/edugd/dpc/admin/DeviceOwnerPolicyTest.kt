package io.github.sun808ey.edugd.dpc.admin

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertNotNull
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DeviceOwnerPolicyTest {
    @Test
    fun testDevicePolicyControllerInit() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val dpc = DevicePolicyController(context)
        assertNotNull(dpc)
    }
}
