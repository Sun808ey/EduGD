package io.github.sun808ey.edugd.dpc

import android.app.Application
import io.github.sun808ey.edugd.dpc.crypto.DeviceKeyStore

class EduDpcApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        DeviceKeyStore.ensureKeyExists()
    }
}
