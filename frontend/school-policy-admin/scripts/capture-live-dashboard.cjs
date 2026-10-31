const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const outputDir = path.resolve(__dirname, '../../../output/edugd-pitch-assets');
fs.mkdirSync(outputDir, { recursive: true });
const captureUsername = process.env.EDUG_CAPTURE_USERNAME || 'ed.admin';
const capturePassword = process.env.EDUG_CAPTURE_PASSWORD;
if (!capturePassword) throw new Error('Set EDUG_CAPTURE_PASSWORD before capturing authenticated dashboard snapshots.');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
  await page.getByLabel('Username').fill(captureUsername);
  await page.getByLabel('Password').fill(capturePassword);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL('**/dashboard');
  await page.waitForTimeout(2500);

  const captures = [
    ['dashboard', '/dashboard'],
    ['devices', '/devices'],
    ['policies', '/policies'],
    ['reports', '/reports'],
    ['operations', '/operations'],
  ];
  for (const [name, route] of captures) {
    if (route !== '/dashboard') {
      await page.locator(`a[href="${route}"]`).first().click();
      await page.waitForURL(`**${route}`);
    }
    await page.waitForTimeout(4000);
    await page.screenshot({ path: path.join(outputDir, `${name}.png`), fullPage: true });
    console.log(`CAPTURED: ${name}`);
  }
  await context.close();
  browser.close().catch(() => {});
  process.exit(0);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
