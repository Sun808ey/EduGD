import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SchoolRegistrationPage } from './SchoolRegistrationPage'
import { adminService } from '@/services/admin.service'

vi.mock('react-router-dom', () => ({ useLocation: () => ({ pathname: '/school' }) }))
vi.mock('@/services/admin.service', () => ({ adminService: { getSchool: vi.fn(), registerSchool: vi.fn(), updateSchool: vi.fn() } }))

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><SchoolRegistrationPage /></QueryClientProvider>)
}

describe('school registration form', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminService.getSchool).mockResolvedValue(null)
  })

  it('persists telephone and email input events in the controlled form state', async () => {
    renderPage()
    expect(adminService.getSchool).toHaveBeenCalled()

    const telephone = await screen.findByLabelText(/Official school telephone number/)
    const email = screen.getByLabelText(/Official school email \(optional\)/)
    fireEvent.change(telephone, { target: { value: '0000000000' } })
    fireEvent.change(email, { target: { value: 'office@example.invalid' } })

    expect(telephone).toHaveValue('0000000000')
    expect(email).toHaveValue('office@example.invalid')
  }, 15000)
})
