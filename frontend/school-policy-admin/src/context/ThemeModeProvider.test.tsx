import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { useContext } from 'react'
import { ThemeModeContext } from './ThemeModeContext'
import { ThemeModeProvider } from './ThemeModeProvider'

function Probe() {
  const value = useContext(ThemeModeContext)
  if (!value) return <span>missing</span>
  return <div><output>{value.mode}</output><button onClick={value.toggle}>toggle</button></div>
}

describe('theme mode provider', () => {
  beforeEach(() => {
    window.localStorage.clear()
    Object.defineProperty(window, 'matchMedia', { configurable: true, value: vi.fn(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn() })) })
    document.documentElement.dataset.theme = ''
    document.documentElement.style.colorScheme = ''
  })

  it('defaults to light mode and persists a dark-mode toggle', async () => {
    render(<ThemeModeProvider><Probe /></ThemeModeProvider>)
    expect(screen.getByText('light')).toBeInTheDocument()
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe('light'))
    fireEvent.click(screen.getByRole('button', { name: 'toggle' }))
    expect(screen.getByText('dark')).toBeInTheDocument()
    await waitFor(() => expect(window.localStorage.getItem('edugd-theme')).toBe('dark'))
    expect(document.documentElement.style.colorScheme).toBe('dark')
  })

  it('honours stored and system dark-mode preferences', () => {
    window.localStorage.setItem('edugd-theme', 'dark')
    render(<ThemeModeProvider><Probe /></ThemeModeProvider>)
    expect(screen.getByText('dark')).toBeInTheDocument()

    window.localStorage.clear()
    vi.mocked(window.matchMedia).mockReturnValue({ matches: true, addListener: vi.fn(), removeListener: vi.fn() } as unknown as MediaQueryList)
    render(<ThemeModeProvider><Probe /></ThemeModeProvider>)
    expect(screen.getAllByText('dark')).toHaveLength(2)
  })
})
