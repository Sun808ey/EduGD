import { describe, expect, it } from 'vitest'
import { formatDate } from '@/lib/format'

describe('Uganda date formatting', () => {
  it('uses Kampala time and handles absent or invalid values', () => {
    expect(formatDate('2026-09-11T00:00:00Z')).toContain('03:00')
    expect(formatDate(null)).toBe('Unknown')
    expect(formatDate('invalid')).toBe('Unknown')
  })
})
