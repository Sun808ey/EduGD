import { describe, expect, it } from 'vitest'
import { buildAndroidProvisioningPayload, serializeAndroidProvisioningPayload, validateAndroidProvisioningInput } from './android-provisioning'

const validInput = {
  apiOrigin: 'https://api.example.test',
  pairingToken: '00000000-0000-4000-8000-000000000000.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
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
})
