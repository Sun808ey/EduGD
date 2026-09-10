import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { resolveApiBaseUrl, resolveSentryDsn } from './src/lib/environment.ts'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  resolveApiBaseUrl(env.VITE_API_BASE_URL, command === 'build')
  resolveSentryDsn(env.VITE_SENTRY_DSN)
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: { proxy: { '/api': { target: 'http://127.0.0.1:5000' } } },
  }
})
