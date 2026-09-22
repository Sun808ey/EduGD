import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { resolveApiBaseUrl, resolveApiTimeout, resolveSentryDsn } from './src/lib/environment.ts'

const sourceDirectory = path
  .resolve(path.dirname(fileURLToPath(import.meta.url)), 'src')
  .replaceAll('\\', '/')
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const apiBaseUrl = resolveApiBaseUrl(env.VITE_API_BASE_URL, command === 'build')
  resolveApiTimeout(env.VITE_API_TIMEOUT)
  const sentryDsn = resolveSentryDsn(env.VITE_SENTRY_DSN)
  const connectSources = command === 'build'
    ? [new URL(apiBaseUrl).origin, ...(sentryDsn ? [new URL(sentryDsn).origin] : [])]
    : []

  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'edug-exact-connect-csp',
        transformIndexHtml: command === 'build' ? {
          order: 'post',
          handler: () => [{ tag: 'meta', attrs: { 'http-equiv': 'Content-Security-Policy', content: `default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self'; connect-src 'self' ${connectSources.join(' ')}; base-uri 'none'; form-action 'self'; object-src 'none'; manifest-src 'self'; upgrade-insecure-requests` }, injectTo: 'head' }],
        } : undefined,
      },
    ],
    build: {
      // Tailwind v4 directives are processed before esbuild minification.
      cssMinify: 'esbuild',
    },
    resolve: {
      alias: [{ find: /^@\//, replacement: `${sourceDirectory}/` }],
    },
    server: {
      proxy: {
        '/api': { target: 'http://127.0.0.1:5000' },
      },
    },
  }
})
