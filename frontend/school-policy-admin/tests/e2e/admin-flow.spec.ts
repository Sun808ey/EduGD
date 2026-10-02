import { AxeBuilder } from '@axe-core/playwright'
import { expect, test, type Page, type TestInfo } from '@playwright/test'

const admin = { username: 'local.e2e.admin', password: 'LocalE2EAdmin!2026' }
const readonly = { username: 'local.e2e.reader', password: 'LocalE2EReader!2026' }
type LiveRequestInit = { method?: string; body?: string; headers?: Record<string, string> }

async function signIn(page: Page, credentials = admin) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(credentials.username)
  await page.getByLabel('Password').fill(credentials.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Device policy at a glance' })).toBeVisible()
}

async function openNavigation(page: Page) {
  const menu = page.getByRole('button', { name: 'Open navigation' })
  if (await menu.isVisible()) await menu.click()
}

async function navigateInApp(page: Page, path: string) {
  await page.evaluate((value) => {
    window.history.pushState({}, '', value)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, path)
}

async function liveApi(page: Page, token: string, path: string, init: LiveRequestInit = {}) {
  return page.evaluate(async ({ path, token, init }) => {
    const response = await fetch(`/api/v1${path}`, {
      ...init,
      headers: { Authorization: token, 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    })
    const text = await response.text()
    return { status: response.status, body: text ? JSON.parse(text) as Record<string, unknown> : null }
  }, { path, token, init })
}

test('uses the live Flask API for the administrator dashboard lifecycle', async ({ page }) => {
  const apiRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/admin/')) apiRequests.push(request.url())
  })
  await signIn(page)
  await expect(page.getByText('Managed devices').locator('..').getByText(/^\d+$/)).toBeVisible()
  await openNavigation(page)
  await page.getByRole('link', { name: 'Devices', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await expect(page.getByText('22222222-2222-4222-8222-222222222222', { exact: true })).toBeVisible()
  await openNavigation(page)
  await page.getByRole('link', { name: 'Policies' }).click()
  await expect(page.getByRole('heading', { name: /Policies/ })).toBeVisible()
  await expect(page.getByText('Local E2E policy')).toBeVisible()
  await openNavigation(page)
  await page.getByRole('link', { name: /Audit/i }).click()
  await expect(page.getByRole('heading', { name: 'Audit events' })).toBeVisible()
  expect(apiRequests.length).toBeGreaterThan(0)
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 })
})

