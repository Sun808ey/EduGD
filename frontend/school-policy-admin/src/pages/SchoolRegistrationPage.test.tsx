import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SchoolRegistrationPage } from './SchoolRegistrationPage'
import { adminService } from '@/services/admin.service'

vi.mock('react-router-dom', () => ({ useLocation: () => ({ pathname: '/school' }) }))
vi.mock('@/services/admin.service', () => ({ adminService: { getSchool: vi.fn(), registerSchool: vi.fn(), updateSchool: vi.fn() } }))

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient()}><SchoolRegistrationPage /></QueryClientProvider>)
}

describe('school registration form', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminService.getSchool).mockResolvedValue(null)
  })

  it('persists telephone and email input events in the controlled form state', async () => {
    renderPage()

    const telephone = await screen.findByRole('textbox', { name: /Official school telephone number/ })
    const email = screen.getByRole('textbox', { name: /Official school email \(optional\)/ })
    fireEvent.input(telephone, { target: { value: '0000000000' } })
    fireEvent.input(email, { target: { value: 'office@example.invalid' } })

    await waitFor(() => {
      expect(telephone).toHaveValue('0000000000')
      expect(email).toHaveValue('office@example.invalid')
    })
  })
})
