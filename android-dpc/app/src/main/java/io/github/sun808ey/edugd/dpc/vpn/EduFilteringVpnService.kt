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
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import org.json.JSONObject

class EduFilteringVpnService : VpnService() {
    private var tunnel: ParcelFileDescriptor? = null
    private var worker: Thread? = null
    private var policy: WebFilterSettings? = null

    companion object {
        const val CHANNEL_ID = "edugd_vpn_channel"
        const val NOTIFICATION_ID = 1001
        const val ACTION_STOP = "io.github.sun808ey.edugd.dpc.vpn.STOP"
        const val EXTRA_PAYLOAD_JSON = "payload_json"
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) { stopSelf(); return START_NOT_STICKY }
        intent?.getStringExtra(EXTRA_PAYLOAD_JSON)?.let { policy = WebFilterSettings.fromPayload(JSONObject(it)) }
        val activePolicy = policy
        if (activePolicy == null || activePolicy.browserPackages.isEmpty()) {
            AuditChain(this).appendEvent("vpn_lockdown_failed", metadata = mapOf("error" to "browser_scope_missing"))
            stopSelf()
            return START_NOT_STICKY
        }
        startForegroundServiceNotification()
        if (tunnel == null) try {
            val builder = Builder().setSession("EduGD browser DNS filter")
                .addAddress("10.8.0.2", 32).addRoute("10.8.0.1", 32).addDnsServer("10.8.0.1")
            val validPackages = activePolicy.browserPackages.filter { packageName ->
                runCatching { packageManager.getPackageInfo(packageName, 0); true }.getOrDefault(false)
            }
            require(validPackages.isNotEmpty()) { "browser_scope_packages_not_installed" }
            validPackages.forEach(builder::addAllowedApplication)
            tunnel = builder.establish() ?: error("Android refused the filtering VPN")
            AuditChain(this).appendEvent("vpn_started", metadata = mapOf("scope" to "browser_dns"))
            worker = startPacketEngine(tunnel!!, activePolicy)
        } catch (e: Exception) {
            AuditChain(this).appendEvent("vpn_lockdown_failed", metadata = mapOf("error" to (e.message ?: "tunnel_failed")))
            stopSelf()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        worker?.interrupt(); tunnel?.close(); tunnel = null; worker = null; super.onDestroy()
    }

    private fun startPacketEngine(fd: ParcelFileDescriptor, settings: WebFilterSettings): Thread {
        val thread = Thread {
            val input = FileInputStream(fd.fileDescriptor)
            val output = FileOutputStream(fd.fileDescriptor)
            val buffer = ByteArray(32767)
            try {
                while (!Thread.currentThread().isInterrupted) {
                    val length = input.read(buffer)
                    if (length <= 0) continue
                    handleIpv4Packet(buffer, length, settings)?.let(output::write)
                }
            } catch (_: Exception) { } finally { input.close(); output.close() }
        }
        thread.name = "EduGD-DnsFilter"; thread.start(); return thread
    }

    private fun handleIpv4Packet(packet: ByteArray, length: Int, settings: WebFilterSettings): ByteArray? {
        if (length < 28 || packet[0].toInt() ushr 4 != 4) return null
        val headerLength = (packet[0].toInt() and 0x0f) * 4
        if (headerLength < 20 || length < headerLength + 8 || packet[9].toInt() and 0xff != 17) return null
        val destinationPort = u16(packet, headerLength + 2)
        if (destinationPort != 53) return null
        val sourcePort = u16(packet, headerLength)
        val dns = packet.copyOfRange(headerLength + 8, length)
        val question = parseQuestion(dns) ?: return null
        val normalized = WebFilterSettings.normalizeDomain(question.name) ?: return null
        val (action, rule) = settings.decision(normalized)
        val response = if (action == "block") {
            AuditChain(this).appendEvent("blocked_domain", metadata = mapOf("domain_hash" to WebFilterSettings.domainHash(normalized), "rule_id" to (rule?.ruleId ?: "default"), "outcome" to "blocked"))
            blockedResponse(dns, question.questionEnd)
        } else queryUpstream(dns) ?: return null
        return wrapUdpIpv4(packet, headerLength, sourcePort, destinationPort, response)
    }