test('loads live deep links and administrator management', async ({ page }) => {
  await signIn(page)
  await page.getByRole('link', { name: 'Devices and enrollment' }).click()
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await navigateInApp(page, '/dashboard')
  await expect(page.getByRole('heading', { name: 'Device policy at a glance' })).toBeVisible()
  await page.getByRole('link', { name: 'Policies and assignments' }).click()
  await expect(page.getByRole('heading', { name: /Policies/ })).toBeVisible()
  await navigateInApp(page, '/devices/22222222-2222-4222-8222-222222222222')
  await expect(page.getByRole('heading', { name: '22222222-2222-4222-8222-222222222222' })).toBeVisible()
  await navigateInApp(page, '/administrators')
  await expect(page.getByRole('heading', { name: 'Administrators' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Create administrator' })).toBeVisible()
  await navigateInApp(page, '/applications')
  await expect(page.getByRole('heading', { name: 'Managed applications' })).toBeVisible()
  await navigateInApp(page, '/translations')
  await expect(page.getByRole('heading', { name: 'Approved-content translation' })).toBeVisible()
  await navigateInApp(page, '/logs')
  await expect(page.getByRole('heading', { name: 'Audit events' })).toBeVisible()
})

test('checks live browser security boundaries and direct CORS behavior', async ({ page }) => {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await signIn(page)
  const frontend = await page.request.get('/login')
  expect(frontend.status()).toBe(200)
  const headers = frontend.headers()
  expect(headers['x-content-type-options']).toBe('nosniff')
  expect(headers['x-frame-options']).toBe('DENY')
  expect(headers['referrer-policy']).toBe('no-referrer')
  const allowed = await page.request.fetch('http://127.0.0.1:5000/api/v1/admin/auth/me', {
    method: 'OPTIONS',
    headers: { Origin: 'http://127.0.0.1:4173', 'Access-Control-Request-Method': 'GET' },
  })
  expect(allowed.status()).toBe(204)
  expect(allowed.headers()['access-control-allow-origin']).toBe('http://127.0.0.1:4173')
  const rejected = await page.request.fetch('http://127.0.0.1:5000/api/v1/admin/auth/me', {
    method: 'OPTIONS',
    headers: { Origin: 'http://unapproved.invalid', 'Access-Control-Request-Method': 'GET' },
  })
  expect(rejected.status()).toBe(403)
  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])
})

test('rejects unsafe localhost QR origins without persisting the token', async ({ page }) => {
  await signIn(page)
  await navigateInApp(page, '/devices')
  await expect(page.getByRole('heading', { name: 'Enrollment tokens' })).toBeVisible()
  await page.getByRole('button', { name: 'Issue token' }).click()
  await page.getByLabel('Reason').fill('live QR serialization verification')
  await page.getByRole('button', { name: 'Issue token', exact: true }).click()
  const pairingToken = await page.getByText(/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/).textContent()
  expect(pairingToken).toBeTruthy()
  await page.getByRole('button', { name: 'Generate QR' }).click()
  const qrDialog = page.getByRole('dialog').last()
  await expect(qrDialog.getByRole('heading', { name: 'Android enrollment QR' })).toBeVisible()
  await expect(qrDialog.getByRole('alert')).toContainText(/HTTPS origin|Invalid URL/i)
  await expect(qrDialog.locator('svg[aria-label="Android device enrollment QR code"]')).toHaveCount(0)
  expect(await qrDialog.textContent()).not.toContain(pairingToken as string)
  await qrDialog.getByRole('button', { name: 'Close' }).click()
  await expect(page.getByText(pairingToken as string, { exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: 'Close' }).click()
  await expect(page.getByText(pairingToken as string, { exact: true })).toHaveCount(0)
  expect(await page.evaluate(async () => ({ local: localStorage.length, session: sessionStorage.length, indexed: (await indexedDB.databases()).length }))).toEqual({ local: 0, session: 0, indexed: 0 })
})

test('enforces live permission boundaries', async ({ page }) => {
  const captured: string[] = []
  page.on('request', (request) => {
    const value = request.headers().authorization
    if (value) captured.push(value)
  })
  await signIn(page, readonly)
  await expect(page.getByRole('link', { name: 'Administrators' })).toHaveCount(0)
  await navigateInApp(page, '/administrators')
  await expect(page.getByRole('alert')).toContainText(/does not have permission/i)
  const token = captured.at(-1)
  expect(token).toMatch(/^Bearer /)
  const status = await page.evaluate(async (value) => {
    const response = await fetch('/api/v1/admin/administrators', {
      method: 'POST',
      headers: { Authorization: value, 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'forbidden.e2e', display_name: 'Forbidden', password: 'ForbiddenE2E!2026', operator_password: 'not-used-after-authorization', reason: 'live forbidden request' }),
    })
    return response.status
  }, token as string)
  expect(status).toBe(403)
})

test('creates an administrator through the live dashboard contract', async ({ page }, testInfo: TestInfo) => {
  await signIn(page)
  await navigateInApp(page, '/administrators')
  const username = `local.e2e.${testInfo.project.name}`
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Display name').fill('Local Created Administrator')
  await page.getByLabel('New administrator password').fill('LocalCreated!2026')
  await page.getByLabel('Your operator password').fill(admin.password)
  await page.getByLabel('Reason for granting administrator access').fill('live dashboard verification')
  await page.getByRole('button', { name: 'Create administrator' }).click()
  await expect(page.getByRole('status')).toContainText(username)
  const administrator = page.locator('article').filter({ hasText: username })
  await expect(administrator).toContainText('active')
  await administrator.getByRole('button', { name: 'Revoke sessions' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Your operator password').fill(admin.password)
  await dialog.getByLabel('Reason').fill('live session revocation verification')
  await dialog.getByRole('button', { name: 'Revoke sessions' }).click()
  await expect(page.getByRole('status')).toContainText('revoked sessions')
})

test('handles a real revoked-session 401 without persistent browser credentials', async ({ page }) => {
  await signIn(page)
  const captured: string[] = []
  page.on('request', (request) => {
    const value = request.headers().authorization
    if (value) captured.push(value)
  })
  await navigateInApp(page, '/devices')
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  const token = captured.at(-1)
  expect(token).toMatch(/^Bearer /)
  const logoutStatus = await page.evaluate(async (value) => (await fetch('/api/v1/admin/auth/logout', { method: 'POST', headers: { Authorization: value } })).status, token as string)
  expect(logoutStatus).toBe(200)
  await navigateInApp(page, '/devices/22222222-2222-4222-8222-222222222222')
  await expect(page).toHaveURL(/\/login$/)
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 })
})

test('passes automated accessibility checks against the live dashboard', async ({ page }) => {
  await signIn(page)
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
})

test('executes disposable token, policy, assignment, and Block lifecycle over live HTTP', async ({ page }, testInfo) => {
  await signIn(page)
  const authorization: string[] = []
  page.on('request', (request) => {
    const value = request.headers().authorization
    if (value) authorization.push(value)
  })
  await navigateInApp(page, '/devices')
  await expect.poll(() => authorization.at(-1)).toMatch(/^Bearer /)
  const token = authorization.at(-1)!
  const deviceUuid = '22222222-2222-4222-8222-222222222222'

  const issued = await liveApi(page, token, '/admin/enrollment-tokens', {
    method: 'POST',
    body: JSON.stringify({ reason: `live disposable ${testInfo.project.name}`, bound_device_uuid: null }),
  })
  expect(issued.status).toBe(201)
  const pairingToken = issued.body?.pairing_token
  const tokenUuid = issued.body?.token_uuid
  expect(typeof pairingToken).toBe('string')
  expect(typeof tokenUuid).toBe('string')
  expect(await page.evaluate(async () => ({ local: localStorage.length, session: sessionStorage.length, indexed: (await indexedDB.databases()).length }))).toEqual({ local: 0, session: 0, indexed: 0 })
  expect(await page.context().cookies()).toEqual([])

  const tokenList = await liveApi(page, token, '/admin/enrollment-tokens?page=1&per_page=25')
  expect(tokenList.status).toBe(200)
  expect(JSON.stringify(tokenList.body)).not.toContain(String(pairingToken))

  const revoked = await liveApi(page, token, `/admin/enrollment-tokens/${String(tokenUuid)}/revoke`, {
    method: 'POST',
    body: JSON.stringify({ reason: 'live disposable cleanup' }),
  })
  expect(revoked.status).toBe(200)
  const replayRevoke = await liveApi(page, token, `/admin/enrollment-tokens/${String(tokenUuid)}/revoke`, {
    method: 'POST',
    body: JSON.stringify({ reason: 'replay attempt' }),
  })
  expect(replayRevoke.status).toBe(409)

  const policyList = await liveApi(page, token, '/admin/policies?page=1&per_page=25&status=active')
  expect(policyList.status).toBe(200)
  const policies = policyList.body?.policies as Array<Record<string, unknown>>
  const policyUuid = String(policies[0].policy_uuid)
  const detail = await liveApi(page, token, `/admin/policies/${policyUuid}`)
  expect(detail.status).toBe(200)
  const revisions = await liveApi(page, token, `/admin/policies/${policyUuid}/revisions?page=1&per_page=25`)
  expect(revisions.status).toBe(200)
  const latest = (revisions.body?.revisions as Array<Record<string, unknown>>)[0]
  const payload = structuredClone(latest.payload) as Record<string, unknown>
  const blockedApps = Array.isArray(payload.blocked_apps) ? payload.blocked_apps.filter((value): value is string => typeof value === 'string') : []
  payload.blocked_apps = [...blockedApps, `org.example.${testInfo.project.name.replace(/[^a-z0-9]/gi, '')}`]
  const revision = await liveApi(page, token, `/admin/policies/${policyUuid}/revisions`, {
    method: 'POST',
    body: JSON.stringify({ payload }),
  })
  expect(revision.status).toBe(201)
  const revisionUuid = String(revision.body?.revision_uuid)
  const activated = await liveApi(page, token, `/admin/policies/${policyUuid}/lifecycle`, {
    method: 'POST',
    body: JSON.stringify({ status: 'active', reason: 'live disposable activation' }),
  })
  expect(activated.status).toBe(200)

  const assigned = await liveApi(page, token, `/admin/devices/${deviceUuid}/policy-assignment`, {
    method: 'POST',
    body: JSON.stringify({ policy_revision_uuid: revisionUuid, reason: 'live disposable assignment' }),
  })
  expect(assigned.status).toBe(200)
  const assignment = await liveApi(page, token, `/admin/devices/${deviceUuid}/policy-assignment`)
  expect(assignment.status).toBe(200)
  expect((assignment.body?.policy_assignment as Record<string, unknown>)?.assignment ?? assignment.body?.assignment).toBeTruthy()
  const cleared = await liveApi(page, token, `/admin/devices/${deviceUuid}/policy-assignment/clear`, {
    method: 'POST',
    body: JSON.stringify({ reason: 'live disposable clear' }),
  })
  expect(cleared.status).toBe(200)

  const blocked = await liveApi(page, token, `/admin/devices/${deviceUuid}/block-overrides`, {
    method: 'POST',
    body: JSON.stringify({ reason: 'live disposable block' }),
  })
  expect(blocked.status).toBe(201)
  const clearBlock = await liveApi(page, token, `/admin/devices/${deviceUuid}/block-overrides/clear`, {
    method: 'POST',
    body: JSON.stringify({ reason: 'live disposable clear' }),
  })
  expect(clearBlock.status).toBe(200)

  const audit = await liveApi(page, token, '/admin/audit-events?page=1&per_page=100')
  expect(audit.status).toBe(200)
  expect(JSON.stringify(audit.body)).toContain('policy_assignment')
  expect(JSON.stringify(audit.body)).not.toContain(String(pairingToken))
})

test('executes live device enrollment, signed sync, audit replay, rotation, and recovery', async ({ page }) => {
  await signIn(page)
  const authorization: string[] = []
  page.on('request', (request) => {
    const value = request.headers().authorization
    if (value) authorization.push(value)
  })
  await navigateInApp(page, '/devices')
  await expect.poll(() => authorization.at(-1)).toMatch(/^Bearer /)
  const adminToken = authorization.at(-1)!
  const issued = await liveApi(page, adminToken, '/admin/enrollment-tokens', {
    method: 'POST',
    body: JSON.stringify({ reason: 'live signed device lifecycle', bound_device_uuid: null }),
  })
  expect(issued.status).toBe(201)
  const pairingToken = String(issued.body?.pairing_token)

  const result = await page.evaluate(async ({ adminToken, pairingToken }) => {
    type JsonObject = Record<string, unknown>
    const encoder = new TextEncoder()
    const b64url = (value: ArrayBuffer | Uint8Array) => {
      const bytes = value instanceof Uint8Array ? value : new Uint8Array(value)
      let binary = ''
      for (const byte of bytes) binary += String.fromCharCode(byte)
      return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
    }
    const digest = async (value: ArrayBuffer | Uint8Array) => new Uint8Array(await crypto.subtle.digest('SHA-256', value as BufferSource))
    const hex = (value: ArrayBuffer | Uint8Array) => [...(value instanceof Uint8Array ? value : new Uint8Array(value))]
      .map((byte) => byte.toString(16).padStart(2, '0')).join('')
    const canonical = (value: unknown): string => {
      if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
      if (value !== null && typeof value === 'object') {
        const object = value as JsonObject
        return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${canonical(object[key])}`).join(',')}}`
      }
      return JSON.stringify(value)
    }
    const makeKeys = () => crypto.subtle.generateKey(
      { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
      true,
      ['sign', 'verify'],
    ) as Promise<CryptoKeyPair>
    const keyMaterial = async () => {
      const keys = await makeKeys()
      const publicKey = new Uint8Array(await crypto.subtle.exportKey('spki', keys.publicKey))
      const fingerprint = await digest(publicKey)
      return { keys, publicKey: b64url(publicKey), fingerprintHex: hex(fingerprint) }
    }
    const readJson = async (response: Response) => {
      const body = await response.text()
      return body ? JSON.parse(body) as JsonObject : null
    }
    const adminFetch = (path: string, init: RequestInit = {}) => fetch(`/api/v1${path}`, {
      ...init,
      headers: { Authorization: adminToken, 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    })
    const deviceFetch = async (deviceUuid: string, credentialUuid: string, privateKey: CryptoKey, path: string, method = 'GET', body = '', query = '') => {
      const bodyHash = hex(await digest(encoder.encode(body)))
      const nonce = b64url(crypto.getRandomValues(new Uint8Array(16)))
      const timestamp = String(Math.floor(Date.now() / 1000))
      const target = `/api/v1${path}`
      const canonicalQuery = query ? query.split('&').sort().join('&') : ''
      const message = encoder.encode(['DEVICE-AUTH-V1', method, target, canonicalQuery, bodyHash, timestamp, nonce, credentialUuid, deviceUuid].join('\n'))
      const signature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', privateKey, message)
      return fetch(`${target}${query ? `?${query}` : ''}`, {
        method,
        body: body || undefined,
        headers: {
          Authorization: `DeviceCredential ${credentialUuid}`,
          'Content-Type': 'application/json',
          'X-Device-Timestamp': timestamp,
          'X-Device-Nonce': nonce,
          'X-Device-Body-SHA256': bodyHash,
          'X-Device-Signature': b64url(signature),
        },
      })
    }

    const deviceUuid = crypto.randomUUID()
    const current = await keyMaterial()
    const tokenUuid = pairingToken.split('.', 1)[0]
    const enrollmentNonce = b64url(crypto.getRandomValues(new Uint8Array(16)))
    const enrollmentMessage = encoder.encode(['DEVICE-ENROLL-V1', deviceUuid, tokenUuid, 'RSA_2048_SHA256', current.fingerprintHex, '14', '34', enrollmentNonce].join('\n'))
    const enrollmentProof = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', current.keys.privateKey, enrollmentMessage)
    const enrollment = await fetch('/api/v1/devices/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_uuid: deviceUuid,
        android_version: '14',
        api_level: 34,
        pairing_token: pairingToken,
        credential: { algorithm: 'RSA_2048_SHA256', public_key: current.publicKey, nonce: enrollmentNonce, proof: b64url(enrollmentProof) },
      }),
    })
    const enrollmentBody = await readJson(enrollment)
    if (enrollment.status !== 201) return { stage: 'enrollment', status: enrollment.status, body: enrollmentBody }
    const credentialUuid = String(enrollmentBody?.credential_uuid)

    const policies = await readJson(await adminFetch('/admin/policies?page=1&per_page=25&status=active'))
    const policyUuid = String((policies?.policies as JsonObject[])[0].policy_uuid)
    const revisions = await readJson(await adminFetch(`/admin/policies/${policyUuid}/revisions?page=1&per_page=25`))
    const revisionUuid = String((revisions?.revisions as JsonObject[])[0].revision_uuid)
    const assigned = await adminFetch(`/admin/devices/${deviceUuid}/policy-assignment`, {
      method: 'POST', body: JSON.stringify({ policy_revision_uuid: revisionUuid, reason: 'live signed device assignment' }),
    })
    if (assigned.status !== 200) return { stage: 'assignment', status: assigned.status }

    const sync = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/sync/policies/${deviceUuid}`, 'GET', '', 'current_version=0')
    const syncBody = await readJson(sync)
    if (sync.status !== 200 || syncBody?.operation !== 'apply') return { stage: 'sync', status: sync.status }
    const policy = syncBody.policy as JsonObject
    const rollback = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/sync/policies/${deviceUuid}`, 'GET', '', `current_version=2147483647&current_policy_uuid=${String(policy.policy_uuid)}&current_revision_uuid=${crypto.randomUUID()}`)
    const rollbackBody = await readJson(rollback)
    const now = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')
    const acknowledgementBody = JSON.stringify({ protocol_version: 3, acknowledgement_uuid: crypto.randomUUID(), observed_at: now(), elapsed_realtime_ms: 1, boot_count: 1, policy_uuid: policy.policy_uuid, revision_uuid: policy.policy_revision_uuid, outcome: 'applied', error_code: null })
    const acknowledgement = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/devices/${deviceUuid}/policy-acknowledgements`, 'POST', acknowledgementBody)
    const acknowledgementReplay = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/devices/${deviceUuid}/policy-acknowledgements`, 'POST', acknowledgementBody)
    const checkIn = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/devices/${deviceUuid}/check-ins`, 'POST', JSON.stringify({ protocol_version: 3, check_in_uuid: crypto.randomUUID(), observed_at: now(), elapsed_realtime_ms: 2, boot_count: 1, dpc_version: 1, android_version: '14', api_level: 34, security_patch: '2026-09-01', capabilities: ['forensic_audit_chain', 'offline_policy_enforcement'], current_policy_uuid: policy.policy_uuid, current_revision_uuid: policy.policy_revision_uuid, policy_status: 'applied', enforcement_healthy: true, queued_event_count: 0 }))

    const firstUnsigned: JsonObject = { event_uuid: crypto.randomUUID(), sequence: 1, occurred_at: now(), elapsed_realtime_ms: 1, boot_count: 1, event_code: 'sync_succeeded', outcome: 'succeeded', policy_uuid: policy.policy_uuid, revision_uuid: policy.policy_revision_uuid, rule_id: null, metadata: { source: 'live-e2e' }, previous_event_hash: null }
    const first = { ...firstUnsigned, event_hash: hex(await digest(encoder.encode(canonical(firstUnsigned)))) }
    const secondUnsigned: JsonObject = { event_uuid: crypto.randomUUID(), sequence: 2, occurred_at: now(), elapsed_realtime_ms: 2, boot_count: 1, event_code: 'policy_applied', outcome: 'succeeded', policy_uuid: policy.policy_uuid, revision_uuid: policy.policy_revision_uuid, rule_id: null, metadata: { source: 'live-e2e' }, previous_event_hash: first.event_hash }
    const second = { ...secondUnsigned, event_hash: hex(await digest(encoder.encode(canonical(secondUnsigned)))) }
    const unsignedBatch: JsonObject = { protocol_version: 3, batch_uuid: crypto.randomUUID(), device_uuid: deviceUuid, credential_uuid: credentialUuid, first_sequence: 1, last_sequence: 2, previous_head: null, final_head: second.event_hash, signature_algorithm: 'RSA_2048_SHA256', events: [first, second] }
    const batchSignature = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', current.keys.privateKey, encoder.encode(canonical(unsignedBatch)))
    const signedBatch = JSON.stringify({ ...unsignedBatch, signature: b64url(batchSignature) })
    const auditUpload = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/devices/${deviceUuid}/audit-batches`, 'POST', signedBatch)
    const auditUploadBody = await readJson(auditUpload)
    const auditReplay = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/devices/${deviceUuid}/audit-batches`, 'POST', signedBatch)
    const auditReplayBody = await readJson(auditReplay)

    const replacement = await keyMaterial()
    const rotationNonce = b64url(crypto.getRandomValues(new Uint8Array(16)))
    const rotationMessage = encoder.encode(['DEVICE-ROTATE-V1', deviceUuid, credentialUuid, 'RSA_2048_SHA256', replacement.fingerprintHex, rotationNonce].join('\n'))
    const rotationProof = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', replacement.keys.privateKey, rotationMessage)
    const rotationBody = JSON.stringify({ algorithm: 'RSA_2048_SHA256', public_key: replacement.publicKey, nonce: rotationNonce, proof: b64url(rotationProof) })
    const rotation = await deviceFetch(deviceUuid, credentialUuid, current.keys.privateKey, `/devices/${deviceUuid}/credentials/rotate`, 'POST', rotationBody)
    const rotationResponse = await readJson(rotation)
    const replacementUuid = String(rotationResponse?.credential_uuid)
    const replacementSync = await deviceFetch(deviceUuid, replacementUuid, replacement.keys.privateKey, `/sync/policies/${deviceUuid}`, 'GET', '', 'current_version=0')
    const block = await adminFetch(`/admin/devices/${deviceUuid}/block-overrides`, { method: 'POST', body: JSON.stringify({ reason: 'live signed device block' }) })
    const blockState = await deviceFetch(deviceUuid, replacementUuid, replacement.keys.privateKey, `/sync/v3/devices/${deviceUuid}/state`)
    const blockStateBody = await readJson(blockState)
    const clearBlock = await adminFetch(`/admin/devices/${deviceUuid}/block-overrides/clear`, { method: 'POST', body: JSON.stringify({ reason: 'live signed device recovery' }) })
    const clearState = await deviceFetch(deviceUuid, replacementUuid, replacement.keys.privateKey, `/sync/v3/devices/${deviceUuid}/state`)
    const clearStateBody = await readJson(clearState)
    const recoveredSync = await deviceFetch(deviceUuid, replacementUuid, replacement.keys.privateKey, `/sync/policies/${deviceUuid}`, 'GET', '', 'current_version=0')
    const revoke = await adminFetch(`/admin/devices/${deviceUuid}/credentials/revoke`, { method: 'POST', body: JSON.stringify({ reason: 'live signed device cleanup' }) })
    const revokedSync = await deviceFetch(deviceUuid, replacementUuid, replacement.keys.privateKey, `/sync/policies/${deviceUuid}`, 'GET', '', 'current_version=0')
    return { stage: 'complete', enrollment: enrollment.status, sync: sync.status, rollback: rollback.status, rollbackBody, rollbackOperation: rollbackBody?.operation, acknowledgement: acknowledgement.status, acknowledgementReplay: acknowledgementReplay.status, checkIn: checkIn.status, auditUpload: auditUpload.status, auditUploadBody, auditReplay: auditReplay.status, auditReplayBody, rotation: rotation.status, replacementSync: replacementSync.status, block: block.status, blockState: blockState.status, blockStateBody, clearBlock: clearBlock.status, clearState: clearState.status, clearStateBody, recoveredSync: recoveredSync.status, revoke: revoke.status, revokedSync: revokedSync.status }
  }, { adminToken, pairingToken })

  expect(result.stage, JSON.stringify(result)).toBe('complete')
  expect(result.enrollment).toBe(201)
  expect(result.sync).toBe(200)
  expect(result.rollback, JSON.stringify(result)).toBe(200)
  expect(result.rollbackOperation).toBe('rollback')
  expect(result.acknowledgement).toBe(200)
  expect(result.acknowledgementReplay).toBe(200)
  expect(result.checkIn).toBe(200)
  expect(result.auditUpload).toBe(200)
  expect(result.auditUploadBody).toMatchObject({ replayed: false, accepted_through_sequence: 2 })
  expect(result.auditReplay).toBe(200)
  expect(result.auditReplayBody).toMatchObject({ replayed: true, accepted_through_sequence: 2 })
  expect(result.rotation).toBe(201)
  expect(result.replacementSync).toBe(200)
  expect(result.block).toBe(201)
  expect(result.blockState).toBe(200)
  expect((result.blockStateBody as { override_state?: { override?: { status?: string } } }).override_state?.override?.status).toBe('active')
  expect(result.clearBlock).toBe(200)
  expect(result.clearState).toBe(200)
  expect((result.clearStateBody as { override_state?: { override?: { status?: string } } }).override_state?.override?.status).toBe('cleared')
  expect(result.recoveredSync).toBe(200)
  expect(result.revoke).toBe(200)
  expect(result.revokedSync).toBe(401)
})

test('shows a real browser-offline dependency failure and recovers when connectivity returns', async ({ page }) => {
  await signIn(page)
  await navigateInApp(page, '/devices')
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await page.context().setOffline(true)
  const offlineFetchRejected = await page.evaluate(async () => {
    try {
      await fetch('/api/v1/admin/devices?page=1&per_page=25', { cache: 'no-store' })
      return false
    } catch {
      return true
    }
  })
  expect(offlineFetchRejected).toBe(true)
  await page.context().setOffline(false)
  await page.getByLabel('Status').first().selectOption('active')
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
})

test('expires a disposable enrollment token through the live enrollment contract', async ({ page }) => {
  test.skip(process.env.EDUG_LIVE_TOKEN_EXPIRY_TEST !== '1', 'run this scenario in its isolated expiry gate')
  await signIn(page)
  const authorization: string[] = []
  page.on('request', (request) => {
    const value = request.headers().authorization
    if (value) authorization.push(value)
  })
  await navigateInApp(page, '/devices')
  await expect.poll(() => authorization.at(-1)).toMatch(/^Bearer /)
  const adminToken = authorization.at(-1)!
  const issued = await liveApi(page, adminToken, '/admin/enrollment-tokens', {
    method: 'POST',
    body: JSON.stringify({ reason: 'live disposable expiry verification', bound_device_uuid: null }),
  })
  expect(issued.status).toBe(201)
  const tokenUuid = String(issued.body?.token_uuid)
  const pairingToken = String(issued.body?.pairing_token)
  await page.waitForTimeout(1500)
  const expiredAttempt = await page.evaluate(async ({ pairingToken }) => {
    const response = await fetch('/api/v1/devices/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_uuid: crypto.randomUUID(),
        android_version: '14',
        api_level: 34,
        pairing_token: pairingToken,
        credential: { algorithm: 'RSA_2048_SHA256', public_key: 'x', nonce: 'x', proof: 'x' },
      }),
    })
    return { status: response.status, body: await response.text() }
  }, { pairingToken })
  expect(expiredAttempt.status).toBe(401)
  const tokens = await liveApi(page, adminToken, '/admin/enrollment-tokens?page=1&per_page=25')
  expect(tokens.status).toBe(200)
  const expired = (tokens.body?.enrollment_tokens as Array<Record<string, unknown>>).find((item) => item.token_uuid === tokenUuid)
  expect(expired?.status).toBe('expired')
  expect(JSON.stringify(tokens.body)).not.toContain(pairingToken)
})

test('receives a real login rate-limit response from disposable Redis', async ({ page }) => {
  test.skip(process.env.EDUG_LIVE_RATE_LIMIT_TEST !== '1', 'run this scenario in its isolated rate-limit gate')
  const responses: number[] = []
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const response = await page.request.post('/api/v1/admin/auth/login', {
      data: { username: 'local.e2e.invalid', password: 'invalid disposable password' },
    })
    responses.push(response.status())
  }
  expect(responses).toContain(429)
})
