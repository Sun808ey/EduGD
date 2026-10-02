package io.github.sun808ey.edugd.dpc.sync

import io.github.sun808ey.edugd.dpc.crypto.DeviceSigningIdentity
class StateSyncClient(private val serverBaseUrl: String, private val deviceUuid: String, private val credentialUuid: String, private val identity: DeviceSigningIdentity, private val trustedSigningKeyId: String, private val trustedSigningPublicKey: String, private val lastAcceptedServerTimeEpochSeconds: Long) {
    fun fetchState(): V3StateResponse? = BackendIntegrationClient(
        serverBaseUrl,
        deviceUuid,
        credentialUuid,
        identity,
        trustedSigningKeyId,
        trustedSigningPublicKey,
        lastAcceptedServerTimeEpochSeconds,
    ).fetchV3State()

    fun acknowledge(policyUuid: String?, revisionUuid: String?, outcome: String, errorCode: String? = null): Boolean = BackendIntegrationClient(
        serverBaseUrl, deviceUuid, credentialUuid, identity, trustedSigningKeyId, trustedSigningPublicKey, lastAcceptedServerTimeEpochSeconds
    ).uploadPolicyAcknowledgement(policyUuid, revisionUuid, outcome, errorCode)
}
