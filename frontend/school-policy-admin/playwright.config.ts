import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['list']] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'python ../../backend/scripts/local_stack.py --e2e --frontend-port 4173',
    url: 'http://127.0.0.1:4173/login',
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      VITE_DPC_SERVER_SIGNING_KEY_ID: 'local-e2e-signing-key',
      VITE_DPC_SERVER_SIGNING_PUBLIC_KEY: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
      VITE_DPC_SERVER_SIGNING_KEY_FINGERPRINT: '66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925',
    },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'] } },
  ],
})
