import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { LandingLanguageProvider } from '@/i18n/LandingLanguageContext'
import { publicLanguageStorageKey } from '@/i18n/languages'
import { MarketingLanguageSelector } from './MarketingLanguageSelector'

describe('MarketingLanguageSelector', () => {
  beforeEach(() => window.localStorage.clear())

  it('keeps English as the default and exposes exactly the approved languages', () => {
    render(<LandingLanguageProvider><MarketingLanguageSelector /></LandingLanguageProvider>)
    fireEvent.click(screen.getByRole('button', { name: /choose language/i }))
    expect(screen.getAllByRole('menuitemradio')).toHaveLength(6)
    expect(screen.getByRole('menuitemradio', { name: 'English' })).toHaveAttribute('aria-checked', 'true')
  })

  it('persists the selected public language without changing the admin key', () => {
    render(<LandingLanguageProvider><MarketingLanguageSelector /></LandingLanguageProvider>)
    fireEvent.click(screen.getByRole('button', { name: /choose language/i }))
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'Luganda' }))
    expect(window.localStorage.getItem(publicLanguageStorageKey)).toBe('lug')
    expect(window.localStorage.getItem('edug.admin.language')).toBeNull()
  })
})
