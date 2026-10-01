import { AxeBuilder } from '@axe-core/playwright'
import { expect, test, type Page, type TestInfo } from '@playwright/test'

const admin = { username: 'local.e2e.admin', password: 'LocalE2EAdmin!2026' }
const readonly = { username: 'local.e2e.reader', password: 'LocalE2EReader!2026' }

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

test('uses the live Flask API for the administrator dashboard lifecycle', async ({ page }) => {
  const apiRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/admin/')) apiRequests.push(request.url())
  })
  await signIn(page)
  await expect(page.getByText('Managed devices').locator('..').getByText('1')).toBeVisible()
  await openNavigation(page)
  await page.getByRole('link', { name: 'Devices' }).click()
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
  await navigateInApp(page, '/devices/22222222-2222-4222-8222-222222222222')
  await expect(page.getByRole('heading', { name: '22222222-2222-4222-8222-222222222222' })).toBeVisible()
  await navigateInApp(page, '/administrators')
  await expect(page.getByRole('heading', { name: 'Administrators' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Create administrator' })).toBeVisible()
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
