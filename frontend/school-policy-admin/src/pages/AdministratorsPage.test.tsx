import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdministratorsPage } from './AdministratorsPage'
import { adminService } from '@/services/admin.service'

const hasPermission = vi.fn()
vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ hasPermission }) }))
vi.mock('@/services/admin.service', () => ({ adminService: { createAdministrator: vi.fn() } }))

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient()}><AdministratorsPage /></QueryClientProvider>)
}

describe('administrator management', () => {
  beforeEach(() => { vi.clearAllMocks(); hasPermission.mockReturnValue(true) })

  it('does not expose the creation form without administrator.manage', () => {
    hasPermission.mockReturnValue(false)
    renderPage()
    expect(screen.queryByRole('button', { name: /create administrator/i })).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/does not have permission/i)
  })

  it('submits the supported backend contract and clears sensitive fields after success', async () => {
    vi.mocked(adminService.createAdministrator).mockResolvedValue({ administrator_uuid: '11111111-1111-4111-8111-111111111111', username: 'new-admin', permissions: ['administrator.manage'], revoked_sessions: 0 })
    renderPage()
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'new-admin' } })
    fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'New Admin' } })
    fireEvent.change(screen.getByLabelText('New administrator password'), { target: { value: 'new-password' } })
    fireEvent.change(screen.getByLabelText('Your operator password'), { target: { value: 'operator-password' } })
    fireEvent.change(screen.getByLabelText('Reason for granting administrator access'), { target: { value: 'Approved access' } })
    fireEvent.click(screen.getByRole('button', { name: /create administrator/i }))
    await waitFor(() => expect(adminService.createAdministrator).toHaveBeenCalledWith('new-admin', 'New Admin', 'new-password', 'operator-password', 'Approved access'))
    expect(await screen.findByRole('status')).toHaveTextContent('new-admin')
    expect(screen.getByLabelText('New administrator password')).toHaveValue('')
    expect(screen.getByLabelText('Your operator password')).toHaveValue('')
  })
})
