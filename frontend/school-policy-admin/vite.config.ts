import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { resolveApiBaseUrl } from './src/lib/environment.ts'

const sourceDirectory = path
  .resolve(path.dirname(fileURLToPath(import.meta.url)), 'src')
  .replaceAll('\\', '/')
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  resolveApiBaseUrl(env.VITE_API_BASE_URL, command === 'build')

  return {
    plugins: [react(), tailwindcss()],
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
