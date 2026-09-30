package io.github.sun808ey.edugd.dpc.vpn

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import androidx.core.app.NotificationCompat
import io.github.sun808ey.edugd.dpc.audit.AuditChain

class EduFilteringVpnService : VpnService() {
    private var tunnel: ParcelFileDescriptor? = null
    private var worker: Thread? = null

    companion object {
        const val CHANNEL_ID = "edugd_vpn_channel"
        const val NOTIFICATION_ID = 1001
    }

    override fun onStartCommand(
        intent: Intent?,
        flags: Int,
        startId: Int,
    ): Int {
        startForegroundServiceNotification()
        if (tunnel == null) {
            try {
                tunnel = Builder()
                    .setSession("EduGD educational filter")
                    .addAddress("10.8.0.2", 32)
                    .addRoute("0.0.0.0", 0)
                    .addDnsServer("10.8.0.1")
                    // Do not call allowBypass().
                    .establish()
                    ?: error("Android refused the filtering VPN")
                worker = startPacketEngine(tunnel!!)
            } catch (e: Exception) {
                e.printStackTrace()
                AuditChain(this).appendEvent("vpn_lockdown_failed", metadata = mapOf("error" to (e.message ?: "tunnel_failed")))
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        worker?.interrupt()
        tunnel?.close()
        tunnel = null
        super.onDestroy()
    }

    private fun startPacketEngine(
        fd: ParcelFileDescriptor,
    ): Thread {
        val thread = Thread {
            try {
                val buffer = ByteArray(32767)
                val inputStream = java.io.FileInputStream(fd.fileDescriptor)
                while (!Thread.currentThread().isInterrupted) {
                    val length = inputStream.read(buffer)
                    if (length > 0) {
                        // Fail-closed drop / control-plane stub
                    }
                }
            } catch (e: Exception) {
                // Interrupted or closed
            }
        }
        thread.start()
        return thread
    }

    private fun startForegroundServiceNotification() {
        val notificationManager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "EduGD Filtering VPN",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Always-on educational filtering VPN for school device"
            }
            notificationManager.createNotificationChannel(channel)
        }

        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("EduGD VPN Active")
            .setContentText("Always-on educational web filtering is enforcing policy")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }
}
