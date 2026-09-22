import { AxeBuilder } from '@axe-core/playwright'
import { expect, test, type Page, type Route } from '@playwright/test'

const administratorUuid = '11111111-1111-4111-8111-111111111111'
const deviceUuid = '22222222-2222-4222-8222-222222222222'
const policyUuid = '33333333-3333-4333-8333-333333333333'
const revisionUuid = '44444444-4444-4444-8444-444444444444'
const eventUuid = '55555555-5555-4555-8555-555555555555'

const json = (route: Route, body: unknown, status = 200, headers: Record<string, string> = {}) => route.fulfill({ status, contentType: 'application/json', headers, body: JSON.stringify(body) })
const pagination = (total: number) => ({ page: 1, per_page: 25, total, has_next: false })

async function mockApi(page: Page, permissions = ['enrollment_token.issue', 'enrollment_token.revoke', 'device_credential.revoke', 'policy.assign']) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/admin/auth/login')) return json(route, { access_token: 'browser-memory-token', token_type: 'Bearer', expires_in: 900, administrator: { administrator_uuid: administratorUuid, username: 'admin', display_name: 'School Administrator' } })
    if (pathname.endsWith('/admin/auth/me')) return json(route, { administrator: { administrator_uuid: administratorUuid, username: 'admin', display_name: 'School Administrator', permissions } })
    if (pathname.endsWith('/admin/auth/logout')) return json(route, { message: 'administrator logged out' })
    if (pathname.endsWith('/admin/devices') && request.method() === 'GET') return json(route, { devices: [{ device_uuid: deviceUuid, android_version: '14', api_level: 34, status: 'active', enrollment_state: 'enrolled', legacy_enrollment_eligible: false, registered_at: '2026-09-10T10:00:00Z', last_sync_at: '2026-09-11T07:00:00Z', active_policy_assignment: null }], pagination: pagination(1) })
    if (pathname.endsWith('/admin/policies') && request.method() === 'GET') return json(route, { policies: [{ policy_uuid: policyUuid, name: 'School day policy', status: 'active', created_at: '2026-09-10T10:00:00Z', updated_at: '2026-09-11T07:00:00Z', latest_revision: { revision_uuid: revisionUuid, version: 1, payload: { camera_disabled: true }, content_hash: 'abc123', created_at: '2026-09-11T07:00:00Z', created_by: 'admin' } }], pagination: pagination(1) })
    if (pathname.endsWith('/admin/audit-events')) return json(route, { audit_events: [{ event_type: 'device_enrollment', event_uuid: eventUuid, category: 'enrollment_succeeded', occurred_at: '2026-09-11T07:00:00Z', failure_class: null }], pagination: pagination(1) })
    if (pathname.endsWith('/admin/enrollment-tokens')) return json(route, { enrollment_tokens: [], pagination: pagination(0) })
    return json(route, { error: { code: 'not_found', message: 'not found' } }, 404)
  })
}

async function signIn(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Username').fill('admin')
  await page.getByLabel('Password').fill('correct horse battery staple')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'System overview' })).toBeVisible()
}

test('authenticates in memory and renders the API-backed administration flow', async ({ page }) => {
  await mockApi(page)
  const authorizationHeaders: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/admin/') && !request.url().endsWith('/auth/login')) authorizationHeaders.push(request.headers().authorization ?? '')
  })
  await signIn(page)
  await expect(page.getByText('Managed devices').locator('..').getByText('1')).toBeVisible()
  expect(authorizationHeaders).toContain('Bearer browser-memory-token')

  const menu = page.getByRole('button', { name: 'Open navigation' })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('link', { name: 'Devices' }).click()
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await expect(page.getByText(deviceUuid, { exact: true })).toBeVisible()
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 })
})

test('meets automated accessibility checks on login and authenticated dashboard', async ({ page }) => {
  await mockApi(page)
  await page.goto('/login')
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
  await signIn(page)
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
})

test('honors the login Retry-After response', async ({ page }) => {
  await page.route('**/api/v1/admin/auth/login', (route) => json(route, { error: { code: 'rate_limit_exceeded', message: 'rate limit exceeded' } }, 429, { 'retry-after': '2', 'access-control-expose-headers': 'Retry-After' }))
  await page.goto('/login')
  await page.getByLabel('Username').fill('admin')
  await page.getByLabel('Password').fill('wrong')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert')).toContainText('Too many sign-in attempts')
  await expect(page.getByRole('button', { name: /Try again in/ })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeEnabled({ timeout: 4_000 })
})

test('clears a revoked session when a protected API call returns 401', async ({ page }) => {
  await mockApi(page)
  await page.route('**/api/v1/admin/devices**', (route) => json(route, { error: { code: 'authentication_failed', message: 'authentication failed' } }, 401))
  await page.goto('/login')
  await page.getByLabel('Username').fill('admin')
  await page.getByLabel('Password').fill('password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('status')).toContainText('expired or was revoked')
})

test('keeps mutation controls hidden for a read-only administrator', async ({ page }) => {
  await mockApi(page, [])
  await signIn(page)
  const menu = page.getByRole('button', { name: 'Open navigation' })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('link', { name: 'Devices' }).click()
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Manage policy' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Issue token' })).toHaveCount(0)
})
