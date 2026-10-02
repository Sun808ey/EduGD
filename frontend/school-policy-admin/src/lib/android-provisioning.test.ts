import { describe, expect, it } from 'vitest'
import { buildAndroidProvisioningPayload, resolveAndroidProvisioningConfig, serializeAndroidProvisioningPayload, validateAndroidProvisioningInput, verifyAndroidProvisioningTrustAnchor } from './android-provisioning'

const validInput = {
  apiOrigin: 'https://api.example.test',
  pairingToken: '00000000-0000-4000-8000-000000000000.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
  serverSigningKeyId: 'dpc-v3-1',
  serverSigningPublicKey: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
  serverSigningKeyFingerprint: '66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925',
  deviceAdminComponentName: 'io.github.sun808ey.edugd.dpc/.admin.AdminReceiver',
  packageDownloadLocation: 'https://downloads.example.test/edugd-dpc.apk',
  signatureChecksum: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
  minimumVersionCode: 1,
}

describe('Android provisioning payloads', () => {
  it('builds the fully managed setup-wizard payload with admin extras', () => {
    const payload = buildAndroidProvisioningPayload(validInput)
    expect(payload['android.app.extra.PROVISIONING_MODE']).toBe('android.app.extra.PROVISIONING_MODE_FULLY_MANAGED_DEVICE')
    expect(payload['android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE']).toEqual({
      api_origin: validInput.apiOrigin,
      pairing_token: validInput.pairingToken,
      server_signing_key_id: validInput.serverSigningKeyId,
      server_signing_public_key: validInput.serverSigningPublicKey,
      server_signing_key_fingerprint: validInput.serverSigningKeyFingerprint,
    })
    expect(payload).not.toHaveProperty('android.app.extra.PROVISIONING_ALLOW_OFFLINE')
  })

  it('serializes deterministically without adding an envelope', () => {
    expect(JSON.parse(serializeAndroidProvisioningPayload(validInput))).toEqual(buildAndroidProvisioningPayload(validInput))
  })

  it.each([
    ['http://api.example.test', 'api origin'],
    ['https://api.example.test/api/v1', 'api origin path'],
  ])('rejects an unsafe %s', (apiOrigin) => {
    expect(() => validateAndroidProvisioningInput({ ...validInput, apiOrigin })).toThrow()
  })

  it('rejects malformed APK, checksum, component, token, and version values', () => {
    expect(() => validateAndroidProvisioningInput({ ...validInput, packageDownloadLocation: 'https://downloads.example.test/app.apk?token=secret' })).toThrow()
    expect(() => validateAndroidProvisioningInput({ ...validInput, signatureChecksum: 'not-a-checksum' })).toThrow()
    expect(() => validateAndroidProvisioningInput({ ...validInput, deviceAdminComponentName: 'not-a-component' })).toThrow()
    expect(() => validateAndroidProvisioningInput({ ...validInput, pairingToken: 'token' })).toThrow()
    expect(() => validateAndroidProvisioningInput({ ...validInput, minimumVersionCode: 0 })).toThrow()
  })

  it.each([
    ['serverSigningKeyId', 'bad key'],
    ['serverSigningPublicKey', 'bad key'],
    ['serverSigningKeyFingerprint', 'A'.repeat(64)],
  ] as const)('rejects malformed %s', (field, value) => {
    expect(() => validateAndroidProvisioningInput({ ...validInput, [field]: value })).toThrow()
  })

  it('rejects a partial trust anchor', () => {
    expect(() => validateAndroidProvisioningInput({ ...validInput, serverSigningPublicKey: '' })).toThrow()
  })

  it('verifies that the configured fingerprint matches the public key', async () => {
    await expect(verifyAndroidProvisioningTrustAnchor(validInput)).resolves.toBeUndefined()
    await expect(verifyAndroidProvisioningTrustAnchor({ ...validInput, serverSigningKeyFingerprint: 'a'.repeat(64) })).rejects.toThrow('does not match')
  })

  it('requires a complete, valid trust anchor in deployment configuration', () => {
    const environment = {
      VITE_DPC_APK_DOWNLOAD_URL: validInput.packageDownloadLocation,
      VITE_DPC_ADMIN_COMPONENT: validInput.deviceAdminComponentName,
      VITE_DPC_SIGNATURE_CHECKSUM: validInput.signatureChecksum,
      VITE_DPC_MIN_VERSION_CODE: String(validInput.minimumVersionCode),
      VITE_DPC_SERVER_SIGNING_KEY_ID: validInput.serverSigningKeyId,
      VITE_DPC_SERVER_SIGNING_PUBLIC_KEY: validInput.serverSigningPublicKey,
      VITE_DPC_SERVER_SIGNING_KEY_FINGERPRINT: validInput.serverSigningKeyFingerprint,
    } as unknown as ImportMetaEnv
    expect(resolveAndroidProvisioningConfig(environment)).toMatchObject({ serverSigningKeyId: validInput.serverSigningKeyId })
    expect(() => resolveAndroidProvisioningConfig({ ...environment, VITE_DPC_SERVER_SIGNING_PUBLIC_KEY: '' })).toThrow('incomplete')
  })
})
