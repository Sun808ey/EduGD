import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const sourceDirectory = path
  .resolve(path.dirname(fileURLToPath(import.meta.url)), 'src')
  .replaceAll('\\', '/')
const attachedKnowledgePath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../output/edugd-180-questions-and-answers.md',
)
const attachedKnowledgeModule = 'virtual:edugd-qa-source'
const resolvedAttachedKnowledgeModule = `\0${attachedKnowledgeModule}`

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'edugd-attached-knowledge-source',
      resolveId(id) {
        return id === attachedKnowledgeModule ? resolvedAttachedKnowledgeModule : undefined
      },
      load(id) {
        if (id !== resolvedAttachedKnowledgeModule) return undefined
        return `export const edugdQaSource = ${JSON.stringify(fs.readFileSync(attachedKnowledgePath, 'utf8'))}`
      },
    },
  ],
  resolve: {
    alias: [{ find: /^@\//, replacement: `${sourceDirectory}/` }],
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    testTimeout: 15_000,
    coverage: {
      reporter: ['text', 'json', 'html'],
      include: [
        'src/auth/**/*.ts',
        'src/context/**/*.{ts,tsx}',
        'src/lib/**/*.ts',
        'src/schemas/**/*.ts',
        'src/services/**/*.ts',
      ],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/'],
      thresholds: {
        statements: 90,
        branches: 85,
        functions: 90,
        lines: 90,
      },
    },
  },
})
