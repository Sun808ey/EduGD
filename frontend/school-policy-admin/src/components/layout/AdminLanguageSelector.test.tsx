import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { LanguageProvider } from '@/i18n/LanguageContext'
import { AdminLanguageSelector } from './AdminLanguageSelector'

describe('AdminLanguageSelector', () => {
  beforeEach(() => { localStorage.clear() })

  it('offers exactly the six languages and persists one selected preference', () => {
    render(<LanguageProvider><AdminLanguageSelector /></LanguageProvider>)
    fireEvent.click(screen.getByRole('button', { name: /language/i }))
    expect(screen.getAllByRole('menuitemradio')).toHaveLength(6)
    fireEvent.click(screen.getByRole('menuitemradio', { name: 'Luganda' }))
    expect(localStorage.getItem('edug.admin.language')).toBe('lug')
    expect(localStorage.getItem('edug.public.language')).toBeNull()
  })

  it('restores focus after Escape closes the menu', () => {
    render(<LanguageProvider><AdminLanguageSelector /></LanguageProvider>)
    const trigger = screen.getByRole('button', { name: /language/i })
    fireEvent.click(trigger)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(trigger).toHaveFocus()
  })
})
