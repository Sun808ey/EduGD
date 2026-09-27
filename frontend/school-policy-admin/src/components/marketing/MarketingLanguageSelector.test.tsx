import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LandingLanguageProvider } from '@/i18n/LandingLanguageContext'
import { publicLanguageStorageKey } from '@/i18n/languages'
import api from '@/services/api'
import { MarketingLanguageSelector } from './MarketingLanguageSelector'

vi.mock('@/services/api', () => ({ default: { post: vi.fn() } }))

describe('MarketingLanguageSelector', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.post).mockResolvedValue({ data: { translations: {} } })
  })

  it('keeps English as the default and exposes exactly the approved languages', () => {
    render(<LandingLanguageProvider><MarketingLanguageSelector /></LandingLanguageProvider>)
    fireEvent.click(screen.getByRole('button', { name: /choose language/i }))
    expect(screen.getAllByRole('menuitemradio')).toHaveLength(6)
    expect(screen.getByRole('menuitemradio', { name: 'English' })).toHaveAttribute('aria-checked', 'true')
  })

  it('persists the selected public language and stays within the route quota', async () => {
    render(<LandingLanguageProvider><MarketingLanguageSelector /></LandingLanguageProvider>)
    fireEvent.click(screen.getByRole('button', { name: /choose language/i }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'Luganda' }))
    expect(window.localStorage.getItem(publicLanguageStorageKey)).toBe('lug')
    expect(window.localStorage.getItem('edug.admin.language')).toBeNull()
    await waitFor(() => expect(api.post).toHaveBeenCalled())
    expect(vi.mocked(api.post).mock.calls.length).toBeLessThanOrEqual(60)
    for (const call of vi.mocked(api.post).mock.calls) {
      expect(call).toEqual([
        '/public/translation/translate',
        expect.objectContaining({ target_language: 'lug', content_key: expect.any(String) }),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      ])
    }
  })
})
