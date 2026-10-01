export interface AndroidProvisioningInput {
  apiOrigin: string
  pairingToken: string
  deviceAdminComponentName: string
  packageDownloadLocation: string
  signatureChecksum: string
  minimumVersionCode: number
}

export interface AndroidProvisioningConfig {
  deviceAdminComponentName: string
  packageDownloadLocation: string
  signatureChecksum: string
  minimumVersionCode: number
}

export type AndroidProvisioningPayload = Record<string, string | number | boolean | Record<string, string>>

const COMPONENT_PATTERN = /^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*\/\.?[A-Za-z][A-Za-z0-9_$.]*(?:\.[A-Za-z][A-Za-z0-9_$]*)*$/
const CHECKSUM_PATTERN = /^[A-Za-z0-9_-]{43}$/

function requireHttpsUrl(value: string, message: string): URL {
  if (!value || value !== value.trim()) throw new Error(message)
  let url: URL
  try {
    url = new URL(value)
  } catch {
    throw new Error(message)
  }
  if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || url.search || url.hash) throw new Error(message)
  return url
}

export function validateAndroidProvisioningInput(input: AndroidProvisioningInput): void {
  const apiOrigin = requireHttpsUrl(input.apiOrigin, 'The DPC API origin must be an HTTPS origin.')
  if (apiOrigin.pathname !== '/') throw new Error('The DPC API origin must not contain a path.')
  requireHttpsUrl(input.packageDownloadLocation, 'The DPC APK URL must be an HTTPS URL without query parameters.')
  if (!COMPONENT_PATTERN.test(input.deviceAdminComponentName)) throw new Error('The DPC admin component name is invalid.')
  if (!CHECKSUM_PATTERN.test(input.signatureChecksum)) throw new Error('The DPC signing certificate checksum is invalid.')
  if (!Number.isSafeInteger(input.minimumVersionCode) || input.minimumVersionCode < 1) throw new Error('The DPC minimum version code must be a positive integer.')
  if (!input.pairingToken || input.pairingToken.length > 80 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(input.pairingToken)) throw new Error('The one-time pairing token is invalid.')
}

export function buildAndroidProvisioningPayload(input: AndroidProvisioningInput): AndroidProvisioningPayload {
  validateAndroidProvisioningInput(input)
  return {
    'android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME': input.deviceAdminComponentName,
    'android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION': input.packageDownloadLocation,
    'android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM': input.signatureChecksum,
    'android.app.extra.PROVISIONING_DEVICE_ADMIN_MINIMUM_VERSION_CODE': input.minimumVersionCode,
    'android.app.extra.PROVISIONING_MODE': 'android.app.extra.PROVISIONING_MODE_FULLY_MANAGED_DEVICE',
    'android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE': {
      api_origin: input.apiOrigin,
      pairing_token: input.pairingToken,
    },
  }
}

export function serializeAndroidProvisioningPayload(input: AndroidProvisioningInput): string {
  return JSON.stringify(buildAndroidProvisioningPayload(input))
}

export function resolveAndroidProvisioningConfig(environment: ImportMetaEnv = import.meta.env): AndroidProvisioningConfig | undefined {
  const apkUrl = environment.VITE_DPC_APK_DOWNLOAD_URL
  const componentName = environment.VITE_DPC_ADMIN_COMPONENT
  const signatureChecksum = environment.VITE_DPC_SIGNATURE_CHECKSUM
  const rawVersionCode = environment.VITE_DPC_MIN_VERSION_CODE
  if (!apkUrl && !componentName && !signatureChecksum && !rawVersionCode) return undefined
  if (!apkUrl || !componentName || !signatureChecksum || !rawVersionCode || !/^\d+$/.test(rawVersionCode)) throw new Error('DPC provisioning configuration is incomplete.')
  const minimumVersionCode = Number(rawVersionCode)
  validateAndroidProvisioningInput({
    apiOrigin: 'https://api.example.invalid',
    pairingToken: '00000000-0000-4000-8000-000000000000.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    deviceAdminComponentName: componentName,
    packageDownloadLocation: apkUrl,
    signatureChecksum,
    minimumVersionCode,
  })
  return { deviceAdminComponentName: componentName, packageDownloadLocation: apkUrl, signatureChecksum, minimumVersionCode }
}
