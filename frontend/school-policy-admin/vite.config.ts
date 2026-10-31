import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { resolveApiBaseUrl, resolveApiTimeout, resolveSentryDsn } from './src/lib/environment.ts'

const sourceDirectory = path
  .resolve(path.dirname(fileURLToPath(import.meta.url)), 'src')
  .replaceAll('\\', '/')
const attachedKnowledgePath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../output/edugd-180-questions-and-answers.md',
)
const attachedKnowledgeModule = 'virtual:edugd-qa-source'
const resolvedAttachedKnowledgeModule = `\0${attachedKnowledgeModule}`
const attachedKnowledgeText = fs.existsSync(attachedKnowledgePath)
  ? fs.readFileSync(attachedKnowledgePath, 'utf8')
  : ''
export default defineConfig(({ command, mode }) => {
  // Explicit process environment values are authoritative for local runs.
  // This keeps a developer's selected API origin from being shadowed by a
  // machine-specific .env.local file.
  const env = { ...loadEnv(mode, process.cwd(), 'VITE_'), ...process.env }
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
        name: 'edugd-attached-knowledge-source',
        resolveId(id) {
          return id === attachedKnowledgeModule ? resolvedAttachedKnowledgeModule : undefined
        },
        load(id) {
          if (id !== resolvedAttachedKnowledgeModule) return undefined
          return `export const edugdQaSource = ${JSON.stringify(attachedKnowledgeText)}`
        },
      },
      {
        name: 'edug-exact-connect-csp',
        transformIndexHtml: command === 'build' ? {
          order: 'post',
          // MUI uses Emotion to inject scoped component styles at runtime. Keep
          // all resource classes restricted while allowing those generated
          // style tags to render the authenticated admin shell.
          handler: () => [{ tag: 'meta', attrs: { 'http-equiv': 'Content-Security-Policy', content: `default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self'; connect-src 'self' ${connectSources.join(' ')}; base-uri 'none'; form-action 'self'; object-src 'none'; manifest-src 'self'; upgrade-insecure-requests` }, injectTo: 'head' }],
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
      headers: {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
      },
      proxy: {
        '/api': { target: 'http://127.0.0.1:5000' },
      },
    },
  }
})