    private fun queryUpstream(query: ByteArray): ByteArray? {
        val socket = DatagramSocket()
        return try {
            if (!protect(socket)) return null
            socket.soTimeout = 1500
            socket.send(DatagramPacket(query, query.size, InetAddress.getByName("1.1.1.1"), 53))
            val response = ByteArray(4096)
            val received = DatagramPacket(response, response.size)
            socket.receive(received)
            response.copyOf(received.length)
        } finally { socket.close() }
    }

    private data class Question(val name: String, val questionEnd: Int)

    private fun parseQuestion(dns: ByteArray): Question? {
        if (dns.size < 17 || u16(dns, 4) != 1) return null
        var index = 12; val labels = mutableListOf<String>()
        while (index < dns.size) {
            val size = dns[index++].toInt() and 0xff
            if (size == 0) break
            if (size > 63 || index + size > dns.size) return null
            labels += String(dns, index, size, Charsets.US_ASCII); index += size
        }
        if (index + 4 > dns.size || labels.isEmpty()) return null
        return Question(labels.joinToString("."), index + 4)
    }

    private fun blockedResponse(query: ByteArray, questionEnd: Int): ByteArray {
        val response = ByteArray(questionEnd)
        System.arraycopy(query, 0, response, 0, 2)
        putU16(response, 2, (u16(query, 2) or 0x8000) and 0xfff3 or 3)
        putU16(response, 4, 1)
        System.arraycopy(query, 12, response, 12, questionEnd - 12)
        return response
    }

    private fun wrapUdpIpv4(original: ByteArray, headerLength: Int, sourcePort: Int, destinationPort: Int, payload: ByteArray): ByteArray {
        val result = ByteArray(headerLength + 8 + payload.size)
        System.arraycopy(original, 0, result, 0, headerLength)
        System.arraycopy(original, 12, result, 16, 4); System.arraycopy(original, 16, result, 12, 4)
        putU16(result, 2, result.size); result[8] = 64; result[9] = 17; putU16(result, 10, 0); putU16(result, 10, checksum(result, 0, headerLength))
        putU16(result, headerLength, destinationPort); putU16(result, headerLength + 2, sourcePort); putU16(result, headerLength + 4, 8 + payload.size); putU16(result, headerLength + 6, 0)
        System.arraycopy(payload, 0, result, headerLength + 8, payload.size)
        putU16(result, headerLength + 6, udpChecksum(result, headerLength, payload.size))
        return result
    }

    private fun udpChecksum(packet: ByteArray, offset: Int, payloadSize: Int): Int {
        var sum = 0L
        for (index in 12 until 20 step 2) sum += u16(packet, index)
        sum += 17L + 8 + payloadSize; sum += u16(packet, offset) + u16(packet, offset + 2)
        for (index in offset + 8 until offset + 8 + payloadSize step 2) sum += ((packet[index].toInt() and 0xff) shl 8) or (if (index + 1 < packet.size) packet[index + 1].toInt() and 0xff else 0)
        while (sum ushr 16 != 0L) sum = (sum and 0xffff) + (sum ushr 16)
        return (sum.inv() and 0xffff).toInt()
    }

    private fun checksum(bytes: ByteArray, offset: Int, length: Int): Int {
        var sum = 0L
        for (index in offset until offset + length step 2) sum += u16(bytes, index)
        while (sum ushr 16 != 0L) sum = (sum and 0xffff) + (sum ushr 16)
        return (sum.inv() and 0xffff).toInt()
    }

    private fun u16(bytes: ByteArray, index: Int): Int = ((bytes[index].toInt() and 0xff) shl 8) or (bytes[index + 1].toInt() and 0xff)
    private fun putU16(bytes: ByteArray, index: Int, value: Int) { bytes[index] = (value ushr 8).toByte(); bytes[index + 1] = value.toByte() }

    private fun startForegroundServiceNotification() {
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) manager.createNotificationChannel(NotificationChannel(CHANNEL_ID, "EduGD Filtering VPN", NotificationManager.IMPORTANCE_LOW))
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID).setContentTitle("EduGD browser filter active").setContentText("Configured browser domains are being filtered").setSmallIcon(android.R.drawable.ic_menu_compass).setOngoing(true).build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) startForeground(NOTIFICATION_ID, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE) else startForeground(NOTIFICATION_ID, notification)
    }
}
