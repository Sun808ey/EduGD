export interface AndroidProvisioningInput {
  apiOrigin: string
  pairingToken: string
  serverSigningKeyId: string
  serverSigningPublicKey: string
  serverSigningKeyFingerprint: string
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
  serverSigningKeyId: string
  serverSigningPublicKey: string
  serverSigningKeyFingerprint: string
}

export type AndroidProvisioningPayload = Record<string, string | number | boolean | Record<string, string>>

const COMPONENT_PATTERN = /^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*\/\.?[A-Za-z][A-Za-z0-9_$.]*(?:\.[A-Za-z][A-Za-z0-9_$]*)*$/
const CHECKSUM_PATTERN = /^[A-Za-z0-9_-]{43}$/
const KEY_ID_PATTERN = /^[A-Za-z0-9._-]{1,128}$/
const PUBLIC_KEY_PATTERN = /^[A-Za-z0-9_-]{43}$/
const FINGERPRINT_PATTERN = /^[0-9a-f]{64}$/

function decodeBase64Url(value: string): Uint8Array {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4)
  return Uint8Array.from(atob(padded), (character) => character.charCodeAt(0))
}

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
  if (!KEY_ID_PATTERN.test(input.serverSigningKeyId)) throw new Error('The DPC signing key ID is invalid.')
  if (!PUBLIC_KEY_PATTERN.test(input.serverSigningPublicKey)) throw new Error('The DPC signing public key is invalid.')
  if (!FINGERPRINT_PATTERN.test(input.serverSigningKeyFingerprint)) throw new Error('The DPC signing key fingerprint is invalid.')
}

export async function verifyAndroidProvisioningTrustAnchor(input: Pick<AndroidProvisioningInput, 'serverSigningPublicKey' | 'serverSigningKeyFingerprint'>): Promise<void> {
  if (!PUBLIC_KEY_PATTERN.test(input.serverSigningPublicKey) || !FINGERPRINT_PATTERN.test(input.serverSigningKeyFingerprint)) {
    throw new Error('The DPC signing trust anchor is invalid.')
  }
  const publicKey = decodeBase64Url(input.serverSigningPublicKey)
  const publicKeyBuffer = publicKey.buffer.slice(publicKey.byteOffset, publicKey.byteOffset + publicKey.byteLength) as ArrayBuffer
  const digest = await crypto.subtle.digest('SHA-256', publicKeyBuffer)
  const actualFingerprint = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join('')
  if (actualFingerprint !== input.serverSigningKeyFingerprint) {
    throw new Error('The DPC signing key fingerprint does not match the public key.')
  }
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
      server_signing_key_id: input.serverSigningKeyId,
      server_signing_public_key: input.serverSigningPublicKey,
      server_signing_key_fingerprint: input.serverSigningKeyFingerprint,
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
  const serverSigningKeyId = environment.VITE_DPC_SERVER_SIGNING_KEY_ID
  const serverSigningPublicKey = environment.VITE_DPC_SERVER_SIGNING_PUBLIC_KEY
  const serverSigningKeyFingerprint = environment.VITE_DPC_SERVER_SIGNING_KEY_FINGERPRINT
  if (!apkUrl && !componentName && !signatureChecksum && !rawVersionCode && !serverSigningKeyId && !serverSigningPublicKey && !serverSigningKeyFingerprint) return undefined
  if (!apkUrl || !componentName || !signatureChecksum || !rawVersionCode || !/^\d+$/.test(rawVersionCode) || !serverSigningKeyId || !serverSigningPublicKey || !serverSigningKeyFingerprint) throw new Error('DPC provisioning configuration is incomplete, including the server signing trust anchor.')
  const minimumVersionCode = Number(rawVersionCode)
  validateAndroidProvisioningInput({
    apiOrigin: 'https://api.example.invalid',
    pairingToken: '00000000-0000-4000-8000-000000000000.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    serverSigningKeyId,
    serverSigningPublicKey,
    serverSigningKeyFingerprint,
    deviceAdminComponentName: componentName,
    packageDownloadLocation: apkUrl,
    signatureChecksum,
    minimumVersionCode,
  })
  return { deviceAdminComponentName: componentName, packageDownloadLocation: apkUrl, signatureChecksum, minimumVersionCode, serverSigningKeyId, serverSigningPublicKey, serverSigningKeyFingerprint }
}
