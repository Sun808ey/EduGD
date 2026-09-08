import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const sourceDirectory = path
  .resolve(path.dirname(fileURLToPath(import.meta.url)), 'src')
  .replaceAll('\\', '/')
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Tailwind v4 directives are processed by PostCSS before esbuild minification.
    cssMinify: 'esbuild',
  },
  resolve: {
    alias: [{ find: /^@\//, replacement: `${sourceDirectory}/` }],
  },
})
