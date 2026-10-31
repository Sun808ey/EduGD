package io.github.sun808ey.edugd.dpc

import android.app.Application
class EduDpcApplication : Application() {
    // Keystore initialization is performed by the background enrollment,
    // synchronization, and audit paths. Keeping it off the application main
    // thread prevents first-launch ANRs while preserving key creation timing.
}
