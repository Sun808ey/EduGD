package io.github.sun808ey.edugd.dpc

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.github.sun808ey.edugd.dpc.admin.DevicePolicyController
import io.github.sun808ey.edugd.dpc.audit.AuditChain
import io.github.sun808ey.edugd.dpc.policy.PolicyRepository

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dpc = DevicePolicyController(this)
        val repository = PolicyRepository(this)
        val auditChain = AuditChain(this)

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    var isDeviceOwner by remember { mutableStateOf(dpc.isDeviceOwner()) }
                    var policyVersion by remember { mutableStateOf(repository.currentPolicyVersion) }
                    var auditHash by remember { mutableStateOf(auditChain.getLastHash()) }

                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(text = "EduGD DPC Status", style = MaterialTheme.typography.headlineMedium)
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(text = "Device Owner Active: $isDeviceOwner")
                                Text(text = "Current Policy Version: $policyVersion")
                                Text(text = "Audit Chain Head Hash: ${auditHash.take(16)}...")
                            }
                        }
                        Button(onClick = {
                            isDeviceOwner = dpc.isDeviceOwner()
                            policyVersion = repository.currentPolicyVersion
                            auditHash = auditChain.getLastHash()
                        }) {
                            Text(text = "Refresh Status")
                        }
                    }
                }
            }
        }
    }
}
